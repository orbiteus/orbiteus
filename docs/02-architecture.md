# 02 — Architecture

## Three deployment artifacts, one codebase

```
+---------------------------+     +---------------------------+
|   admin-ui (Next.js 16)   |     |   portal-ui (Next.js 16)  |
|   internal users (RBAC)   |     |   external users / share  |
+-------------+-------------+     +-------------+-------------+
              |  /api/* (admin-ui: server proxy; portal: rewrites)          |
              v                                  v
+------------------------------------------------------------------+
|  FastAPI behind Gunicorn + UvicornWorker (modular monolith)      |
|                                                                  |
|  orbiteus_core: registry, BaseRepository, AutoRouter, ui-config, |
|                 JWT/RBAC, Audit, EventBus, Outbox, Cache,        |
|                 Realtime (SSE), AI Layer, Sequences, Attachments |
|                                                                  |
|  modules:       base, auth, crm (canonical), hr/project/social  |
+----------+----------------------+--------------------+-----------+
           |                      |                    |
+----------v---------+  +---------v--------+  +--------v---------+
|  PostgreSQL 16     |  |  Redis 7         |  |  Celery workers  |
|  + pgvector        |  |  cache, pub/sub  |  |  + Celery Beat   |
|  via PgBouncer     |  |  rate limit, jti |  |  (broker: Redis) |
+--------------------+  +------------------+  +------------------+
```

## Modular monolith — rules

- **One process tree** in production (multiple replicas of the same image).
- Modules are **physical directories** (`backend/modules/<name>/`) with explicit
  `manifest.py` declaring `depends_on`.
- Modules **do not import each other**. They communicate through:
  - UUID FKs (data references)
  - Public services exposed by `orbiteus_core` (cross-cutting)
  - Events on the EventBus / Outbox (asynchronous)
- `ModuleRegistry` topologically sorts modules at startup before bootstrap.

## Lifecycle

```
registry.register("crm")
  |
  v  bootstrap
  +-- _discover()          # import module, validate manifest
  +-- _topological_sort()  # graphlib.TopologicalSorter (stdlib)
  +-- _load_mappings()     # SQLAlchemy Table + register_mapping()
  +-- _register_security() # seed access.yaml into RBAC cache (Redis)
  +-- _register_actions()  # AI Action Registry
  +-- _register_ai()       # AIModuleConfig registry
  +-- _register_routes()   # mount auto-CRUD + custom router
  +-- _register_menus()    # base_ui_menus entries
  +-- on_install()         # one-time per tenant (seed)
```

## Backend technology choices

| Concern | Choice | Rationale |
|---|---|---|
| HTTP server | Gunicorn + UvicornWorker | Mature, well-documented, prod default for FastAPI |
| ORM | SQLAlchemy 2 imperative mapping | Domain dataclasses stay free of ORM coupling |
| Migrations | Alembic + `pg_try_advisory_lock` | Safe across replicas |
| DB pooler | PgBouncer (transaction mode) | Required at >100 concurrent connections |
| Cache / Pub/Sub / Broker / Rate limit / JWT revocation | Redis 7 | One component, many roles |
| Queue / scheduled tasks | Celery 5 + Celery Beat | Largest Python community, AI-friendly |
| Embeddings store | pgvector | Same DB, no extra service |

See ADRs `0011`, `0012`, `0013`, `0014`, `0015` for the full reasoning.

## Frontend technology choices

| Concern | Choice |
|---|---|
| Framework | Next.js 16 App Router (React 19) |
| Design system | Mantine 9 |
| Shared widgets / AI | `admin-ui/src/orbiteus-ui/` (copy to portal-ui when needed) |
| State | Component-local + axios + ui-config cache |
| Charts | Recharts 3 |

`admin-ui` and `portal-ui` are independent Next.js apps; cross-cutting widgets
and AI surfaces ship from `admin-ui/src/orbiteus-ui/` until the portal copies them.

## Multi-tenancy

- `tenant_id` on every business table.
- `BaseRepository._tenant_filter()` is automatic; bypass requires superadmin
  context and is logged.
- `SystemModel` (base engine tables) — no `tenant_id`, global per instance.

## RBAC (5 levels)

1. **Model access** (`base_model_access`) — role × model × {read, write, create, unlink}.
2. **Record rules** (`base_rule`) — domain expressions filtering rows.
3. **Action RBAC** — every Action declares `requires_feature`; resolver filters.
4. **Field-level** — read/write per field per role *(planned, see tree-spec)*.
5. **Scope** — JWT claim `scope ∈ {internal, portal, ai}` is the upper bound.

See `05-rbac-multitenancy.md`.

## What the architecture deliberately rejects

- Microservices (we are a monolith on purpose).
- A second design system on the front.
- Background runtimes other than Celery in MVP.
- ORM other than SQLAlchemy 2 (imperative).
- Provider-specific SDKs in modules — only via `orbiteus_core.ai.providers`.
