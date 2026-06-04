"""Demo dataset for the default Orbiteus tenant — small, realistic, idempotent.

Used when ``SEED_DEMO_DATA=1`` (see ``docker-compose.yml``). Never creates
extra tenants or bulk junk; replaces the deprecated ``seed_bulk_demo.py``.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.config import settings
from orbiteus_core.context import RequestContext
from orbiteus_core.security.passwords import hash_password

logger = logging.getLogger(__name__)

DEMO_SEED_VERSION = "1"
DEMO_SEED_PARAM = "demo.seed_version"
DEMO_PASSWORD = "demo1234"

KEEP_EMAILS = frozenset(
    e.lower()
    for e in (
        settings.bootstrap_admin_email,
        "demo.manager@example.com",
        "demo.user@example.com",
        "demo.sales@example.com",
    )
)


@dataclass(frozen=True)
class DemoUserSpec:
    email: str
    name: str
    role_ids: tuple[str, ...]
    is_superadmin: bool = False


DEMO_USERS: tuple[DemoUserSpec, ...] = (
    DemoUserSpec(
        email="demo.manager@example.com",
        name="Alex Manager",
        role_ids=("base.group_system",),
    ),
    DemoUserSpec(
        email="demo.user@example.com",
        name="Jordan User",
        role_ids=("base.group_user",),
    ),
    DemoUserSpec(
        email="demo.sales@example.com",
        name="Sam Sales",
        role_ids=("base.group_user",),
    ),
)

DEMO_COMPANIES: tuple[dict[str, Any], ...] = (
    {
        "name": "Orbiteus HQ",
        "currency_code": "PLN",
        "country_code": "PL",
        "city": "Warsaw",
        "email": "hq@orbiteus.local",
        "vat": "PL1234567890",
    },
    {
        "name": "Orbiteus Labs",
        "currency_code": "EUR",
        "country_code": "DE",
        "city": "Berlin",
        "email": "labs@orbiteus.local",
    },
)

DEMO_ATTACHMENTS: tuple[dict[str, str], ...] = (
    {
        "filename": "company-overview.txt",
        "mimetype": "text/plain",
        "body": "Orbiteus HQ — demo attachment.\nModular engine for business apps.\n",
        "description": "Company overview (demo)",
    },
    {
        "filename": "onboarding-checklist.txt",
        "mimetype": "text/plain",
        "body": "- Invite team\n- Configure SMTP\n- Upload documents\n",
        "description": "Onboarding checklist (demo)",
    },
)


async def reset_demo_database(session: AsyncSession, *, default_tenant_id: uuid.UUID) -> dict[str, int]:
    """Remove bulk/junk rows and non-default tenants. Keeps bootstrap admin."""
    from modules.base.model.mapping import (
        base_agent_runs_table,
        base_agents_table,
        base_attachments_table,
        base_audit_log_table,
        base_config_params_table,
        base_embeddings_table,
        base_mail_templates_table,
        base_model_access_table,
        base_model_fields_table,
        base_models_table,
        base_rules_table,
        base_ui_menus_table,
        base_ui_views_table,
        companies_table,
        tenants_table,
        user_roles_table,
        users_table,
    )

    stats: dict[str, int] = {}

    async def _count(stmt) -> int:
        return (await session.execute(stmt)).scalar_one()

    # Attachment binaries first (all tenants — clean filestore).
    await _purge_attachment_storage()

    r = await session.execute(delete(base_attachments_table))
    stats["base_attachments"] = r.rowcount or 0

    # Tenant-scoped rows on non-default tenants.
    other_tenant_ids = (
        await session.execute(
            select(tenants_table.c.id).where(tenants_table.c.id != default_tenant_id)
        )
    ).scalars().all()

    for tid in other_tenant_ids:
        for table in (
            base_agent_runs_table,
            base_agents_table,
            base_embeddings_table,
            base_audit_log_table,
            users_table,
            companies_table,
        ):
            if "tenant_id" in table.c:
                await session.execute(delete(table).where(table.c.tenant_id == tid))

    r = await session.execute(
        delete(tenants_table).where(tenants_table.c.id != default_tenant_id)
    )
    stats["base_tenants"] = r.rowcount or 0

    # Default tenant — drop all companies (re-created by seed).
    r = await session.execute(
        delete(companies_table).where(companies_table.c.tenant_id == default_tenant_id)
    )
    stats["base_companies"] = r.rowcount or 0

    # Bulk demo script duplicated YAML model-access rows — rebuild from YAML.
    r = await session.execute(delete(base_model_access_table))
    stats["base_model_access"] = r.rowcount or 0

    # Users: keep bootstrap admin + demo personas only.
    user_rows = (
        await session.execute(
            select(users_table.c.id, users_table.c.email).where(
                users_table.c.tenant_id == default_tenant_id
            )
        )
    ).all()
    remove_ids = [
        row.id for row in user_rows if (row.email or "").lower() not in KEEP_EMAILS
    ]
    if remove_ids:
        await session.execute(
            delete(user_roles_table).where(user_roles_table.c.user_id.in_(remove_ids))
        )
        r = await session.execute(
            delete(users_table).where(users_table.c.id.in_(remove_ids))
        )
        stats["base_users"] = r.rowcount or 0

    # Legacy bulk-seed artefacts (global / cross-tenant junk).
    for table, condition in (
        (base_config_params_table, base_config_params_table.c.key.like("seed.%")),
        (base_ui_menus_table, base_ui_menus_table.c.name.like("Seed Menu%")),
        (base_ui_views_table, base_ui_views_table.c.module == "seed"),
        (base_rules_table, base_rules_table.c.name.like("Seed Rule%")),
        (base_model_fields_table, base_model_fields_table.c.model_name.like("x.seed.%")),
        (base_models_table, base_models_table.c.model_name.like("x.seed.%")),
        (base_mail_templates_table, base_mail_templates_table.c.name.like("Seed Mail Template%")),
        (base_model_access_table, base_model_access_table.c.model_name.like("x.seed.%")),
    ):
        r = await session.execute(delete(table).where(condition))
        key = table.name
        stats[key] = stats.get(key, 0) + (r.rowcount or 0)

    # Orphan attachments pointing at deleted companies (metadata without binary).
    await session.execute(
        text(
            """
            DELETE FROM base_attachments a
            WHERE a.res_model = 'base.company'
              AND a.res_id IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM base_companies c WHERE c.id = a.res_id)
            """
        )
    )

    # Reset demo marker so seed runs again.
    await session.execute(
        delete(base_config_params_table).where(base_config_params_table.c.key == DEMO_SEED_PARAM)
    )

    await session.flush()
    logger.info("Demo database reset complete: %s", stats)
    return stats


async def seed_demo_data(
    session: AsyncSession,
    *,
    default_tenant_id: uuid.UUID,
    force: bool = False,
) -> dict[str, Any]:
    """Insert a small demo dataset on the default tenant (idempotent)."""
    from modules.base.controller.repositories import (
        CompanyRepository,
        ConfigParamRepository,
        UserRepository,
    )
    from modules.base.controller.attachment_service import AttachmentService

    ctx = RequestContext(is_superadmin=True, tenant_id=default_tenant_id)
    cfg_repo = ConfigParamRepository(session, ctx)

    if not force:
        existing, _ = await cfg_repo.search(domain=[("key", "=", DEMO_SEED_PARAM)], limit=1)
        if existing and existing[0].value == DEMO_SEED_VERSION:
            logger.info("Demo seed already applied (version %s)", DEMO_SEED_VERSION)
            return {"status": "skipped", "version": DEMO_SEED_VERSION}

    company_repo = CompanyRepository(session, ctx)
    company_ids: list[uuid.UUID] = []
    for spec in DEMO_COMPANIES:
        rec = await company_repo.create({**spec, "tenant_id": default_tenant_id})
        company_ids.append(rec.id)

    hq_id = company_ids[0]

    user_repo = UserRepository(session, ctx)
    pwd_hash = hash_password(DEMO_PASSWORD)

    for spec in DEMO_USERS:
        found, _ = await user_repo.search(domain=[("email", "=", spec.email)], limit=1)
        payload = {
            "email": spec.email,
            "name": spec.name,
            "password_hash": pwd_hash,
            "tenant_id": default_tenant_id,
            "company_id": hq_id,
            "company_ids": [str(hq_id)],
            "role_ids": list(spec.role_ids),
            "is_superadmin": spec.is_superadmin,
            "is_active": True,
            "language": "en",
            "timezone": "Europe/Warsaw",
        }
        if found:
            await user_repo.update(found[0].id, payload)
        else:
            await user_repo.create(payload)

    # Bind bootstrap admin to HQ for a coherent demo shell.
    admins, _ = await user_repo.search(
        domain=[("email", "=", settings.bootstrap_admin_email)],
        limit=1,
    )
    if admins:
        await user_repo.update(
            admins[0].id,
            {
                "tenant_id": default_tenant_id,
                "company_id": hq_id,
                "company_ids": [str(hq_id)],
            },
        )

    attachment_svc = AttachmentService(session)
    attachments_created = 0
    for att in DEMO_ATTACHMENTS:
        body = att["body"].encode("utf-8")
        await attachment_svc.upload(
            ctx,
            file_bytes=body,
            filename=att["filename"],
            mimetype=att["mimetype"],
            res_model="base.company",
            res_id=hq_id,
            description=att["description"],
        )
        attachments_created += 1

    await cfg_repo.create(
        {
            "key": DEMO_SEED_PARAM,
            "value": DEMO_SEED_VERSION,
            "description": "Demo dataset version (see orbiteus_core/demo_seed.py)",
        }
    )

    await session.commit()

    result = {
        "status": "seeded",
        "version": DEMO_SEED_VERSION,
        "tenant_id": str(default_tenant_id),
        "companies": len(company_ids),
        "demo_users": len(DEMO_USERS),
        "attachments": attachments_created,
        "demo_password": DEMO_PASSWORD,
    }
    logger.info("Demo seed applied: %s", result)
    return result


async def _purge_attachment_storage() -> None:
    """Remove all files from the configured attachment backend."""
    try:
        from orbiteus_core.storage import get_storage
        from orbiteus_core.storage.local import LocalStorage

        storage = get_storage()
        if isinstance(storage, LocalStorage):
            root = storage._root
            if root.is_dir():
                for path in sorted(root.rglob("*"), reverse=True):
                    if path.is_file():
                        path.unlink(missing_ok=True)
                    elif path.is_dir() and path != root:
                        try:
                            path.rmdir()
                        except OSError:
                            pass
    except Exception:  # noqa: BLE001
        logger.exception("attachment_storage.purge_failed")


async def run_demo_seed_pipeline(
    *,
    reset: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """Entry used by CLI and app lifespan."""
    import api  # noqa: F401 — ensure mappings loaded

    from orbiteus_core.db import AsyncSessionFactory
    from modules.base.controller.repositories import TenantRepository

    async with AsyncSessionFactory() as session:
        root_ctx = RequestContext(is_superadmin=True)
        tenant_repo = TenantRepository(session, root_ctx)
        tenants, _ = await tenant_repo.search(
            domain=[("slug", "=", settings.bootstrap_admin_tenant_slug)],
            limit=1,
        )
        if not tenants:
            tenants, _ = await tenant_repo.search(limit=1)
        if not tenants:
            raise RuntimeError("No tenant found — run app bootstrap first")

        default_tenant_id = tenants[0].id
        out: dict[str, Any] = {"tenant_id": str(default_tenant_id)}

        if reset:
            out["reset"] = await reset_demo_database(session, default_tenant_id=default_tenant_id)
            await session.commit()
            # Restore YAML access matrix after bulk-seed duplicates are wiped.
            from orbiteus_core.registry import registry

            await registry.seed_security_to_db()
            await _reload_rbac_after_demo_seed()

        out["seed"] = await seed_demo_data(
            session,
            default_tenant_id=default_tenant_id,
            force=force or reset,
        )
        return out


async def _reload_rbac_after_demo_seed() -> None:
    """Push freshly seeded YAML access rows into the RBAC cache."""
    import json

    from orbiteus_core.context import RequestContext
    from orbiteus_core.db import AsyncSessionFactory
    from orbiteus_core.security.rbac import reload_access_cache
    from modules.base.controller.repositories import ModelAccessRepository, RecordRuleRepository

    ctx = RequestContext(is_superadmin=True)
    async with AsyncSessionFactory() as session:
        access_repo = ModelAccessRepository(session, ctx)
        rule_repo = RecordRuleRepository(session, ctx)
        access_objs, _ = await access_repo.search(limit=10000)
        rule_objs, _ = await rule_repo.search(limit=10000)

        access_rows = [
            {
                "role_name": getattr(a, "role_name", ""),
                "model_name": getattr(a, "model_name", ""),
                "perm_read": getattr(a, "perm_read", False),
                "perm_write": getattr(a, "perm_write", False),
                "perm_create": getattr(a, "perm_create", False),
                "perm_unlink": getattr(a, "perm_unlink", False),
            }
            for a in access_objs
        ]

        def _to_list(val):
            if isinstance(val, list):
                return val
            if isinstance(val, str):
                try:
                    return json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    return []
            return []

        rule_rows = [
            {
                "model_name": getattr(r, "model_name", ""),
                "roles": _to_list(getattr(r, "roles", [])),
                "domain": _to_list(getattr(r, "domain_force", [])),
                "global": getattr(r, "is_global", False),
            }
            for r in rule_objs
        ]
        await reload_access_cache(access_rows, rule_rows)
