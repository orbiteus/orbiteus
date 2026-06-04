<div align="center">
  <a href="https://orbiteus.com">
    <img src="docs/assets/symbol-readme.svg" alt="Orbiteus" width="160" />
  </a>

  <!-- LOCKED: README hero tagline — do not edit without explicit product-owner approval (see AGENTS.md). -->
  **Orbiteus — A Full-Stack Development Framework for AI Agents. Build custom ERP, CRM & Business Tools in days not months. Start with 80% of the job done.**

  ![status](https://img.shields.io/badge/version-v1.1.0-blue)
  ![license](https://img.shields.io/badge/license-MIT-green)
  ![PRs](https://img.shields.io/badge/PRs-welcome-brightgreen)
  ![backend](https://img.shields.io/badge/backend-FastAPI%20%7C%20Python%203.13-3776AB)
  ![frontend](https://img.shields.io/badge/frontend-Next.js%2016%20%7C%20Mantine%209-000000)
  ![db](https://img.shields.io/badge/db-PostgreSQL%2016%20%2B%20pgvector-336791)
</div>

> **AI agents** touching this repository: read [`docs/pre-prompt.md`](docs/pre-prompt.md) first. It is the canonical stack and convention contract. Skipping it leads to invented dependencies and bypassed framework primitives — both out of bounds.

---

## What is Orbiteus?

Orbiteus is an **AI agent engine** for **domain business applications** — operational CRM, club management, HR, integrations, and custom tools that fill gaps generic SaaS cannot. Your agents implement **your** processes on top of guardrails (auth, RBAC, audit, APIs, admin shell, jobs, realtime, AI tools).

The bundled CRM module is a **framework demo**, not the product you must ship. See [`docs/40-reference-product-caltrain.md`](docs/40-reference-product-caltrain.md) for a reference domain app (fitness CRM replacing a rent-by-the-seat sales tool).

You can ship a solid domain app **in days** when you follow [`docs/39-spec-driven-agent-workflow.md`](docs/39-spec-driven-agent-workflow.md): Ask → Spec → Implement → Verify.

## HOW TO USE IT?

**Tell your AI agent to build your app using Orbiteus** — that's the whole idea.

The engine already carries the **technical baseline**: app server, database layer, admin shell, security and tenancy model, audit trail, background jobs, webhooks, portal surface, and AI tools that obey the same rules as people. Your agent works **inside** this codebase and its contracts ([`docs/pre-prompt.md`](docs/pre-prompt.md)) so you are not inventing sessions, queues, or RBAC from scratch.

You **start with roughly 80% of the plumbing done**. **What you focus on** is describing your business — who uses the app, what you sell, what you track, what “done” looks like, and the edge cases that matter. **What the AI agent and Orbiteus take on together** is the heavy technical work: modules, migrations, views, APIs, tests, and shipping something you can run and grow.

## What you can build with Orbiteus

**Any business** — from a one-person shop to a large operator — can use Orbiteus to build **whatever internal or customer-facing application you actually need**. You are not picking from a short menu of verticals; you describe the process, and your AI agent implements it on top of the engine.

Examples (illustrative, not a limit):

- **Replace a rent-by-the-seat sales CRM** with one that follows **your** pipeline stages, approvals, and handoffs — not a vendor’s median company.
- **Replace a legacy WMS** with a modern stock-and-movements system **plus** a **supplier portal** your partners actually log into.
- **Replace a third-party “collect reviews” SaaS** with your own feedback app **tied to your product and domain data** — same origin, same rules, your data model.
- **Projects, sales, client communication, operations, finance** in one coherent surface — **you name it**. The stack is already there: **~80% of the plumbing is done** (auth, multi-tenancy, permissions, audit, APIs, admin UI, background jobs, realtime, and **AI agents** calling tools under the **same** rules as people). You add **your** business logic, integrations, and the last mile of UX that makes it yours — not another hand-rolled session stack or webhook-retry science project.

---

## Screenshots

Files: [`docs/assets/readme-screenshots/`](docs/assets/readme-screenshots/) (`1.png`–`5.png`). Swap files there to refresh the gallery.

| ![Admin dashboard and AI assistant](docs/assets/readme-screenshots/1.png) | ![Command palette — quick create](docs/assets/readme-screenshots/2.png) |
|:---:|:---:|
| **1.** Admin dashboard — CRM KPIs, AI assistant, CRM + Technical nav. | **2.** Command palette (`⌘K`) — create records across modules from one search. |

| ![New webhook form](docs/assets/readme-screenshots/3.png) | ![Audit log](docs/assets/readme-screenshots/4.png) |
|:---:|:---:|
| **3.** Webhooks — outbound events, target URL, optional auth headers. | **4.** Audit log — tenant-wide trail with filters and field-level diffs. |

| ![AI integration BYOK](docs/assets/readme-screenshots/5.png) |
|:---:|
| **5.** AI integration — BYOK provider keys, models, per-tenant token budget. |

---

## Engine matrix

What ships in the repo, in four layers. Icons are small line-art SVGs in [`docs/assets/engine-matrix/`](docs/assets/engine-matrix/).

### Backend

| ![PostgreSQL](docs/assets/engine-matrix/backend-postgres.svg) | ![FastAPI](docs/assets/engine-matrix/backend-fastapi.svg) | ![Redis & workers](docs/assets/engine-matrix/backend-redis-jobs.svg) |
|:---:|:---:|:---:|
| **PostgreSQL + pgvector**<br/>Tenant-scoped data, SQLAlchemy 2 + asyncpg, Alembic migrations, embeddings storage. | **FastAPI core**<br/>Auto-routed REST, OpenAPI, structured logs, Prometheus metrics, Gunicorn + Uvicorn in production. | **Redis + Celery**<br/>Cache, rate limits, JTI revocation, outbox, workers, Beat, signed webhooks, realtime Pub/Sub. |

### Frontend (admin-ui)

| ![Admin shell](docs/assets/engine-matrix/frontend-shell.svg) | ![Views](docs/assets/engine-matrix/frontend-views.svg) | ![Command palette](docs/assets/engine-matrix/frontend-command.svg) |
|:---:|:---:|:---:|
| **Next.js 16 + Mantine 9**<br/>Internal admin shell, auth session, design system (`orbiteus-ui`), production `next build`. | **Views + registry**<br/>List, form, kanban, calendar, graph from view XML — minimal bespoke TSX per business module. | **Command palette**<br/>`⌘K` actions wired to the engine; server-side `/api` proxy to the FastAPI backend. |

### Portal UI

| ![External users](docs/assets/engine-matrix/portal-external.svg) | ![Share links](docs/assets/engine-matrix/portal-share.svg) | ![API path](docs/assets/engine-matrix/portal-api.svg) |
|:---:|:---:|:---:|
| **Partner-facing app**<br/>Separate Next deployable; RBAC scope `portal` for external users. | **Share links**<br/>Token exchange and scoped access for customers or vendors (see [`docs/09-portal-ui.md`](docs/09-portal-ui.md)). | **Same-origin API**<br/>Next rewrites `/api/*` to `BACKEND_URL` — no CORS tricks in the browser for portal traffic. |

### Built-in AI layer

| ![BYOK](docs/assets/engine-matrix/ai-byok.svg) | ![Tools](docs/assets/engine-matrix/ai-tools.svg) | ![Streaming](docs/assets/engine-matrix/ai-stream.svg) |
|:---:|:---:|:---:|
| **BYOK providers**<br/>Anthropic, OpenAI, Ollama; encrypted tenant credentials; model + budget fields in admin. | **Tool dispatcher**<br/>Agents call registered tools that use `BaseRepository` — same RBAC and audit as human writes. | **Chat + embeddings**<br/>Streaming `/api/ai/chat`, dashboard prompts, pgvector-backed retrieval (see [`docs/15-ai-layer.md`](docs/15-ai-layer.md)). |

---

## Capabilities (proof, not philosophy)

| | |
|---|---|
| **Modular monolith** | `registry.register("your_module")` wires models, security, views, actions, and optional AI surface in one place. |
| **Zero TSX per business module** | Catch-all admin routes + widget registry + view XML — new tables and APIs ship with matching UI patterns. |
| **Multi-tenant by default** | Repository-enforced tenancy; negative tests for cross-tenant access. |
| **Layered RBAC** | Model access, record rules, actions, and AI scopes; Redis-backed cache with cross-replica invalidation. |
| **Audit** | CRUD, auth events, AI tool calls — with redaction hooks for sensitive payloads. |
| **Events, outbox, webhooks** | Atomic outbox rows, Celery workers, bounded retries, dead-letter path, HMAC-signed delivery. |
| **Realtime** | SSE + Redis Pub/Sub; tenant-scoped topics; admin lists and portal views can subscribe safely. |
| **Infra in one command** | Docker Compose: Postgres 16 + pgvector, Redis, backend, admin UI, portal UI (see [`docs/17-deployment.md`](docs/17-deployment.md)). |
| **CI gate** | Docs checks, pytest + coverage, Vitest, `next build`, Playwright, audits, secrets baseline, license policy. |

---

## Quick start

```bash
git clone <repo-url>
cd orbiteus
docker compose up --build
```

| Surface | URL |
|--------|-----|
| Admin UI | http://localhost:3000 |
| Portal UI | http://localhost:3001 (dev compose; prod uses reverse proxy — see deployment docs) |
| API | http://localhost:8000/api |
| OpenAPI | http://localhost:8000/api/docs |
| Metrics | http://localhost:8000/metrics |

Default login (development only): `admin@example.com` / `admin1234`.

**Optional demo dataset** (curated companies, users, attachments):

```bash
# One-time cleanup after old bulk seed + load demo (add to .env or export):
SEED_DEMO_DATA=1 RESET_DEMO_DATA=1 docker compose up --build

# Or manually:
docker compose exec backend python -m scripts.seed_demo --reset
```

Demo users (password `demo1234`): `demo.manager@example.com`, `demo.user@example.com`, `demo.sales@example.com`.  
Rotate `BOOTSTRAP_ADMIN_PASSWORD` and `SECRET_KEY` before any production traffic — the production profile refuses default secrets.

---

## Architecture at a glance

```
+---------------------------+     +---------------------------+
|   admin-ui (Next.js 16)   |     |   portal-ui (Next.js 16)  |
|   internal users (RBAC)   |     |   external users / share  |
+-------------+-------------+     +-------------+-------------+
              |  /api/*  (admin-ui: server proxy; portal: rewrites + same-origin)|
              v          v                       v            v
+------------------------------------------------------------------+
|  FastAPI (Gunicorn + UvicornWorker in production)               |
|  orbiteus_core: registry, repositories, auto-router, AI,        |
|                 auth, RBAC, audit, events, cache, realtime       |
|  modules:       base, auth, crm (reference sample), …          |
+----------+----------------------+--------------------+-----------+
           |                      |                    |
+----------v---------+  +---------v--------+  +--------v---------+
|  PostgreSQL 16     |  |  Redis 7         |  |  Celery 5        |
|  + pgvector        |  |  cache, pub/sub, |  |  + Beat          |
|  (+ PgBouncer)     |  |  rate limits,   |  |  outbox drain    |
+--------------------+  |  session revoke  |  |  + webhooks       |
                        +------------------+------------------+
```

---

## What ships in the box (summary)

For the full checklist against the internal Definition of Done, see [`docs/34-inventory-and-status.md`](docs/34-inventory-and-status.md) and [`CHANGELOG.md`](CHANGELOG.md). In one breath:

- **Identity & sessions** — JWT access/refresh with rotation, TOTP + recovery codes, password reset flow, HttpOnly cookie session for the admin shell, share tokens for portal.
- **Data & rules** — Async SQLAlchemy 2, Alembic, soft delete hooks, attribution columns, record rules, strict tenant filters on repositories.
- **AI** — Provider adapters (Anthropic, OpenAI, Ollama), BYOK storage, streaming chat, tool dispatcher, embeddings table with pgvector.
- **Ops** — Structured logs, Prometheus metrics families, optional OpenTelemetry, backup scripts and restore-drill documentation.
- **Quality gate** — GitHub Actions workflow aggregating docs, tests, audits, and license reports.

---

## For engineers (stack & modules)

### Tech stack (authoritative detail)

Binding list lives in [`docs/pre-prompt.md`](docs/pre-prompt.md) (stack section). In short: Python 3.13, FastAPI, SQLAlchemy 2 + asyncpg, Pydantic v2, Redis, Celery 5, PostgreSQL 16 + pgvector, Next.js 16 + React 19 + Mantine 9.

**Monorepo (npm workspaces):** `admin-ui` and `portal-ui` only. Cross-cutting widgets and AI surfaces (`PromptInput`, `AIDashboard`, shared form widgets) live under **`admin-ui/src/orbiteus-ui/`**. When the portal needs the same UX, copy the relevant files into `portal-ui` (two deployable apps, no separate `packages/*` workspace).

### Module layout

Full convention: [`docs/03-modules.md`](docs/03-modules.md). Skeleton:

```
modules/<name>/
  manifest.py
  model/domain.py, mapping.py, schemas.py
  controller/repositories.py, services.py, router.py
  security/access.yaml
  view/*.xml, config.py
  actions.py, ai.py, bootstrap.py, docs/spec.md
```

Register once:

```python
registry.register("your_module")
```

You get migrations against declared tables, REST + OpenAPI for each model, dynamic list/form/kanban/calendar/graph, Command Palette actions, AI tool surface, audit, RBAC, and realtime hooks — without copying CRUD from another module.

### Running tests

```bash
# backend
PYTHONPATH=backend pytest -q --cov --cov-report=term

# admin UI unit tests
npm test --workspace admin-ui

# Playwright (stack on :3000)
npm run e2e --workspace admin-ui
```

Details: [`docs/20-testing.md`](docs/20-testing.md) and `.github/workflows/ci.yml`.

---

## Documentation map

| Topic | File |
|-------|------|
| Pre-prompt (read first) | [`docs/pre-prompt.md`](docs/pre-prompt.md) |
| Architecture | [`docs/02-architecture.md`](docs/02-architecture.md) |
| Modules | [`docs/03-modules.md`](docs/03-modules.md) |
| Data model + `base_*` | [`docs/04-data-model.md`](docs/04-data-model.md) |
| RBAC + multi-tenancy | [`docs/05-rbac-multitenancy.md`](docs/05-rbac-multitenancy.md) |
| Auth | [`docs/06-auth.md`](docs/06-auth.md) |
| Auto-CRUD API + webhooks | [`docs/07-api.md`](docs/07-api.md) |
| Admin UI | [`docs/08-admin-ui.md`](docs/08-admin-ui.md) |
| Design system (Mantine + `orbiteus-ui`) | [`docs/10-design-system.md`](docs/10-design-system.md) |
| Portal UI | [`docs/09-portal-ui.md`](docs/09-portal-ui.md) |
| Realtime | [`docs/11-realtime.md`](docs/11-realtime.md) |
| Events + queues | [`docs/12-events-and-queues.md`](docs/12-events-and-queues.md) |
| Audit | [`docs/14-audit.md`](docs/14-audit.md) |
| AI layer | [`docs/15-ai-layer.md`](docs/15-ai-layer.md) |
| Deployment | [`docs/17-deployment.md`](docs/17-deployment.md) |
| Security | [`docs/18-security.md`](docs/18-security.md) |
| Testing | [`docs/20-testing.md`](docs/20-testing.md) |
| Observability | [`docs/29-observability.md`](docs/29-observability.md) |
| Backups + DR | [`docs/31-backups-and-dr.md`](docs/31-backups-and-dr.md) |
| Inventory ledger | [`docs/34-inventory-and-status.md`](docs/34-inventory-and-status.md) |
| Definition of Done | [`docs/35-core-definition-of-done.md`](docs/35-core-definition-of-done.md) |
| ADRs | [`docs/adr/`](docs/adr/) |

---

## Contributing

We welcome fixes, docs, and modules that follow the registry contract. Start with [`CONTRIBUTING.md`](CONTRIBUTING.md) (branching, review expectations, and the PR checklist) and [`AGENTS.md`](AGENTS.md) for automation policy.

---

## Versioning + release

Current line is **`v1.1.0`**. Release notes: [`CHANGELOG.md`](CHANGELOG.md). Honest code-vs-docs progress: [`docs/34-inventory-and-status.md`](docs/34-inventory-and-status.md).

---

## License

MIT — see [`LICENSE`](LICENSE). Third-party manifests: [`THIRD_PARTY_LICENSES.python.json`](THIRD_PARTY_LICENSES.python.json), [`THIRD_PARTY_LICENSES.node.json`](THIRD_PARTY_LICENSES.node.json) (regenerated via `scripts/generate_licenses.sh`; CI enforces a no-GPL policy with a small compatibility allow-list — see `docs/27-licenses.md`).
