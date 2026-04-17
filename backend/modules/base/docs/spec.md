# Moduł base — Specification

> Status: IMPLEMENTED (v0.1)
> depends_on: []
> auto_install: True (zawsze instalowany jako pierwszy)

---

## Cel modułu

Moduł `base` to fundament całego systemu. Definiuje:
1. Obiekty infrastrukturalne (Tenant, Company, User, Partner)
2. System objects (ir_*) — metadane frameworka queryable przez API
3. Branding (app.name, app.logo_url z ir_config_param)
4. Public endpoints: /health, /branding, /modules, /menus

---

## Modele domenowe

### Tenant
Najwyższy poziom izolacji. Jedna organizacja = jeden tenant.
```python
id, name, slug, plan, is_active, created_at
```
- `slug` — unikalny identyfikator URL (np. "cosmonauts")
- `plan` — "free" | "pro" | "enterprise"
- Tabela: `base_tenants`
- Typ: SystemModel (brak tenant_id — jest tenantEM)

### Company
Spółka w obrębie tenanta. Tenant może mieć wiele spółek.
```python
id, tenant_id, name, currency_code, country_code,
vat, email, phone, city, address, parent_company_id
```
- `parent_company_id` — hierarchia spółek (holding)
- Tabela: `base_companies`

### User
Użytkownik systemu. Należy do tenanta, może być w wielu spółkach.
```python
id, tenant_id, email, name, password_hash,
company_ids: list[UUID],   # multi-company
role_ids: list[str],       # RBAC roles
language, timezone,
is_active, is_superadmin,
totp_enabled, totp_secret,
last_login
```
- `company_ids` — JSONB array
- `role_ids` — JSONB array (np. ["base.group_user", "crm.salesman"])
- Tabela: `base_users`

### Partner
Kontakt zewnętrzny (klient, dostawca, osoba). Shared resource w module.
```python
id, tenant_id, company_id, name, email, phone,
mobile, street, city, zip_code, country_code,
vat, website, is_company, parent_id,
lang, comment, tags: list[str]
```
- `is_company` — firma vs osoba prywatna
- `parent_id` — osoba należy do firmy (hierarchia kontaktów)
- Tabela: `base_partners`

---

## System Objects (ir_*)

### ir_model
Auto-wypełniany przy rejestracji modułu. Przeglądalny przez UI.
```python
id, model_name, label, module, is_transient, description
```
Tabela: `base_ir_models`

### ir_model_fields
Pola modeli. Auto-wypełniane przy rejestracji.
```python
id, model_id, field_name, field_type, label,
required, readonly, is_stored
```
Tabela: `base_ir_model_fields`

### ir_model_access
Uprawnienia ról do modeli.
```python
id, model_name, role_name,
perm_read, perm_write, perm_create, perm_unlink
```
Tabela: `base_ir_model_access`

### ir_rule
Record rules — domain-based filtering per rola.
```python
id, name, model_name, role_name,
domain_force,   # np. "[('user_id', '=', current_user)]"
is_global       # True = dotyczy wszystkich ról
```
Tabela: `base_ir_rules`

### ir_ui_menu
Drzewo menu sidebar w UI.
```python
id, name, parent_id, sequence, icon, action_type,
action_id, groups: list[str]
```
Tabela: `base_ir_ui_menus`

### ir_action_window
Akcja otwierająca widok (list/form/kanban).
```python
id, name, model_name, view_type, domain, context
```
Tabela: `base_ir_action_windows`

### ir_action_server
Akcja serwerowa (Python code / workflow trigger).
```python
id, name, model_name, code, binding_model_name
```
Tabela: `base_ir_action_servers`

### ir_sequence
Sekwencje numeryczne. Używane np. do faktur: INV/2024/00001.
```python
id, name, code, prefix, suffix, padding,
number_next, number_increment, use_date_range
```
Tabela: `base_ir_sequences`

### ir_config_param
Key-value store parametrów systemowych. Używany dla brandingu.
```python
id, key, value, description
```
Klucze systemowe:
- `app.name` — nazwa aplikacji w UI
- `app.logo_url` — URL logo
- `app.favicon_url` — URL favicon

Tabela: `base_ir_config_params`

### ir_cron
Zaplanowane zadania. Bridge do Temporal.io schedules.
```python
id, name, function_name, module_name,
interval_number, interval_type,   # "minutes"|"hours"|"days"|"weeks"|"months"
is_active, next_call, last_call,
priority
```
Tabela: `base_ir_crons`

### ir_mail_template
Szablony emaili (Jinja2).
```python
id, name, model_name, subject, body_html,
from_email, reply_to, lang
```
Tabela: `base_ir_mail_templates`

### ir_attachment
Pliki attached do rekordów.
```python
id, tenant_id, name, model_name, record_id,
file_path, file_size, mimetype, checksum
```
Storage: LocalFS na start, S3-compatible interface (easy swap).
Tabela: `base_ir_attachments`

---

## API Endpoints

### Auto-CRUD (generowane przez AutoRouter)
Każdy model powyżej ma 5 endpointów: GET list, GET one, POST, PUT, DELETE.
Prefix: `/api/base/`

Przykłady:
```
GET  /api/base/user
GET  /api/base/user/{id}
POST /api/base/user
PUT  /api/base/user/{id}
DELETE /api/base/user/{id}
```

### Custom endpoints
```
GET /api/base/health          → {"status": "ok"}
GET /api/base/branding        → {name, logo_url, favicon_url}  [public, no auth]
GET /api/base/modules         → lista załadowanych modułów [superadmin]
GET /api/base/menus           → drzewo menu [auth]
```

---

## Branding flow

```
1. Startup → _seed_branding() wstawia domyślne rekordy ir_config_param jeśli nie istnieją
2. GET /api/base/branding → czyta z ir_config_param
3. Frontend BrandingContext → fetch przy starcie aplikacji
4. useBranding() → hook używany w AppShell header i Login page
5. Fallback: NEXT_PUBLIC_APP_NAME z .env.local
```

Zmiana nazwy/logo: PUT /api/base/ir-config-param/{id} lub SQL update.

---

## Security seeds

Przy starcie ładowane do RBAC cache (modules/base/security.py):
- `base.group_system` — pełny dostęp do wszystkich modeli base
- `base.group_user` — odczyt partner i company

---

## Status implementacji

| Komponent | Status | Uwagi |
|---|---|---|
| domain.py | DONE | 17 modeli |
| mapping.py | DONE | 17 tabel |
| repositories.py | DONE | |
| schemas.py | DONE | |
| security.py | DONE | |
| router.py | DONE | |
| Branding endpoint | DONE | |
| ir_model auto-fill | TODO | przy module load wstawić rekordy |
| ir_sequence engine | TODO | nextval() funkcja |
| ir_cron → Temporal | TODO | |
| Attachments upload | TODO | |
