# 22 — Implementation Plan

## Phases

| Phase | Goal | Status |
|---|---|---|
| 1 — Architecture | Monorepo, Docker, module system, contracts | DONE |
| 2 — Backend (framework) | ORM, auto-CRUD, RBAC, tenant isolation, AI primitive | IN PROGRESS |
| 3 — Admin UI (framework) | Dynamic renderer, widget registry | IN PROGRESS |
| 4 — Cross-cutting | Audit, cache, events, realtime, AI layer, portal | PLANNED |
| 5 — Canonical CRM | Person / Lead / Stage / Team + AI demo | PLANNED |

## Wave priorities

### Wave 1 — Foundations (unblocks everything else)
1. Repository hooks (before/after CRUD)
2. `created_by_id` / `modified_by_id` columns
3. Audit log (mandatory, opt-out)
4. EventBus + Outbox
5. Move `_seed_crm_defaults` from `api.py` lifespan to `modules/crm/bootstrap.py`
6. Migrate service in compose; advisory lock in Alembic

### Wave 2 — Cross-cutting infra
1. Redis cache layer (RBAC + jti revocation + presence + rate limit)
2. Celery worker + beat
3. Realtime (SSE + Redis Pub/Sub backplane)
4. nginx config for SSE
5. PgBouncer in compose

### Wave 3 — AI layer (BYOK, ready-to-go)
1. `base_ai_credential` table + Fernet encryption
2. Provider abstraction (Anthropic, OpenAI, Ollama)
3. `AIModuleConfig` registry + `ai.py` convention
4. `<PromptInput>` widget in `admin-ui/src/orbiteus-ui`
5. `pgvector` + `base_embedding` + Outbox-driven reindex

### Wave 4 — Canonical CRM (MVP)
1. Rename Customer→Person, Opportunity→Lead, drop Pipeline, add Team
2. Calendar view for `crm.lead`
3. Statusbar widget for `crm.lead.stage`
4. Many2one resolution in API + widget on UI
5. Demo `ai.py` with sample prompts and dashboards

### Wave 5 — Portal (external partner UI)
1. Scaffold `portal-ui/` Next.js app
2. Share-link issuance endpoint
3. `<portal>` view declaration in modules
4. Comments and limited-action surface
5. Strict CSP and CORS for portal origin

### Wave 6 — Operational hardening
1. Observability (Prometheus + structured logs + OTel)
2. Rate limiting (token buckets) end to end
3. Backups (pg_dump cron + S3 target)
4. Multi-host migration guide validated against k8s test cluster

### Wave 7 — Agent UX and domain apps (2026-05)
1. Repositioning docs + ADR-0021 (domain-first, not ERP-first)
2. TanStack Query data layer in admin-ui (ADR-0020)
3. Spec-driven agent workflow (`docs/39`, `modules-spec-template.md`)
4. Reference product doc (`docs/40-reference-product-caltrain.md`)
5. GET one `?expand=` for form many2one labels
6. CRM as sole in-repo showcase domain module; Tier B = optional feature routes in admin-ui (ADR-0021)

## Tracking

Concrete checkboxes live in:

- `23-tree-spec-framework.md` (backend)
- `24-tree-spec-admin-ui.md` (admin)
- `25-tree-spec-portal-ui.md` (portal)

Each tree-spec lists items with `[ ]` / `[x]` and `depends_on` references to ADRs
or other items. Cross-cutting waves have items in multiple tree-specs.

## Definition of "Done" per wave

A wave is done when:

- All items in the wave's tree-spec rows are `[x]`.
- Tests cover at least 80% of new lines.
- CHANGELOG entry written.
- Relevant doc files updated.
- ADRs created or amended.

## What is explicitly NOT in MVP

- Temporal (use Outbox + Celery — ADR `0015`)
- arq / dramatiq / RQ (Celery is the choice — ADR `0013`)
- Granian / Hypercorn (Gunicorn + UvicornWorker — ADR `0011`)
- Kubernetes (single-host compose runs — see `32-multi-host-migration.md`)
- ElasticSearch (Postgres + RapidFuzz + pgvector cover the cases)
- Second design system

These return only with their own ADR and a concrete need.
