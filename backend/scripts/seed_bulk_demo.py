"""Seed bulk demo data: ~100 rows for every current ORM model.

Scope:
- base: tenant, company, partner, user
- base system: ir_model, ir_model_field, ir_model_access, ir_rule, ir_ui_menu,
  ir_action_window, ir_action_server, ir_sequence, ir_config_param, ir_cron,
  ir_mail_template, ir_ui_view, ir_attachment
- crm: customer, pipeline, stage, opportunity

Usage:
  cd backend
  SEED_COUNT=100 python3 -m scripts.seed_bulk_demo
"""
from __future__ import annotations

import asyncio
import os
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import api  # noqa: F401 - ensure mappings/registry are bootstrapped
from sqlalchemy import insert

from modules.base.controller.repositories import (
    CompanyRepository,
    IrConfigParamRepository,
    IrCronRepository,
    IrModelAccessRepository,
    IrModelFieldRepository,
    IrModelRepository,
    IrRuleRepository,
    IrSequenceRepository,
    IrUiMenuRepository,
    IrUiViewRepository,
    PartnerRepository,
    TenantRepository,
    UserRepository,
)
from modules.base.model.mapping import (
    ir_action_servers_table,
    ir_action_windows_table,
    ir_attachments_table,
    ir_mail_templates_table,
)
from modules.crm.controller.repositories import (
    CustomerRepository,
    OpportunityRepository,
    PipelineRepository,
    StageRepository,
)
from orbiteus_core.context import RequestContext
from orbiteus_core.db import AsyncSessionFactory
from orbiteus_core.security.passwords import hash_password

COUNT = int(os.environ.get("SEED_COUNT", "100"))
BATCH = os.environ.get("SEED_BATCH", uuid.uuid4().hex[:10])
CRM_STANDARD_STAGES = [
    {"name": "Lead", "sequence": 10, "probability": 10.0, "is_won": False, "is_lost": False, "fold": False},
    {"name": "Qualified", "sequence": 20, "probability": 30.0, "is_won": False, "is_lost": False, "fold": False},
    {"name": "Proposition", "sequence": 30, "probability": 55.0, "is_won": False, "is_lost": False, "fold": False},
    {"name": "Negotiation", "sequence": 40, "probability": 75.0, "is_won": False, "is_lost": False, "fold": False},
    {"name": "Won", "sequence": 90, "probability": 100.0, "is_won": True, "is_lost": False, "fold": True},
    {"name": "Lost", "sequence": 100, "probability": 0.0, "is_won": False, "is_lost": True, "fold": True},
]


def _u(i: int) -> str:
    return f"{i + 1:04d}"


async def _run() -> None:
    created: dict[str, int] = defaultdict(int)
    pwd = hash_password("seed1234")
    now = datetime.now(timezone.utc)

    async with AsyncSessionFactory() as session:
        root_ctx = RequestContext(is_superadmin=True)

        t_repo = TenantRepository(session, root_ctx)
        c_repo = CompanyRepository(session, root_ctx)
        p_repo = PartnerRepository(session, root_ctx)
        u_repo = UserRepository(session, root_ctx)

        irm_repo = IrModelRepository(session, root_ctx)
        irmf_repo = IrModelFieldRepository(session, root_ctx)
        irma_repo = IrModelAccessRepository(session, root_ctx)
        irr_repo = IrRuleRepository(session, root_ctx)
        irmenu_repo = IrUiMenuRepository(session, root_ctx)
        irseq_repo = IrSequenceRepository(session, root_ctx)
        ircfg_repo = IrConfigParamRepository(session, root_ctx)
        ircron_repo = IrCronRepository(session, root_ctx)
        irview_repo = IrUiViewRepository(session, root_ctx)

        cust_repo = CustomerRepository(session, root_ctx)
        pipe_repo = PipelineRepository(session, root_ctx)
        stage_repo = StageRepository(session, root_ctx)
        opp_repo = OpportunityRepository(session, root_ctx)

        tenants: list[uuid.UUID] = []
        companies: list[uuid.UUID] = []
        partners: list[uuid.UUID] = []
        users: list[uuid.UUID] = []
        ir_models: list[uuid.UUID] = []
        pipelines: list[uuid.UUID] = []
        stages: list[uuid.UUID] = []
        customers: list[uuid.UUID] = []

        # base.tenant (100)
        for i in range(COUNT):
            rec = await t_repo.create(
                {
                    "name": f"Seed Tenant {BATCH}-{_u(i)}",
                    "slug": f"seed-{BATCH}-tenant-{_u(i)}",
                    "plan": ["free", "starter", "professional", "enterprise"][i % 4],
                    "is_active": True,
                    "settings": {"batch": BATCH, "idx": i + 1},
                }
            )
            tenants.append(rec.id)
            created["base.tenant"] += 1

        # base.company (100)
        for i in range(COUNT):
            ctx = RequestContext(is_superadmin=True, tenant_id=tenants[i])
            repo = CompanyRepository(session, ctx)
            rec = await repo.create(
                {
                    "name": f"Seed Company {BATCH}-{_u(i)}",
                    "tenant_id": tenants[i],
                    "currency_code": ["PLN", "EUR", "USD"][i % 3],
                    "country_code": "PL",
                    "city": ["Warsaw", "Krakow", "Poznan", "Gdansk"][i % 4],
                    "street": f"Seed Street {i + 1}",
                    "zip_code": f"{i%99+1:02d}-{i%999:03d}",
                    "email": f"company-{BATCH}-{_u(i)}@example.com",
                    "phone": f"+48 500 {i%1000:03d} {((i*7)%1000):03d}",
                }
            )
            companies.append(rec.id)
            created["base.company"] += 1

        # base.partner (100)
        for i in range(COUNT):
            ctx = RequestContext(is_superadmin=True, tenant_id=tenants[i], company_id=companies[i])
            repo = PartnerRepository(session, ctx)
            rec = await repo.create(
                {
                    "name": f"Seed Partner {BATCH}-{_u(i)}",
                    "tenant_id": tenants[i],
                    "company_id": companies[i],
                    "email": f"partner-{BATCH}-{_u(i)}@example.com",
                    "phone": f"+48 601 {i%1000:03d} {((i*11)%1000):03d}",
                    "mobile": f"+48 602 {i%1000:03d} {((i*13)%1000):03d}",
                    "city": ["Warsaw", "Wroclaw", "Lodz", "Szczecin"][i % 4],
                    "country_code": "PL",
                    "is_company": i % 2 == 0,
                }
            )
            partners.append(rec.id)
            created["base.partner"] += 1

        # base.user (100)
        for i in range(COUNT):
            ctx = RequestContext(is_superadmin=True, tenant_id=tenants[i], company_id=companies[i])
            repo = UserRepository(session, ctx)
            rec = await repo.create(
                {
                    "email": f"user-{BATCH}-{_u(i)}@seed.example.com",
                    "name": f"Seed User {BATCH}-{_u(i)}",
                    "password_hash": pwd,
                    "tenant_id": tenants[i],
                    "company_id": companies[i],
                    "partner_id": partners[i],
                    "company_ids": [str(companies[i])],
                    "role_ids": [],
                    "is_superadmin": False,
                    "language": ["en", "pl", "de"][i % 3],
                    "timezone": ["Europe/Warsaw", "UTC", "Europe/Berlin"][i % 3],
                }
            )
            users.append(rec.id)
            created["base.user"] += 1

        # base.ir-model (100)
        for i in range(COUNT):
            rec = await irm_repo.create(
                {
                    "model_name": f"x.seed.{BATCH}.model.{_u(i)}",
                    "label": f"Seed Model {_u(i)}",
                    "module": "seed",
                    "description": f"Demo model {_u(i)} ({BATCH})",
                    "is_transient": i % 10 == 0,
                }
            )
            ir_models.append(rec.id)
            created["base.ir-model"] += 1

        # base.ir-model-field (100)
        for i in range(COUNT):
            await irmf_repo.create(
                {
                    "model_id": ir_models[i],
                    "model_name": f"x.seed.{BATCH}.model.{_u(i)}",
                    "field_name": f"x_field_{_u(i)}",
                    "field_type": ["char", "integer", "float", "boolean", "date"][i % 5],
                    "label": f"Field {_u(i)}",
                    "required": i % 2 == 0,
                    "readonly": i % 3 == 0,
                    "is_custom": True,
                    "selection_values": [{"value": "a", "label": "A"}] if i % 5 == 0 else [],
                    "related_model": None,
                }
            )
            created["base.ir-model-field"] += 1

        # base.ir-model-access (100)
        for i in range(COUNT):
            await irma_repo.create(
                {
                    "model_name": f"x.seed.{BATCH}.model.{_u(i)}",
                    "role_name": f"seed_role_{i % 20:02d}",
                    "perm_read": True,
                    "perm_write": i % 2 == 0,
                    "perm_create": i % 3 != 0,
                    "perm_unlink": i % 4 == 0,
                }
            )
            created["base.ir-model-access"] += 1

        # base.ir-rule (100)
        for i in range(COUNT):
            await irr_repo.create(
                {
                    "name": f"Seed Rule {BATCH}-{_u(i)}",
                    "model_name": f"x.seed.{BATCH}.model.{_u(i)}",
                    "domain_force": "[]",
                    "roles": [f"seed_role_{i % 20:02d}"],
                    "is_global": i % 7 == 0,
                    "perm_read": True,
                    "perm_write": i % 2 == 0,
                    "perm_create": True,
                    "perm_unlink": i % 5 == 0,
                }
            )
            created["base.ir-rule"] += 1

        # base.ir-ui-menu (100)
        parent_id: uuid.UUID | None = None
        for i in range(COUNT):
            rec = await irmenu_repo.create(
                {
                    "name": f"Seed Menu {BATCH}-{_u(i)}",
                    "parent_id": parent_id if i % 5 != 0 else None,
                    "sequence": 10 + i,
                    "action_id": None,
                    "action_type": "",
                    "icon": ["list", "settings", "folder", "chart"][i % 4],
                    "groups": ["base.group_system"] if i % 2 == 0 else [],
                    "web_icon": None,
                }
            )
            if i % 5 == 0:
                parent_id = rec.id
            created["base.ir-ui-menu"] += 1

        # base.ir-sequence (100)
        for i in range(COUNT):
            await irseq_repo.create(
                {
                    "name": f"Seed Sequence {BATCH}-{_u(i)}",
                    "code": f"seed.{BATCH}.seq.{_u(i)}",
                    "prefix": f"S{_u(i)}/",
                    "suffix": "",
                    "padding": 5 + (i % 3),
                    "number_next": 1 + i,
                    "number_increment": 1,
                    "use_date_range": i % 2 == 0,
                }
            )
            created["base.ir-sequence"] += 1

        # base.ir-config-param (100)
        for i in range(COUNT):
            await ircfg_repo.create(
                {
                    "key": f"seed.{BATCH}.param.{_u(i)}",
                    "value": f"value-{BATCH}-{_u(i)}",
                    "description": f"Seed config param {_u(i)}",
                    "groups": ["base.group_system"] if i % 2 == 0 else [],
                }
            )
            created["base.ir-config-param"] += 1

        # base.ir-cron (100)
        for i in range(COUNT):
            await ircron_repo.create(
                {
                    "name": f"Seed Cron {BATCH}-{_u(i)}",
                    "model_name": f"x.seed.{BATCH}.model.{_u(i)}",
                    "function_name": "seed.noop",
                    "args": "[]",
                    "kwargs": "{}",
                    "interval_number": (i % 12) + 1,
                    "interval_type": ["minutes", "hours", "days", "weeks"][i % 4],
                    "is_active": i % 3 != 0,
                    "next_call": (now + timedelta(days=i % 30)).isoformat(),
                    "temporal_schedule_id": f"seed-sched-{BATCH}-{_u(i)}",
                }
            )
            created["base.ir-cron"] += 1

        # base.ir-ui-view (100)
        for i in range(COUNT):
            await irview_repo.create(
                {
                    "name": f"seed.{BATCH}.view.{_u(i)}",
                    "model": f"x.seed.{BATCH}.model.{_u(i)}",
                    "type": ["form", "list", "kanban", "search"][i % 4],
                    "arch": "<view><field name='name'/></view>",
                    "inherit_id": None,
                    "priority": 16 + (i % 5),
                    "active": True,
                    "module": "seed",
                }
            )
            created["base.ir-ui-view"] += 1

        # base.ir-action-window (100) -- mapped ORM model without repository class
        await session.execute(
            insert(ir_action_windows_table),
            [
                {
                    "name": f"Seed Window Action {BATCH}-{_u(i)}",
                    "model_name": f"x.seed.{BATCH}.model.{_u(i)}",
                    "view_mode": ["list,form", "kanban,form", "calendar,list,form"][i % 3],
                    "domain": "[]",
                    "context": "{}",
                    "target": ["current", "new"][i % 2],
                    "create_date": now,
                    "write_date": now,
                }
                for i in range(COUNT)
            ],
        )
        created["base.ir-action-window"] += COUNT

        # base.ir-action-server (100) -- mapped ORM model without repository class
        await session.execute(
            insert(ir_action_servers_table),
            [
                {
                    "name": f"Seed Server Action {BATCH}-{_u(i)}",
                    "model_name": f"x.seed.{BATCH}.model.{_u(i)}",
                    "code": "return None",
                    "action_type": ["code", "temporal_workflow"][i % 2],
                    "workflow_name": f"seed.workflow.{_u(i)}" if i % 2 else None,
                    "create_date": now,
                    "write_date": now,
                }
                for i in range(COUNT)
            ],
        )
        created["base.ir-action-server"] += COUNT

        # base.ir-mail-template (100) -- mapped ORM model without repository class
        await session.execute(
            insert(ir_mail_templates_table),
            [
                {
                    "name": f"Seed Mail Template {BATCH}-{_u(i)}",
                    "model_name": f"x.seed.{BATCH}.model.{_u(i)}",
                    "subject": f"Seed subject {i + 1}",
                    "body_html": f"<p>Hello from seed batch {BATCH} #{i + 1}</p>",
                    "from_email": "noreply@seed.example.com",
                    "reply_to": "support@seed.example.com",
                    "lang": ["en", "pl", "de"][i % 3],
                    "auto_delete": i % 2 == 0,
                    "create_date": now,
                    "write_date": now,
                }
                for i in range(COUNT)
            ],
        )
        created["base.ir-mail-template"] += COUNT

        # crm.customer (100)
        for i in range(COUNT):
            ctx = RequestContext(is_superadmin=True, tenant_id=tenants[0], company_id=companies[0])
            repo = CustomerRepository(session, ctx)
            rec = await repo.create(
                {
                    "name": f"Seed Customer {BATCH}-{_u(i)}",
                    "tenant_id": tenants[0],
                    "company_id": companies[0],
                    "email": f"customer-{BATCH}-{_u(i)}@example.com",
                    "phone": f"+48 603 {i%1000:03d} {((i*5)%1000):03d}",
                    "mobile": f"+48 604 {i%1000:03d} {((i*17)%1000):03d}",
                    "website": f"https://seed-{BATCH}-{_u(i)}.example.com",
                    "city": ["Warsaw", "Krakow", "Wroclaw", "Poznan"][i % 4],
                    "country_code": "PL",
                    "is_company": i % 2 == 0,
                    "status": ["lead", "prospect", "customer", "churned"][i % 4],
                    "assigned_user_id": users[0],
                    "partner_id": partners[0],
                    "tags": ["seed", f"group-{i % 10}"],
                    "notes": f"Seed note {i + 1}",
                }
            )
            customers.append(rec.id)
            created["crm.customer"] += 1

        # crm.pipeline (100) — one default pipeline with standard stages + additional custom pipelines
        default_pipeline_id: uuid.UUID | None = None
        for i in range(COUNT):
            tenant_idx = i if i < len(tenants) else 0
            ctx = RequestContext(
                is_superadmin=True,
                tenant_id=tenants[tenant_idx],
                company_id=companies[tenant_idx],
            )
            repo = PipelineRepository(session, ctx)
            rec = await repo.create(
                {
                    "name": "Sales Pipeline" if i == 0 else f"Seed Pipeline {BATCH}-{_u(i)}",
                    "tenant_id": tenants[tenant_idx],
                    "company_id": companies[tenant_idx],
                    "description": "Default CRM pipeline with standard stages" if i == 0 else f"Seed pipeline {_u(i)}",
                    "currency_code": ["PLN", "EUR", "USD"][i % 3],
                    "is_default": i == 0,
                }
            )
            if i == 0:
                default_pipeline_id = rec.id
            pipelines.append(rec.id)
            created["crm.pipeline"] += 1

        # crm.stage (standard) — fixed, reusable stages for default pipeline
        if default_pipeline_id is not None:
            default_ctx = RequestContext(is_superadmin=True, tenant_id=tenants[0], company_id=companies[0])
            repo = StageRepository(session, default_ctx)
            for stage_def in CRM_STANDARD_STAGES:
                rec = await repo.create(
                    {
                        "name": stage_def["name"],
                        "tenant_id": tenants[0],
                        "company_id": companies[0],
                        "pipeline_id": default_pipeline_id,
                        "sequence": stage_def["sequence"],
                        "probability": stage_def["probability"],
                        "is_won": stage_def["is_won"],
                        "is_lost": stage_def["is_lost"],
                        "fold": stage_def["fold"],
                    }
                )
                stages.append(rec.id)
                created["crm.stage"] += 1

        # crm.opportunity (100)
        for i in range(COUNT):
            ctx = RequestContext(is_superadmin=True, tenant_id=tenants[0], company_id=companies[0])
            repo = OpportunityRepository(session, ctx)
            await repo.create(
                {
                    "name": f"Seed Opportunity {BATCH}-{_u(i)}",
                    "tenant_id": tenants[0],
                    "company_id": companies[0],
                    "customer_id": customers[i],
                    "pipeline_id": default_pipeline_id,
                    "stage_id": stages[i % len(stages)] if stages else None,
                    "assigned_user_id": users[0],
                    "expected_revenue": float(1000 + (i * 137) % 50000),
                    "probability": float(CRM_STANDARD_STAGES[i % len(CRM_STANDARD_STAGES)]["probability"]),
                    "close_date": (now + timedelta(days=(i % 120))).isoformat(),
                    "description": f"Bulk demo row {i + 1}",
                    "lost_reason": "Price" if CRM_STANDARD_STAGES[i % len(CRM_STANDARD_STAGES)]["is_lost"] else "",
                    "tags": ["seed", f"prio-{i % 5}"],
                    "workflow_run_id": None,
                }
            )
            created["crm.opportunity"] += 1

        # base.ir-attachment (100) -- mapped ORM model without repository class
        await session.execute(
            insert(ir_attachments_table),
            [
                {
                    "tenant_id": tenants[i],
                    "company_id": companies[i],
                    "name": f"Seed Attachment {BATCH}-{_u(i)}.txt",
                    "res_model": "crm.customer",
                    "res_id": customers[i],
                    "mimetype": "text/plain",
                    "file_size": 100 + i,
                    "store_fname": f"seed/{BATCH}/{_u(i)}.txt",
                    "url": None,
                    "description": f"Seed attachment {_u(i)}",
                    "create_date": now,
                    "write_date": now,
                    "active": True,
                    "custom_fields": {},
                }
                for i in range(COUNT)
            ],
        )
        created["base.ir-attachment"] += COUNT

        await session.commit()

    print(f"OK: seeded batch={BATCH}, count={COUNT} per model")
    for k in sorted(created.keys()):
        print(f"  - {k}: {created[k]}")
    print(f"Sample login: user-{BATCH}-0001@seed.example.com / seed1234")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
