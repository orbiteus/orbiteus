# Changelog

All notable changes to Orbiteus are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added

- `CONTRIBUTING.md` — contribution guide aligned with monorepo layout and spec-first modules
- `SECURITY.md` — coordinated vulnerability disclosure policy for GitHub Security tab

---

## [0.1.0] — 2026-04-16

### Added — Phase 1 (Architecture) + Phase 2 (Backend)

**Architecture (Phase 1)**
- Monorepo: `backend/` + `admin-ui/` + `docker-compose.yml`
- Docker one-command setup: `docker compose up --build` -> full stack running
- `backend/Dockerfile`, `admin-ui/Dockerfile`, `docker-compose.yml`
- Alembic migrations auto-applied at startup via `entrypoint.sh`
- Superadmin seed (`admin@example.com` / `admin1234`) on first run
- Module registration system with topological dependency sort

**Backend — data layer (Phase 2)**
- `GET /api/base/ui-config` — full UI config from Pydantic Write schemas + XML views (in-memory)
- Schema introspection: Pydantic annotations -> UI field types (text, email, tel, number, boolean, textarea, select, date)
- Auto-CRUD: 5 REST endpoints per registered model (auth-gated)
- Query param filtering: `?status=prospect`, `?name__contains=acme`, `?order_by=name&order_dir=desc`
- Operators: eq, __contains, __gt, __gte, __lt, __lte, __in, __ne
- Tenant isolation automatic in BaseRepository
- RBAC: ir_model_access + ir_rule (record rules)
- JWT auth + bcrypt + TOTP 2FA
- `GET /api/ai/actions?q=&limit=8` — RapidFuzz action search (~1ms, zero LLM calls)
- AI Action Registry with multilingual keywords (EN + PL)
- Optional Claude Haiku reranking when score < 40
- 16 built-in actions across base, auth, crm modules
- 30 tests passing on PostgreSQL (no mocks)

**Frontend — initial renderer (Phase 3 — in progress)**
- Next.js 14 App Router + Mantine 8 dark theme
- ResourceList — generic list with pagination, search, column sorting
- ResourceForm — generic form (text, email, tel, number, textarea, select, boolean, date)
- ResourceKanban — drag-drop kanban board (dnd-kit)
- CommandPalette (Cmd+K) — debounced search, grouped results, keyboard nav
- Dynamic sidebar from ui-config
- Catch-all routes: /[module]/[model]/* auto-renders from backend config

### Modules

| Module | Models |
|--------|--------|
| `base` | Company, Partner, User, Tenant, IrConfigParam, IrSequence, IrCron, IrUiView, IrUiMenu, IrModelAccess, IrRule |
| `auth` | JWT login/logout, password change, TOTP 2FA |
| `crm` | Customer, Opportunity, Pipeline, Stage |

---

## [0.0.1] — 2026-03-10

### Added — Initial scaffold

- FastAPI + SQLAlchemy 2.0 imperative mapping + Pydantic v2 monorepo
- `orbiteus_core/registry.py` — `ModuleRegistry` with auto-router, auto-migration, view loading
- `orbiteus_core/repository.py` — `BaseRepository` with tenant isolation
- `orbiteus_core/auto_router.py` — auto-CRUD router per registered model
- JWT auth with `python-jose` + bcrypt
- PostgreSQL 16 with asyncpg driver
- Alembic migration setup

[Unreleased]: https://github.com/orbiteus/orbiteus/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/orbiteus/orbiteus/releases/tag/v0.1.0

