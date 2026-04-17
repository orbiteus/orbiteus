# orbiteus_core — Engine Specification

> Status: IMPLEMENTED (v0.1)
> Moduł: orbiteus_core
> Typ: Framework engine (nie moduł biznesowy)

---

## Odpowiedzialność

`orbiteus_core` to silnik systemu. Nie zawiera logiki biznesowej.
Odpowiada za:
- Rejestrację i lifecycle modułów
- Auto-generację CRUD API
- Warstwę bazy danych (engine, session, metadata)
- Security (JWT, RBAC, RLS context)
- Bazowe typy domenowe (BaseModel, SystemModel)

---

## Pliki i ich odpowiedzialność

### config.py
Konfiguracja przez zmienne środowiskowe (pydantic-settings).

```python
class Settings:
    database_url: str          # PostgreSQL connection string
    secret_key: str            # JWT signing key
    algorithm: str             # HS256
    access_token_expire_minutes: int   # default 60
    refresh_token_expire_days: int     # default 30
    temporal_host: str         # Temporal server
    temporal_namespace: str
    app_name: str              # "ERP" — fallback jeśli brak w DB
    environment: str           # development | production
    cors_origins: list[str]
```

### base_domain.py
Bazowe dataclassy dziedziczone przez wszystkie modele.

```python
@dataclass
class BaseModel:
    """Dla modeli biznesowych z izolacją tenant/company."""
    id: UUID                    # auto-generated
    tenant_id: UUID             # RLS isolation
    company_id: UUID | None     # multi-company
    create_date: datetime       # auto
    write_date: datetime        # auto
    active: bool = True         # soft delete
    custom_fields: dict = {}    # JSONB — custom fields bez migracji

@dataclass
class SystemModel:
    """Dla tabel systemowych (ir_*) — bez tenant_id."""
    id: UUID
    create_date: datetime
    write_date: datetime
```

### mapper.py
Helper do SQLAlchemy imperative mapping.

```python
make_base_columns()    # dodaje kolumny BaseModel do tabeli
make_system_columns()  # dodaje kolumny SystemModel do tabeli
register_mapping(DomainClass, table)  # mapper_registry.map_imperatively()
```

**Decyzja:** SQLAlchemy Imperative Mapping zamiast DeclarativeBase.
**Uzasadnienie:** Czysta separacja domain (czyste dataclassy) od infrastruktury (tabele).

### repository.py
Generyczny async CRUD.

```python
class BaseRepository[T]:
    async def get(id: UUID) -> T
    async def search(domain=[], limit=100, offset=0) -> tuple[list[T], int]
    async def create(data: dict) -> T
    async def update(id: UUID, data: dict) -> T
    async def delete(id: UUID) -> None
```

**Domain syntax** (Odoo-style):
```python
domain = [("status", "=", "active"), ("tenant_id", "=", some_uuid)]
```

### auto_router.py
Generuje 5 endpointów CRUD per model automatycznie.

```
GET    /api/{module}/{model}          → search (+ pagination)
GET    /api/{module}/{model}/{id}     → get one
POST   /api/{module}/{model}          → create
PUT    /api/{module}/{model}/{id}     → update
DELETE /api/{module}/{model}/{id}     → delete
```

**Ważne:** POST/PUT używają `Request` + `model.model_validate(await request.json())`
zamiast `payload: WriteSchema` — bo FastAPI nie obsługuje dynamicznych typów w sygnaturze.

### registry.py
ModuleRegistry — serce systemu.

```python
registry.register("crm")  # rejestruje moduł
registry.bootstrap(app)   # uruchamia cały lifecycle
```

Lifecycle:
1. `_discover()` — importuje moduły, waliduje manifest
2. `_topological_sort()` — graphlib.TopologicalSorter (stdlib)
3. `_load_mappings()` — wywołuje module.mapping.setup()
4. `_register_security()` — wywołuje module.security.setup()
5. `_register_routes()` — montuje auto-CRUD + custom router
6. `_register_menus()` — wstawia ir_ui_menu

### security/middleware.py
```python
get_current_context()   # dekoduje JWT → RequestContext
require_auth()          # dependency — 401 jeśli brak tokena
require_superadmin()    # dependency — 403 jeśli nie superadmin
```

### security/rbac.py
In-memory cache uprawnień. Ładowany przy starcie z modułu base.

```python
check_model_access(ctx, model_name, perm)  # → True/False
apply_record_rules(ctx, model_name, query) # → query z WHERE
```

### security/tokens.py
```python
create_access_token(data: dict) -> str   # exp: 60 min
create_refresh_token(data: dict) -> str  # exp: 30 days
decode_access_token(token: str) -> dict
decode_refresh_token(token: str) -> dict
```

### security/passwords.py
```python
hash_password(password: str) -> str   # bcrypt
verify_password(plain, hashed) -> bool
```

**Uwaga:** używamy bezpośrednio `import bcrypt`, nie passlib (niekompatybilne z bcrypt 4.x).

### context.py
```python
@dataclass
class RequestContext:
    tenant_id: UUID | None = None
    company_id: UUID | None = None
    user_id: UUID | None = None
    roles: list[str] = []
    is_superadmin: bool = False
```

### db.py
```python
metadata          # SQLAlchemy MetaData — shared by all modules
AsyncSessionFactory  # async_sessionmaker
get_session()     # FastAPI dependency → AsyncSession
```

---

## Status implementacji

| Komponent | Status | Uwagi |
|---|---|---|
| config.py | DONE | |
| base_domain.py | DONE | |
| mapper.py | DONE | |
| repository.py | DONE | |
| auto_router.py | DONE | |
| registry.py | DONE | |
| security/middleware.py | DONE | |
| security/rbac.py | DONE | in-memory, TODO: persist to DB |
| security/tokens.py | DONE | |
| security/passwords.py | DONE | |
| context.py | DONE | |
| db.py | DONE | |
| temporal.py | PARTIAL | client helper OK, workflows TODO |
| openapi.py | TODO | custom x-erp-* extensions |

---

## Decyzje techniczne

| Decyzja | Wybór | Uzasadnienie |
|---|---|---|
| ORM style | Imperative mapping | Domain clean, bez SA coupling |
| Auth | JWT (access + refresh) | Stateless, skalowalne |
| Password | bcrypt direct | passlib 4.x incompatible |
| RBAC cache | In-memory dict | Szybkość, reload przy starcie |
| Multi-tenancy | RLS + tenant_id | Prostota, jeden connection pool |
| Python DI | lagom | Lightweight auto-wiring |
