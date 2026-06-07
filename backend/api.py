"""ERP Backend – FastAPI application entry point.

Module registration order matters – dependencies must be registered first.
ModuleRegistry handles topological sorting automatically.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from orbiteus_core.config import settings
from orbiteus_core.health import router as health_router
from orbiteus_core.observability import (
    RequestIdMiddleware,
    configure_json_logging,
    metrics_endpoint,
)
from orbiteus_core.registry import registry

# Structured JSON logs with request_id correlation (docs/29-observability.md).
configure_json_logging(level="INFO" if not settings.debug else "DEBUG")
logger = logging.getLogger(__name__)

_BRANDING_DEFAULTS = [
    ("app.name", "Orbiteus", "Application display name"),
    ("app.logo_url", "/branding/logo.svg", "URL to logo image (leave empty to use text name)"),
    ("app.favicon_url", "/branding/logo.svg", "URL to favicon"),
]

_DEFAULT_SUPERADMIN_EMAIL = settings.bootstrap_admin_email
_DEFAULT_SUPERADMIN_PASSWORD = settings.bootstrap_admin_password
_DEFAULT_TENANT_NAME = settings.bootstrap_admin_tenant_name
_DEFAULT_TENANT_SLUG = settings.bootstrap_admin_tenant_slug
# Product seeds (e.g. CRM default stages) live in the module's `bootstrap.py`,
# not in the engine lifespan. See `modules/crm/bootstrap.py` (PR 9 / ADR-0008).


async def _create_tables() -> None:
    """Create all registered SQLAlchemy tables if they don't exist."""
    from orbiteus_core.db import engine, metadata

    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    logger.info("Database tables created (if not exist).")


async def _seed_default_tenant() -> "uuid.UUID":  # type: ignore[name-defined]
    """Ensure at least one Tenant row exists; return its id.

    Multi-tenancy is on by default (`docs/05-rbac-multitenancy.md`); without
    a tenant the bootstrap admin gets `tenant_id = NULL`, which then breaks
    every endpoint that requires tenant context (AI BYOK, share-link issue,
    portal-scope tokens, audit attribution).
    """
    from orbiteus_core.context import RequestContext
    from orbiteus_core.db import AsyncSessionFactory
    from modules.base.controller.repositories import TenantRepository

    ctx = RequestContext(is_superadmin=True)
    async with AsyncSessionFactory() as session:
        repo = TenantRepository(session, ctx)
        existing, total = await repo.search(limit=1)
        if total > 0 and existing:
            return existing[0].id

        tenant = await repo.create({
            "name": _DEFAULT_TENANT_NAME,
            "slug": _DEFAULT_TENANT_SLUG,
            "plan": "free",
            "is_active": True,
        })
        await session.commit()
        logger.info(
            "Bootstrap default tenant created: name=%s slug=%s id=%s",
            tenant.name, tenant.slug, tenant.id,
        )
        return tenant.id


async def _seed_superadmin(default_tenant_id: "uuid.UUID") -> None:  # type: ignore[name-defined]
    """Create a default superadmin user on first startup if no users exist.

    Also backfills `tenant_id` on a pre-existing admin row so installations
    that bootstrapped before the default-tenant change don't stay stuck
    without a tenant binding.
    """
    from orbiteus_core.context import RequestContext
    from orbiteus_core.db import AsyncSessionFactory
    from orbiteus_core.security.passwords import hash_password
    from modules.base.controller.repositories import UserRepository

    ctx = RequestContext(is_superadmin=True)
    async with AsyncSessionFactory() as session:
        repo = UserRepository(session, ctx)
        existing, total = await repo.search(limit=1)
        if total == 0:
            if settings.environment.lower() == "production" and _DEFAULT_SUPERADMIN_PASSWORD == "admin1234":
                raise RuntimeError(
                    "Refusing to create bootstrap superadmin with default password in production."
                )
            await repo.create({
                "tenant_id": default_tenant_id,
                "email": _DEFAULT_SUPERADMIN_EMAIL,
                "name": "Administrator",
                "password_hash": hash_password(_DEFAULT_SUPERADMIN_PASSWORD),
                "is_superadmin": True,
                "is_active": True,
                "language": "en",
                "company_ids": [],
                "role_ids": [],
            })
            await session.commit()
            logger.warning(
                "Default superadmin created: email=%s password=%s tenant=%s "
                "— CHANGE THIS IN PRODUCTION!",
                _DEFAULT_SUPERADMIN_EMAIL,
                _DEFAULT_SUPERADMIN_PASSWORD,
                default_tenant_id,
            )
            return

        # Backfill: a superadmin from the pre-default-tenant era has
        # `tenant_id IS NULL`; bind it to the default tenant so AI BYOK
        # and other tenant-scoped endpoints start working without a
        # manual SQL fix.
        admin = next(
            (u for u in existing if getattr(u, "is_superadmin", False) and u.tenant_id is None),
            None,
        )
        if admin is not None:
            await repo.update(admin.id, {"tenant_id": default_tenant_id})
            await session.commit()
            logger.warning(
                "Bound legacy superadmin %s to default tenant %s "
                "(retroactive multi-tenancy fix).",
                admin.email, default_tenant_id,
            )


async def _maybe_apply_demo_seed() -> None:
    """Optional curated demo dataset (``SEED_DEMO_DATA`` / ``RESET_DEMO_DATA``)."""
    if not settings.seed_demo_data and not settings.reset_demo_data:
        return
    if settings.environment.lower() == "production" and settings.reset_demo_data:
        logger.error("RESET_DEMO_DATA is disabled in production — skipping demo reset")
        return
    from orbiteus_core.demo_seed import run_demo_seed_pipeline

    try:
        result = await run_demo_seed_pipeline(
            reset=settings.reset_demo_data,
            force=settings.reset_demo_data,
        )
        logger.info("Demo seed pipeline finished: %s", result.get("seed", result))
    except Exception:
        logger.exception("demo_seed.pipeline_failed")


async def _seed_default_roles() -> None:
    """Ensure built-in RBAC roles exist (idempotent)."""
    from orbiteus_core.context import RequestContext
    from orbiteus_core.db import AsyncSessionFactory
    from modules.base.roles_seed import seed_default_roles

    ctx = RequestContext(is_superadmin=True)
    async with AsyncSessionFactory() as session:
        await seed_default_roles(session, ctx)
        await session.commit()


async def _seed_default_agents(default_tenant_id: "uuid.UUID") -> None:  # type: ignore[name-defined]
    """Ensure showcase AI agents exist for the default tenant (idempotent)."""
    from orbiteus_core.db import AsyncSessionFactory
    from modules.base.agents_seed import seed_default_agents

    async with AsyncSessionFactory() as session:
        await seed_default_agents(session, tenant_id=default_tenant_id)
        await session.commit()


async def _seed_branding() -> None:
    """Insert default branding params if not present."""
    from orbiteus_core.context import RequestContext
    from orbiteus_core.db import AsyncSessionFactory
    from modules.base.controller.repositories import ConfigParamRepository

    ctx = RequestContext(is_superadmin=True)
    async with AsyncSessionFactory() as session:
        repo = ConfigParamRepository(session, ctx)
        for key, value, description in _BRANDING_DEFAULTS:
            existing, _ = await repo.search(domain=[("key", "=", key)], limit=1)
            if not existing:
                await repo.create({"key": key, "value": value, "description": description})
        await session.commit()


async def _reload_rbac_cache() -> None:
    """Load RBAC access entries and record rules into in-memory cache."""
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

        # Convert domain objects to dicts for the RBAC cache
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
        # Persists to Redis + bumps version + publishes `rbac.invalidate`
        # so other replicas refresh their L1 cache.
        await reload_access_cache(access_rows, rule_rows)


def _seed_auto_actions() -> None:
    """Auto-register `<model>.list` / `<model>.create` actions for every
    model exposed via `auto_router._model_registry`.

    These actions populate the Cmd+K Command Palette out of the box, so a
    new business module that adds models doesn't have to also write an
    `actions.py`. Module-defined actions take precedence — only ids that
    aren't already registered are added (so the curated CRM keywords in
    `modules/crm/actions.py` keep their hand-tuned labels and synonyms).
    """
    from orbiteus_core.ai.action import Action, ActionCategory
    from orbiteus_core.ai.registry import action_registry
    from orbiteus_core.auto_router import _model_registry

    existing: set[str] = {a.id for a in action_registry.get_all()}
    auto_count = 0

    for mod_name in registry.loaded_modules:
        try:
            desc = registry.get_module(mod_name)
        except Exception:
            continue

        for model_name in desc.manifest.get("models", []):
            if model_name not in _model_registry:
                continue

            # `crm.person` → segment `person`; `base.registry-model` → `ir-model`.
            segment = model_name.split(".", 1)[1] if "." in model_name else model_name
            label = segment.replace("-", " ").replace("_", " ").title()
            list_id = f"{model_name}.list"
            create_id = f"{model_name}.create"

            if list_id not in existing:
                action_registry.register_module(mod_name, [Action(
                    id=list_id,
                    label=label,
                    keywords=[
                        label.lower(),
                        f"list of {label.lower()}",
                        segment,
                        model_name,
                    ],
                    description=f"Open the {label} list view",
                    category=ActionCategory.NAVIGATE,
                    target="navigate",
                    target_url=f"/{mod_name}/{segment}",
                    requires_feature=f"{model_name}.view",
                    icon="list",
                )])
                auto_count += 1

            if create_id not in existing:
                action_registry.register_module(mod_name, [Action(
                    id=create_id,
                    label=f"Create {label}",
                    keywords=[
                        f"new {label.lower()}",
                        f"add {label.lower()}",
                        f"create {label.lower()}",
                    ],
                    description=f"Open the form to create a new {label.lower()} record",
                    category=ActionCategory.CREATE,
                    target="navigate",
                    target_url=f"/{mod_name}/{segment}/new",
                    requires_feature=f"{model_name}.create",
                    icon="plus",
                )])
                auto_count += 1

    if auto_count:
        logger.info(
            "Auto-registered %d CRUD actions in the Command Palette "
            "(modules: %s).",
            auto_count, ", ".join(registry.loaded_modules),
        )


async def _bootstrap_modules(tenant_id: "uuid.UUID | None" = None) -> None:
    """Run each module's `bootstrap.on_install()` once per fresh tenant.

    Replaces the legacy `_seed_crm_defaults` (PR 9 / ADR-0008). Modules
    declare their bootstrap path in `manifest.MANIFEST["bootstrap"]`.
    """
    import importlib

    from orbiteus_core.context import RequestContext
    from orbiteus_core.db import AsyncSessionFactory

    ctx = RequestContext(is_superadmin=True, tenant_id=tenant_id)
    bootstrap_paths: list[str] = []
    for mod_name in registry.loaded_modules:
        try:
            manifest_mod = importlib.import_module(f"modules.{mod_name}.manifest")
        except ModuleNotFoundError:
            continue
        path = getattr(manifest_mod, "MANIFEST", {}).get("bootstrap")
        if path:
            bootstrap_paths.append(path)

    if not bootstrap_paths:
        return

    async with AsyncSessionFactory() as session:
        for path in bootstrap_paths:
            try:
                module = importlib.import_module(path)
                if hasattr(module, "on_install"):
                    await module.on_install(session, ctx)
            except Exception:
                # `module` is reserved on LogRecord; use a custom key.
                logger.exception("module.bootstrap.failed", extra={"module_path": path})


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    await _create_tables()
    default_tenant_id = await _seed_default_tenant()
    await _seed_superadmin(default_tenant_id)
    await _seed_default_roles()
    await _seed_default_agents(default_tenant_id)
    await _seed_branding()
    await registry.seed_security_to_db()
    await registry.seed_views_to_db()
    await _bootstrap_modules(default_tenant_id)
    await registry.seed_registry_to_db()
    await _maybe_apply_demo_seed()
    # Pull RBAC matrix from DB and push to Redis (+ publish invalidate so
    # other replicas refresh their L1).
    await _reload_rbac_cache()
    from orbiteus_core.attachment_dispatcher import register_attachment_dispatcher

    register_attachment_dispatcher()
    # Wire EventBus → RBAC reload bridge so any future mutation of
    # base_model_access / base_rules in any replica fans out invalidation.
    from orbiteus_core.security.rbac import register_rbac_invalidator, start_invalidator
    register_rbac_invalidator()
    # Background pub/sub listener — refreshes L1 cache cross-replica
    # within ~50ms of any rbac.invalidate notification.
    await start_invalidator()
    # Auto-register CRUD actions in the Command Palette for every model
    # exposed by the registry. Module-curated actions in `actions.py` win
    # on id collisions; everything else gets a generic
    # `<model>.list` / `<model>.create` pair.
    _seed_auto_actions()
    logger.info("Startup complete — RBAC cache loaded.")
    yield
    # Cleanly stop the background pub/sub listener so we don't leak a task.
    from orbiteus_core.security.rbac import stop_invalidator
    await stop_invalidator()
    logger.info("Shutting down.")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="Composable ERP Engine",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request-id, access log, Prometheus counters/histograms (docs/29).
    app.add_middleware(RequestIdMiddleware)

    # IP rate limit (PR 6). Tenant/user buckets are checked deeper in the stack
    # because JWT is decoded later (security.middleware).
    from orbiteus_core.security.rate_limit_middleware import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware)

    # Health and metrics endpoints
    app.include_router(health_router)
    app.add_api_route("/metrics", metrics_endpoint, methods=["GET"], include_in_schema=False)

    # ---------------------------------------------------------------------------
    # Register modules (order matters for depends_on – registry sorts them)
    # ---------------------------------------------------------------------------
    registry.register("base")
    registry.register("locales")
    registry.register("auth")

    # Bootstrap: load mappings, register routes, seed security
    registry.bootstrap(app)

    # Wire the outbox dispatcher onto record.* events (PR 4 / ADR-0010).
    from orbiteus_core.outbox_dispatcher import register_dispatchers
    register_dispatchers()

    from orbiteus_core.embedding_dispatcher import register_embedding_dispatcher
    register_embedding_dispatcher()

    # Wire the realtime publishers (PR 7 / ADR-0006, ADR-0014).
    from orbiteus_core.realtime import register_realtime_publishers
    from orbiteus_core.realtime_router import router as realtime_router
    register_realtime_publishers()
    app.include_router(realtime_router)

    # External portal (share-link exchange). PR 12 / ADR-0007.
    from orbiteus_core.portal_router import router as portal_router
    app.include_router(portal_router)

    # OpenTelemetry instrumentation (no-op unless OTEL_EXPORTER_OTLP_ENDPOINT set).
    from orbiteus_core.observability.tracing import setup_tracing
    setup_tracing(app)

    # AI-native layer — Command Palette endpoint
    from orbiteus_core.ai.router import router as ai_router
    app.include_router(ai_router)

    logger.info("Orbiteus application ready.")
    return app


app = create_app()
