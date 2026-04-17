# Orbiteus Engine — Architecture Specification

> Status: LIVING DOCUMENT — updated as decisions are made
> Last updated: 2026-03-18
> **Read this before starting any new feature or module.**

---

## 1. Purpose

Engine for building business applications (ERP/CRM/WMS/Commerce and beyond).
A client/partner installs the engine, configures modules, brands the UI, and gets their own application.

**This is not a finished product — it is a platform for building products.**

Example use cases:
- Gym chain management
- Interior design studio
- Transport management system (TMS)
- Niche CRM SaaS for vertical X
- Warehouse management (WMS)

---

## 2. Development Axis

All work follows four sequential phases. A phase must be closed before the next one starts.

```
PHASE 1          PHASE 2          PHASE 3          PHASE 4
Architecture  →  Backend       →  Frontend      →  Features & Modules
(skeleton)       (data+logic)     (renderer)       (business value)
```

| Phase | What | Goal |
|-------|------|------|
| **1 — Architecture** | Monorepo, Docker, module system, core ↔ module ↔ frontend contracts | `docker compose up` = full stack running, modules auto-discovered |
| **2 — Backend** | Data models, ORM, migrations, CRUD, auth, RBAC, tenant isolation, AI actions, queues | Any Python module gets full REST API + OpenAPI + query filtering automatically |
| **3 — Frontend** | Dynamic renderer, auto-menu, views (list, form, kanban, graph, table, activities) | Zero TSX per module — write Python, get UI. Like Odoo but modern stack. |
| **4 — Features** | Extension patterns, Smart Search, SSE, audit trail, business modules (HR, Project, Inventory...) | Engine is complete → go to clients with ready platform, add micro-modules per project |

**Closing Phase 1–3 = we have a working ENGINE.**
Phase 4 is ongoing forever — adding modules and features per client need.

---

## 3. Design Principles (Non-negotiable)

| Principle | Rule |
|-----------|------|
| **Spec-first** | Every module has `docs/spec.md` before any code |
| **Module isolation** | Modules never import each other — only through `orbiteus_core` API. No `relationship()` cross-module — FK UUID only. |
| **Auto-propagation** | `registry.register("hr")` → tables, CRUD API, OpenAPI, UI, command palette — all automatic |
| **AI-native** | Every module declares Actions — business units accessible via UI and AI |
| **White-label** | No product name hardcoded in UI — everything from `ir_config_param` |
| **Open source stack** | 100% MIT/Apache/BSD — no GPL, no vendor lock-in |
| **Tenant isolation** | `tenant_id` on every business table — enforced automatically at repository layer |
| **RBAC everywhere** | Every action checks permissions — AI cannot bypass RBAC |
| **PostgreSQL only** | Production = Postgres. Period. |

---

## 4. Tech Stack

### Backend
| Layer | Technology | License |
|-------|-----------|---------|
| Language | Python 3.12+ | PSF |
| API Framework | FastAPI (lifespan) | MIT |
| ORM | SQLAlchemy 2.0 (imperative mapping) | MIT |
| Migrations | Alembic (`upgrade head` at startup) | MIT |
| Validation | Pydantic v2 | MIT |
| Auth | python-jose (JWT) + bcrypt | MIT / Apache |
| 2FA | pyotp (TOTP) | MIT |
| Async DB driver | asyncpg | Apache |
| Background jobs | Temporal.io | MIT |
| Fuzzy matching | RapidFuzz | MIT |
| Database | PostgreSQL 16 | PostgreSQL License |

### Frontend
| Layer | Technology | License |
|-------|-----------|---------|
| Framework | Next.js 14 (App Router) | MIT |
| UI Library | React 18 | MIT |
| Components | Mantine 8 | MIT |
| Icons | @tabler/icons-react | MIT |
| HTTP Client | axios | MIT |
| Drag & Drop | @dnd-kit | MIT |

### AI (optional — does not block development)
| Layer | Technology | Notes |
|-------|-----------|-------|
| LLM | Claude API (Anthropic) | Reranking only when score < 40 |
| Fuzzy match | RapidFuzz | Primary — zero API calls, works offline |

---

## 5. Architecture Layers

```
+--------------------------------------------------------------+
|  Admin UI (Next.js 14 + Mantine 8)                           |
|  - White-label branding per tenant                           |
|  - CommandPalette (Cmd+K) — action search                    |
|  - Catch-all routes: /[module]/[model] -> auto-generated UI  |
|  - Views: list, form, kanban, graph, table, activities       |
+---------------------+----------------------------------------+
                      |  /api/* (Next.js rewrite proxy)
+---------------------v----------------------------------------+
|  FastAPI                                                     |
|  - Auto-CRUD routes (5 endpoints per model)                  |
|  - GET /api/base/ui-config — field metadata for frontend     |
|  - GET /api/ai/actions?q= — command palette resolver         |
|  - Custom module routers                                     |
|  - OpenAPI /api/docs                                         |
+---------------------+----------------------------------------+
                      |
+---------------------v----------------------------------------+
|  orbiteus_core                                                  |
|  - ModuleRegistry (lifecycle, topological sort)              |
|  - AutoRouter (CRUD generation + auth)                       |
|  - BaseRepository (CRUD + tenant filter + RBAC + hooks)      |
|  - Security (JWT, RBAC, RLS context)                         |
|  - AI layer (ActionRegistry, ActionResolver)                 |
+---------------------+----------------------------------------+
                      |
+---------------------v----------------------------------------+
|  Modules (base -> auth -> crm -> hr -> project -> ...)       |
|  - manifest.py + domain.py + mapping.py + schemas.py         |
|  - repositories.py + services.py + router.py                 |
|  - actions.py (AI-native: module action declarations)        |
|  - security/access.yaml                                      |
+---------------------+----------------------------------------+
                      |
+----------+----------+---+----------+
| PostgreSQL 16           | Temporal |
| - tenant_id isolation   | - Jobs   |
| - UUID PKs              | - Sagas  |
| - JSONB custom fields   |          |
+-------------------------+----------+
```

---

## 6. Multi-tenancy

**Strategy: `tenant_id` on every business table + BaseRepository auto-filters.**

```
Tenant (organization)
  +-- Company (legal entity within org)
        +-- User (user within company)
              +-- role_ids -> features -> permissions
```

- `tenant_id` — data isolation (BaseRepository._tenant_filter() automatic)
- `company_id` — segmentation within tenant
- User can belong to multiple companies
- `SystemModel` (ir_* tables) — no tenant_id, global per instance

---

## 7. RBAC — 4 Levels

### Level 1 — Model Access (ir_model_access)
```
Role -> Model -> [read, write, create, unlink]
```
Checked in `BaseRepository._check_model_access()` on every operation.

### Level 2 — Record Rules (ir_rule)
Domain-based row filtering per role — salesman sees only their own records.
Applied automatically in `BaseRepository.search()` and `get()`.

### Level 3 — Action RBAC
Every Action has `requires_feature`. Resolver filters actions by user's features.
**AI cannot bypass RBAC — ActionExecutor verifies permissions independently.**

### Level 4 — Field Security (Phase 4)
Per-field read/write per role.

---

## 8. Module Lifecycle

```
registry.register("crm")
  |
  v
discover()
  -> validate_deps()         # topological sort, check depends_on
  -> load_mappings()         # SQLAlchemy Table + imperative mapper
  -> register_security()     # seed RBAC cache from security/access.yaml
  -> register_actions()      # load actions.py into ActionRegistry
  -> register_routes()       # mount auto-CRUD + custom router
  -> register_menus()        # insert ir_ui_menu entries
  -> on_install()            # one-time init (seed data, custom fields)
```

---

## 9. Module Structure

```
modules/my_module/
+-- manifest.py              # metadata: name, version, depends_on, models, menus
+-- actions.py               # AI-native: Action list for command palette + search
+-- model/
|   +-- domain.py            # pure Python dataclasses
|   +-- mapping.py           # SQLAlchemy Table + register_model()
|   +-- schemas.py           # Pydantic Read/Write schemas
+-- controller/
|   +-- repositories.py      # extends BaseRepository per model
|   +-- services.py          # business logic (stateless)
|   +-- router.py            # custom FastAPI endpoints
+-- security/
|   +-- access.yaml          # role -> model -> CRUD permissions
+-- view/
|   +-- *_views.xml          # list/form/kanban view definitions
|   +-- config.py            # view registration
+-- docs/
|   +-- spec.md              # REQUIRED before implementation
+-- __init__.py
```

### Cross-module rule
```python
# FORBIDDEN
from modules.crm.model.domain import Customer

# CORRECT — FK UUID + separate query
customer_id: uuid.UUID  # ID only
# fetch separately via own repo or orbiteus_core service
```

---

## 10. AI-native Layer

### Principle

> Every business action in the ERP (create record, change status, navigate to view,
> run report) MUST be registered as an `Action`.
> REST endpoint = HTTP interface. Action = business unit accessible everywhere.

### Action structure

```python
# modules/crm/actions.py
from orbiteus_core.ai import Action, ActionCategory

ACTIONS = [
    Action(
        id="crm.customer.create",
        label="Create Customer",
        keywords=["new customer", "add client", "nowy klient", "dodaj klienta"],
        description="Open form to create a new customer",
        category=ActionCategory.CREATE,
        target="navigate",
        target_url="/crm/customer/new",
        requires_feature="crm.customers.manage",
        icon="user-plus",
    ),
]
```

Keywords are multilingual — RapidFuzz matches regardless of input language.

### ActionCategory
```python
class ActionCategory(str, Enum):
    NAVIGATE = "navigate"   # open a view / page
    CREATE   = "create"     # open a creation form
    REPORT   = "report"     # open a report / analytics
    EXECUTE  = "execute"    # execute action without form (e.g. send email)
    SEARCH   = "search"     # open view with predefined filter
```

### Resolver — no LLM in default mode

```
GET /api/ai/actions?q=new+customer&limit=8

1. Get all Actions from ActionRegistry
2. Filter by requires_feature (RBAC — user's token)
3. RapidFuzz: score each action vs query (label + keywords)
4. If max_score < 40 and LLM configured -> semantic reranking (optional)
5. Return top 8 sorted by score

Cost: ~1ms, zero API calls in happy path
```

---

## 11. UI Auto-generation

```
registry.register("hr")
  |
  v  bootstrap
  |
  +-- mapping.py -> register_model("hr.employee", EmployeeWrite schema)
  |
  v  GET /api/base/ui-config
  {
    "modules": [{
      "name": "hr",
      "models": [{
        "name": "hr.employee",
        "fields": [
          {"name": "first_name", "type": "text",  "required": true,  "label": "First Name"},
          {"name": "email",      "type": "email", "required": false, "label": "Email"}
        ],
        "views": { "list": "<list>...</list>", "form": "<form>...</form>" }
      }]
    }]
  }
  |
  v  Frontend: /[module]/[model]/page.tsx (catch-all)
  -> fetchUiConfig() -> find model -> render ResourceList with columns from fields
  -> /[module]/[model]/new -> ResourceForm with fields from Pydantic
  -> /[module]/[model]/[id] -> ResourceForm with loaded data
```

**Result: zero TSX per module. Write Python, get UI.**

---

## 12. Query Params Filtering

Every auto-CRUD list endpoint supports:

```
GET /api/crm/customer?status=prospect
  -> domain [("status","=","prospect")]

GET /api/crm/customer?name__contains=acme
  -> domain [("name","ilike","%acme%")]

GET /api/crm/customer?created_after=2024-01-01
  -> domain [("create_date",">=","2024-01-01")]

GET /api/crm/customer?order_by=name&order_dir=asc

Operators: (none)=eq, __contains, __gt, __gte, __lt, __lte, __in, __ne
```

---

## 13. Definition of Done — Orbiteus Engine

> **The Engine is DONE when ALL of the following are true:**
>
> 1. A developer can create a new module (e.g. HR) by writing only
>    `manifest.py` + `model/` + `security/access.yaml` + `actions.py`
>    and gets a fully working CRUD with UI + command palette **without a single line of TSX**.
>
> 2. Backend and frontend start with one command:
>    `docker compose up` -> http://localhost:3000 ready to use.

---

## PHASE 1 — Architecture (Engine Skeleton)

**Status: DONE**

Monorepo structure, Docker, module system, communication contracts.

- [x] Monorepo: `backend/` + `admin-ui/` + `docker-compose.yml`
- [x] `docker-compose.yml` — services: postgres:16 (healthcheck), backend, frontend
- [x] `backend/Dockerfile` — Python 3.12, uv install, entrypoint with alembic + uvicorn
- [x] `admin-ui/Dockerfile` — Node 20, next build, next start
- [x] `docker compose up --build` from clean checkout -> full stack in < 3 min
- [x] Backend `DATABASE_URL` env var -> postgres service in Docker
- [x] Frontend `/api/*` proxy to backend via `next.config.js`
- [x] Alembic `upgrade head` at startup (entrypoint.sh)
- [x] Superadmin seed (`admin@example.com` / `admin1234`) on first run
- [x] `orbiteus_core/registry.py` — ModuleRegistry, register(), bootstrap, topological sort
- [x] `orbiteus_core/auto_router.py` — 5 CRUD endpoints per model (auth-gated)
- [x] `orbiteus_core/repository.py` — BaseRepository + tenant_filter + RBAC check
- [x] `orbiteus_core/security.py` — JWT, require_auth, RequestContext
- [x] `orbiteus_core/manifest.py` — ModuleManifest Pydantic model
- [x] Module structure convention established (manifest + model + controller + security + view + actions)

---

## PHASE 2 — Backend (Data & Logic)

**Status: DONE**

Data models, ORM, migrations, auto-CRUD, auth, RBAC, tenant isolation, AI actions.

- [x] FastAPI + SQLAlchemy 2.0 imperative mapping + asyncpg + PostgreSQL
- [x] Pydantic v2 Read/Write schemas per model
- [x] Auto-CRUD: 5 endpoints per registered model (list, create, get, update, delete)
- [x] Query param filtering: eq, __contains, __gte, __gt, __lte, __lt, __in, __ne
- [x] Query ordering: order_by + order_dir
- [x] Date aliases: created_after, created_before, updated_after, updated_before
- [x] Tenant isolation automatic in BaseRepository
- [x] RBAC: ir_model_access + ir_rule (record rules)
- [x] JWT auth + bcrypt + TOTP 2FA
- [x] `GET /api/base/ui-config` — field metadata from Pydantic schemas + XML views
- [x] AI Action Registry + RapidFuzz resolver (~1ms)
- [x] `GET /api/ai/actions?q=&limit=8` — ranked results, RBAC-filtered
- [x] Optional Claude Haiku reranking when score < 40
- [x] Multilingual action keywords (EN + PL, extensible)
- [x] Modules: base (11 models), auth (JWT + 2FA), crm (Customer, Opportunity, Pipeline, Stage)
- [x] 30 tests passing on PostgreSQL (no mocks)

---

## PHASE 3 — Frontend (Dynamic Renderer)

**Status: IN PROGRESS**

Dynamic UI that auto-renders from backend config. Zero TSX per module.

**Done:**
- [x] Next.js 14 App Router + Mantine 8 dark theme
- [x] `ResourceList` — generic list with pagination, search, column sorting, delete
- [x] `ResourceForm` — generic form with field types (text, email, tel, number, textarea, select, boolean, date)
- [x] `ResourceKanban` — drag-drop kanban board (dnd-kit)
- [x] `ViewSwitcher` — toggle between list/kanban via URL param
- [x] Dynamic options fetching for select fields (optionsResource)
- [x] `CommandPalette` (Cmd+K) — debounced search, grouped results, keyboard nav
- [x] Dynamic sidebar from ui-config (modules auto-appear)
- [x] Catch-all routes: /[module]/[model]/* auto-renders from ui-config
- [x] Login page + JWT token storage + 401 redirect
- [x] Toast notifications (Mantine) for CRUD operations
- [x] Backend validation errors parsed and shown per field

**Pending:**
- [ ] Views: graph, calendar, activities, dashboard (like Odoo view types)
- [ ] Smart Search in list — `?` prefix for LLM-generated filters
- [ ] Action suggestions above list results when query matches actions
- [ ] Badge/statusbar widget for status fields
- [ ] Many2one widget — display related record name instead of UUID
- [ ] Monetary widget — currency formatting
- [ ] Responsive layout — mobile sidebar collapse
- [ ] White-label branding from ir_config_param (logo, colors, app name)

**Verification:**
```
1. registry.register("hr") -> restart backend
2. http://localhost:3000/hr/employee -> list with columns from Pydantic (no TSX edit)
3. Click "New" -> form with fields from Pydantic
4. Save -> record visible in list
5. Cmd+K -> type "employee" -> action appears
```

---

## PHASE 4 — Features & Modules

**Status: NOT STARTED**

Extension patterns and business modules. Only starts after Phase 3 is closed.

### 4A — Engine Extensions

**BaseRepository hooks:**
- [ ] before_create, after_create, before_write, after_write, before_unlink, after_unlink

**Response Enrichers:**
- [ ] `@register_enricher(model)` — module can inject computed fields into another module's response
- [ ] Example: HR module enriches CRM customer with assigned employee name

**Mutation Guards:**
- [ ] `@register_guard(model, op)` — declarative write validation
- [ ] Example: cannot delete a won opportunity

**Custom Fields (EAV):**
- [ ] `CustomFieldDef` per module — admin adds fields without migrations (JSONB `custom_fields`)
- [ ] Query engine: `?cf_vat_number=PL123` transparently filters JSONB

**Widget Injection:**
- [ ] Named slots in forms: `<WidgetSlot name="crm.customer.form.sidebar" />`
- [ ] Module registers widgets for other module's slots

**Auth extensions:**
- [ ] Superadmin impersonation: `POST /api/auth/impersonate`
- [ ] API Keys: `IrApiKey` model, `x-api-key` header -> RequestContext

**Feature Flags:**
- [ ] `get_flag(key, tenant_id)` via IrConfigParam — no separate table

**Real-time (SSE):**
- [ ] `GET /api/base/events` — SSE stream per user
- [ ] `emit_notification(user_id, type, payload)` from any module

**Audit:**
- [ ] `ir_audit_log` table — auto-wired via hooks, opt-in per model via manifest
- [ ] Saved views (perspectives): `ir_perspective` — saved filters/sorts per model per user

**Quality gates:**
- [ ] Module isolation CI check — no `from modules.X import` in `modules.Y`
- [ ] Test coverage >= 80% for orbiteus_core/

### 4B — Smart Search

- [ ] `GET /api/ai/search?q=&model=` — mode 1: filter, mode 2: action suggestions
- [ ] `?` prefix prompt mode: LLM generates domain filter, displayed as editable tags
- [ ] pgvector semantic search — defer to when needed

### 4C — Business Modules

```
hr        — Employee, Department, Contract
project   — Project, Task, Milestone
social    — Chatter, Activities, Notifications (SSE)
inventory — Warehouse, Product, StockMove
accounting — Invoice, Payment
```

Each module = just `manifest.py + model/ + actions.py + security/` -> full CRUD + UI + command palette.

### DEFER to V2

- Query Index (denormalized search for custom fields) — when pgvector enters
- Data Sync with cursor resumption — dedicated `data_sync` module
- Integrations Registry (plugin marketplace)
- Field-level encryption (AES-GCM per tenant + KMS) — GDPR module
- Workflow saga compensation — Temporal.io handles natively

---

## 14. ADR (Architectural Decision Records)

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-10 | SQLAlchemy imperative mapping (not declarative) | Full control over mapping, no magic |
| 2026-03-10 | PostgreSQL only (not SQLite in prod/tests) | UUID, JSONB, pgvector, RLS — SQLite lacks these |
| 2026-03-10 | Pydantic schema = auto-CRUD schema = UI config | One model does everything — zero duplication |
| 2026-03-12 | AI-native = Command Palette, not auto-execute agent | User controls actions, AI only ranks/suggests — security and UX |
| 2026-03-12 | No relationship() cross-module | Prevents coupling — modules communicate only through FK UUID |
| 2026-03-12 | actions.py in every module (not just REST) | REST = HTTP interface, Action = business unit — separation of layers |
| 2026-03-12 | Response Enrichers for cross-module field injection | Module HR can enrich CRM response without editing CRM — isolation preserved |
| 2026-03-12 | Mutation Guards for declarative write validation | Block operations without hardcoding in handler — domain logic outside CRUD |
| 2026-03-12 | Widget Injection via named slots | Module HR injects widget into CRM form without editing CRM — composability |
| 2026-03-12 | Feature flags via IrConfigParam (not separate table) | Same effect, fewer tables, zero additional migrations |
| 2026-03-12 | SSE for notifications (not WebSocket) | Simpler infra, sufficient for in-app notifications and progress bars |
| 2026-03-18 | 4-phase development axis (Arch -> Backend -> Frontend -> Features) | Clear sequential flow, each phase must close before next starts |
