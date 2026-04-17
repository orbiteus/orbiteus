<div align="center">
  <a href="https://orbiteus.com">
    <img src="docs/assets/logo-readme.svg" alt="Orbiteus" width="320" />
  </a>
</div>

# Orbiteus — AI-Native, Composable ERP/CRM Engine

**Website:** [orbiteus.com](https://orbiteus.com)

> **Build your own business management tools 10x faster** than forcing your business into the rigid constraints of legacy off-the-shelf systems.
>
> Feel the freedom of managing your business live — through hyper-personalization of the system to your unique business model.

---

![Orbiteus — Customer list](docs/assets/1.png)
![Orbiteus — Command Palette](docs/assets/2.png)

---

## What is Orbiteus?

Orbiteus is **not a product** — it's a **platform for building products**.

You install the engine, configure modules, brand the UI, and get your own business application — perfectly shaped around your processes, not the other way around.

**What you can build with Orbiteus:**
- Gym chain management (members, contracts, trainers)
- Interior design studio (projects, suppliers, subcontractors)
- Transport management system (TMS)
- Niche CRM SaaS for any vertical
- Warehouse management (WMS)
- Any combination of the above

**The core promise:** `registry.register("your_module")` → database tables, full CRUD REST API, OpenAPI docs, UI (list + form + kanban), and Command Palette actions — all generated automatically. Zero boilerplate.

---

## Quick Start — One Command

```bash
git clone <repo-url>
cd orbiteus
docker compose up --build
```

That's it. Open:
- **App UI**: http://localhost:3000
- **API docs**: http://localhost:8000/api/docs

Default login: `admin@example.com` / `admin1234`

> **First run:** Docker pulls images and builds — ~2 min. Subsequent starts are instant.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 16 |
| Migrations | Alembic (auto-applied at startup) |
| Auth | JWT (python-jose) + bcrypt |
| Fuzzy search | RapidFuzz (~1ms, no LLM needed) |
| Frontend | Next.js 14 (App Router) + Mantine 8 |
| AI (optional) | Claude API — reranking when ANTHROPIC_API_KEY is set |

**100% open-source stack** — MIT/Apache/BSD, no vendor lock-in.

---

## Architecture

```
+--------------------------------------------------------------+
|  Next.js 14 (App Router)                                     |
|  Generic renderer — zero TSX per module                      |
|  CommandPalette (Cmd+K) — AI-powered action search           |
+---------------------+----------------------------------------+
                      |  /api/*  (proxy via next.config.js)
+---------------------v----------------------------------------+
|  FastAPI — Auto-routed CRUD per module model                 |
|  JWT auth · RBAC · Tenant isolation                          |
|  GET /api/base/ui-config  — schema-driven UI config          |
|  GET /api/ai/actions      — command palette actions          |
+---------------------+----------------------------------------+
                      |
+---------------------v----------------------------------------+
|  PostgreSQL 16                                               |
|  Row-level tenant isolation (tenant_id on every table)       |
+--------------------------------------------------------------+
```

### Auto-registration

```python
# api.py — entire module registration
registry.register("base")
registry.register("auth")
registry.register("crm")
# registry.register("hr")   <- uncomment = full HR module, live instantly
```

One call → the module gets:
1. SQL tables (created at startup)
2. REST API: `GET/POST /api/{module}/{model}`, `GET/PUT/DELETE /api/{module}/{model}/{id}`
3. Query param filtering: `?status=active`, `?name__contains=acme`, `?order_by=name&order_dir=desc`
4. OpenAPI schema (auto-documented)
5. UI config entry (fields, types, required flags, view definitions)
6. Command Palette actions (Cmd+K)

### Tenant isolation

Every business table has `tenant_id`. The repository layer automatically injects `WHERE tenant_id = current_tenant` on every query — no module code needed.

### Schema-driven UI

The frontend never hardcodes field names or types. It calls `GET /api/base/ui-config` and renders everything dynamically:

```json
{
  "modules": [{
    "name": "crm",
    "models": [{
      "name": "crm.customer",
      "fields": [
        { "name": "name",   "type": "text",  "required": true  },
        { "name": "email",  "type": "email", "required": false },
        { "name": "status", "type": "text",  "required": false }
      ],
      "views": {
        "list": "<list><field name='name'/>...</list>",
        "form": "<form><field name='name'/>...</form>"
      }
    }]
  }]
}
```

### AI Command Palette (Cmd+K)

Every module registers actions. Users press **Cmd+K**, type naturally ("new customer", "show pipeline"), and the engine ranks results with RapidFuzz in ~1ms — no LLM API call in the happy path.

```python
# modules/crm/actions.py
ACTIONS = [
    Action(
        id="crm.customer.create",
        label="Create Customer",
        keywords=["new customer", "add client", "nowy klient"],
        category=ActionCategory.CREATE,
        target="navigate",
        target_url="/crm/customer/new",
    ),
]
```

---

## Building a Module

### Module structure

```
backend/modules/your_module/
├── manifest.py               <- module metadata (name, version, depends_on)
├── actions.py                <- Command Palette actions
├── model/
│   ├── domain.py             <- Python dataclasses (domain objects)
│   ├── mapping.py            <- SQLAlchemy imperative mapping
│   └── schemas.py            <- Pydantic Read/Write schemas
├── controller/
│   ├── repositories.py       <- DB access layer (extends BaseRepository)
│   ├── router.py             <- Custom FastAPI routes (optional — CRUD is auto)
│   └── security.py           <- Permission checks
├── security/
│   └── access.yaml           <- RBAC rules (groups + model permissions)
└── view/
    ├── your_model_views.xml  <- list/form/kanban view definitions
    └── config.py             <- view registration
```

### Step 1 — manifest.py

```python
from orbiteus_core.manifest import ModuleManifest

manifest = ModuleManifest(
    name="inventory",
    version="1.0.0",
    depends_on=["base"],
    label="Inventory",
    description="Stock management",
)
```

### Step 2 — Domain model + SQLAlchemy mapping

```python
# model/domain.py
from dataclasses import dataclass
from uuid import UUID

@dataclass
class Product:
    id: UUID
    tenant_id: UUID
    name: str
    sku: str
    stock_qty: int = 0

# model/mapping.py
from orbiteus_core.db import metadata
from sqlalchemy import Table, Column, String, Integer
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from orbiteus_core.model_registry import model_registry
from .domain import Product

products_table = Table(
    "inventory_products", metadata,
    Column("id",        PGUUID, primary_key=True),
    Column("tenant_id", PGUUID, nullable=False, index=True),
    Column("name",      String(255), nullable=False),
    Column("sku",       String(100), nullable=False),
    Column("stock_qty", Integer, default=0),
)

model_registry.map_imperatively(Product, products_table)
```

### Step 3 — Pydantic schemas

```python
# model/schemas.py
from pydantic import BaseModel
from uuid import UUID

class ProductWrite(BaseModel):
    name: str
    sku: str
    stock_qty: int = 0

class ProductRead(ProductWrite):
    id: UUID
```

### Step 4 — Register in api.py

```python
registry.register("inventory")
```

Done. You now have:

```
POST   /api/inventory/product
GET    /api/inventory/product?sku__contains=abc&order_by=name
GET    /api/inventory/product/{id}
PUT    /api/inventory/product/{id}
DELETE /api/inventory/product/{id}
```

Plus auto-generated UI — list table, create form, edit form.

### Step 5 — Add Command Palette actions

```python
# modules/inventory/actions.py
from orbiteus_core.ai import Action, ActionCategory

ACTIONS = [
    Action(
        id="inventory.product.list",
        label="Product List",
        keywords=["products", "stock", "inventory"],
        category=ActionCategory.NAVIGATE,
        target="navigate",
        target_url="/inventory/product",
    ),
    Action(
        id="inventory.product.create",
        label="Add Product",
        keywords=["new product", "add item", "stock in"],
        category=ActionCategory.CREATE,
        target="navigate",
        target_url="/inventory/product/new",
    ),
]
```

### Step 6 — RBAC (security/access.yaml)

```yaml
groups:
  - id: inventory_manager
    label: Inventory Manager
  - id: inventory_viewer
    label: Inventory Viewer (read-only)

access:
  - model: inventory.product
    group: inventory_manager
    perm_read: true
    perm_write: true
    perm_create: true
    perm_unlink: true

  - model: inventory.product
    group: inventory_viewer
    perm_read: true
    perm_write: false
    perm_create: false
    perm_unlink: false
```

---

## Running Locally (without Docker)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install uv && uv pip install -e ".[dev]"

createdb orbiteus                          # PostgreSQL must be running
uvicorn api:app --reload --port 8000
```

### Frontend

```bash
cd admin-ui
npm install
npm run dev
```

### Tests

```bash
cd backend
pytest tests/ -v
```

Tests run against a real PostgreSQL database (`orbiteus_test`). No mocks — if it passes here, it works in production.

---

## Environment Variables

```bash
cp .env.example .env   # then edit as needed
```

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://orbiteus:orbiteus@localhost:5432/orbiteus` | PostgreSQL DSN |
| `SECRET_KEY` | `change-me-in-production` | JWT signing key — **must change in prod** |
| `BACKEND_URL` | `http://localhost:8000` | Set to `http://backend:8000` in Docker (automatic via compose) |
| `ANTHROPIC_API_KEY` | _(empty)_ | Optional — enables AI reranking in Command Palette |

---

## Development Phases

All work follows a strict sequential axis. Each phase must be closed before the next starts.

| Phase | Status | What |
|-------|--------|------|
| **1 — Architecture** | Done | Monorepo, Docker, module system, core-module-frontend contracts |
| **2 — Backend** | Done | Data models, ORM, migrations, auto-CRUD, auth, RBAC, AI actions, 30 tests |
| **3 — Frontend** | In Progress | Dynamic renderer, auto-menu, views (list, form, kanban, graph, activities) |
| **4 — Features** | Not Started | Extension patterns, Smart Search, SSE, audit, business modules (HR, Project, Inventory...) |

**Closing Phase 1–3 = working ENGINE.** Phase 4 is ongoing — adding modules per client need.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full specification.

---

## Design Principles (Non-negotiable)

| Principle | What it means |
|-----------|--------------|
| **Spec-first** | Every module has docs/spec.md before any code |
| **Module isolation** | Modules never import each other directly — only through orbiteus_core API |
| **Auto-propagation** | registry.register("x") creates everything — tables, API, UI, palette |
| **AI-native** | Every module declares Actions — business units accessible via UI and AI |
| **White-label** | No product name hardcoded in UI — everything via ir_config_param |
| **Tenant isolation** | tenant_id on every business table — enforced at repository layer |
| **RBAC everywhere** | Every action checks permissions — AI cannot bypass RBAC |
| **PostgreSQL only** | Production = Postgres. Period. |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch conventions, spec-first workflow, and how to run tests.

---

## Security

See [SECURITY.md](SECURITY.md) for how to report vulnerabilities privately and what is in scope.

---

## License

MIT
