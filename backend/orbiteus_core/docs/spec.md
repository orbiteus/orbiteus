# orbiteus_core — module spec

> **Superseded by `docs/`.** This file is kept for in-tree readability next
> to the source. The authoritative engine documentation lives in the
> top-level `docs/` chapters; pointers below.
>
> **Canonical sources:**
> - `docs/02-architecture.md` — modular monolith, 3-layer model
> - `docs/04-data-model.md` — `BaseModel` / `SystemModel` / `base_*`
> - `docs/05-rbac-multitenancy.md` — 5-level RBAC + `tenant_id`
> - `docs/12-events-and-queues.md` — EventBus + Outbox + Celery
> - `docs/14-audit.md` — mandatory audit policy
> - `docs/15-ai-layer.md` — provider adapters, BYOK, tools, embeddings

## Responsibilities

`orbiteus_core` is the framework layer (no business code). It provides:

- **Module Registry** — topological sort of `modules/<name>/manifest.py`,
  install + bootstrap orchestration.
- **`BaseRepository`** — auto tenant filter, RBAC enforcement, soft delete,
  `created_by` / `modified_by` attribution, before/after hooks, mandatory
  audit log.
- **`AutoRouter`** — generates list/get/create/update/delete + `/aggregate`
  CRUD endpoints from a model + Pydantic Read/Write schemas.
- **`ui-config`** — registry-driven UI metadata served at
  `GET /api/base/ui-config`; the Admin UI catch-all routes render it.
- **Auth + RBAC** — JWT (HS256) + bcrypt, JTI revocation in Redis, TOTP
  + recovery codes, httpOnly cookie session for the browser
  ([ADR-0017](../../../../docs/adr/0017-httponly-cookie-session.md)),
  five-level RBAC (`base_model_access`, `base_rule`, action RBAC, field-level,
  scope).
- **Audit log** (`base_audit_log`) — mandatory, opt-out via
  `AUDIT_OPTOUT_MODELS`; per-field diff on every CRUD.
- **EventBus** (in-process, sync) + **Postgres Outbox** (`base_outbox`)
  drained by Celery for durable side effects (webhooks, embeddings,
  email).
- **Cache** — Redis abstraction (`Cache`, `get_redis`, `get_cache`).
- **Realtime** — SSE endpoint `/api/realtime/subscribe` + Redis Pub/Sub
  backplane.
- **AI layer** — provider ABC (Anthropic, OpenAI, Ollama), BYOK
  (`base_ai_credentials`, Fernet at-rest), embeddings (`base_embeddings`,
  pgvector + HNSW), per-tenant token budgets in Redis, redaction.
- **Observability** — JSON logging with `request_id` / `tenant_id` /
  `actor` ContextVars, Prometheus `/metrics`, OpenTelemetry tracing
  (opt-in).

## Layering rules

- Modules **never** import each other (`from modules.crm…` inside
  `modules/hr` is forbidden). They communicate via UUID FKs, public
  services exposed by `orbiteus_core`, and the EventBus / Outbox.
- The AI layer calls the same `BaseRepository` as the UI; AI never
  bypasses RBAC.
- Heavy work (embeddings refresh, webhook delivery) goes through Celery
  via the Outbox — never inline.

## Status

100% Definition of Done at v1.0. See
`docs/34-inventory-and-status.md` for the per-feature matrix and
`docs/35-core-definition-of-done.md` for the release checklist.
