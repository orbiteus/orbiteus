# 03 — Modules

## Directory layout

```
backend/modules/<name>/
  manifest.py            # name, version, depends_on, models, menus
  model/
    domain.py            # @dataclass — pure Python, no SQLAlchemy
    mapping.py           # SQLAlchemy Table + register_mapping()
    schemas.py           # Pydantic Read/Write
  controller/
    repositories.py      # extends BaseRepository per model
    services.py          # stateless business logic
    router.py            # custom FastAPI endpoints (beyond auto-CRUD)
  security/
    access.yaml          # role -> model -> CRUD permissions
  view/
    *_views.xml          # list / form / kanban / calendar arch
    config.py            # view registration
  actions.py             # AI Action declarations (Command Palette + AI tools)
  ai.py                  # AIModuleConfig: prompts, accessible_models, callable_actions
  bootstrap.py           # on_install / seed defaults (NOT in api.py lifespan)
  docs/spec.md           # REQUIRED before code; declares Layer + depends_on
  __init__.py
```

## `manifest.py`

```python
from orbiteus_core.manifest import ModuleManifest

manifest = ModuleManifest(
    name="crm",
    version="0.2.0",
    depends_on=["base", "auth"],
    layer="product",   # "framework" | "product"
    description="Canonical CRM example: Person, Lead, Stage, Team.",
)
```

## `domain.py`

Pure dataclasses, no SQLAlchemy:

```python
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

@dataclass
class Person:
    id: UUID
    tenant_id: UUID
    company_id: UUID | None
    name: str
    email: str | None
    phone: str | None
    kind: str             # "lead" | "customer" | "contact"
    create_date: datetime
    write_date: datetime
    active: bool = True
    custom_fields: dict = None
```

## `mapping.py`

SQLAlchemy imperative mapping:

```python
from sqlalchemy import Column, String, Table
from orbiteus_core.db import metadata
from orbiteus_core.mapper import make_base_columns, register_mapping
from .domain import Person

person_table = Table(
    "crm_persons",
    metadata,
    *make_base_columns(),
    Column("name", String(255), nullable=False),
    Column("email", String(320)),
    Column("phone", String(64)),
    Column("kind", String(32), nullable=False, server_default="contact"),
)

def setup() -> None:
    register_mapping(Person, person_table)
```

## `schemas.py`

Pydantic v2 Read / Write:

```python
from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime

class PersonRead(BaseModel):
    id: UUID
    name: str
    email: EmailStr | None
    phone: str | None
    kind: str
    create_date: datetime
    write_date: datetime

class PersonWrite(BaseModel):
    name: str
    email: EmailStr | None = None
    phone: str | None = None
    kind: str = "contact"
```

## `controller/repositories.py`

```python
from orbiteus_core.repository import BaseRepository
from ..model.domain import Person

class PersonRepository(BaseRepository[Person]):
    pass
```

## `security/access.yaml`

```yaml
crm.person:
  - role: sales_rep
    read: true
    write: true
    create: true
    unlink: false
```

## `actions.py`

```python
from orbiteus_core.ai import Action, ActionCategory

ACTIONS = [
    Action(
        id="crm.person.create",
        label="Create Person",
        keywords=["new contact", "add lead"],
        category=ActionCategory.CREATE,
        target_url="/crm/person/new",
        requires_feature="crm.persons.manage",
        icon="user-plus",
    ),
]
```

## `ai.py` (NEW — AI-native engine convention)

```python
from orbiteus_core.ai import AIModuleConfig, PromptTemplate

AI = AIModuleConfig(
    enabled=True,
    system_prompt="You are a CRM assistant for {{ tenant.name }}.",
    accessible_models=["crm.person", "crm.lead", "crm.stage", "crm.team"],
    callable_actions=["crm.person.create", "crm.lead.create", "crm.lead.move_stage"],
    embed_models=["crm.person", "crm.lead"],
    suggested_prompts=[
        PromptTemplate(id="hot_leads", label="Show hot leads this week"),
        PromptTemplate(id="weekly_summary", label="Summarize team activity this week"),
    ],
    dashboard=True,
)
```

## `bootstrap.py`

One-time seed per tenant. **Not** invoked from `backend/api.py` lifespan —
called by `registry.bootstrap(app)` after the module is loaded.

```python
async def on_install(session, ctx) -> None:
    """Seed default stages, default team, etc."""
    ...
```

## `docs/spec.md`

Required before any code. First lines must declare:

```markdown
# Module: crm

> **Layer:** product (canonical example)
> **depends_on:** [base, auth]
> **Status:** in development (CRM-MVP rename in progress)
```

## Cross-module rule

```python
# FORBIDDEN
from modules.crm.model.domain import Person

# CORRECT — UUID FK only, fetch through your own repo or core service
person_id: UUID
```

## When to add a new module — checklist

- [ ] New aggregate root that does not belong to an existing module.
- [ ] Independent RBAC matrix.
- [ ] Optional in some deployments.
- [ ] No cross-module Python imports needed.

If any answer is "no", extend an existing module instead.

## Enable / disable (Module catalog)

Orbiteus is a **modular monolith**: modules are `registry.register(...)` at
**process startup**, not hot-plugged at runtime.

| Layer | What the toggle does today |
|-------|----------------------------|
| **Persistence** | `base_config_params` key `module.<name>.enabled` (`true` / `false`) |
| **Backend read paths** | Filter **ui-config**, **i18n locales/messages**, user `language` normalization |
| **Backend API routes** | Still mounted until **process restart** (runtime unload deferred) |
| **Admin SPA** | `applyModuleToggleSideEffects()` — invalidate TanStack Query (`ui-config`, `i18n`, `resource`, `attachments`); redirect to `/` if you are on a route under a module that was just disabled |

**Operator expectation:** “Off” means hidden from nav and dependent features
(Languages, lists, etc.) without redeploy. **Not** the same as removing
`registry.register("crm")` from `api.py` — that still requires a backend restart.

**Full browser reload** is not required for catalog toggles when caches are
invalidated; use restart when you change **code** or **registry membership**.
