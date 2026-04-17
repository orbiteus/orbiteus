# Orbiteus — Phase 2: Backend Specification & Dependency Tree

> Living document. Check boxes [x] as items are completed.
> Last updated: 2026-03-19
> Target: Backend mature enough to build a real CRM/ERP on top of it.

---

## 1. Vision

The backend is the **engine core**. Every business module (CRM, HR, Inventory) is
built on top of `orbiteus_core` which provides:

- Auto-CRUD with full-featured ORM (relations, computed fields, hooks)
- RBAC at model, record, and field level
- Workflow engine with guards and actions
- Activity/chatter system (notes, calls, follow-ups on any record)
- Email integration (templates, SMTP, queue)
- File attachments (upload, download, storage)
- Document numbering (atomic sequences)
- Audit trail (who changed what, when, diff)
- Import/export (CSV at minimum)
- Reporting (aggregation endpoints, PDF generation)
- Cron jobs that actually execute

**Definition of Done for Phase 2:**
> A developer writing a new module gets: auto-CRUD with relation resolution,
> computed fields, hooks, workflow support, activity log, file attachments,
> audit trail, and sequence generation — without writing any of that infrastructure.
> All of this works through `BaseRepository` and `orbiteus_core` automatically.

---

## 2. Current State (as-is audit)

| Feature | Status | Notes |
|---------|--------|-------|
| Auto-CRUD (5 endpoints per model) | DONE | Works, auth-gated |
| Tenant isolation | DONE | Automatic in BaseRepository |
| JWT + bcrypt + TOTP 2FA | DONE | Fully implemented |
| RBAC model access | DONE | Cache loaded at startup |
| RBAC record rules | DONE | Code exists, needs more tests |
| Query param filtering | DONE | eq, contains, gte, gt, lte, lt, in, ne |
| AI Action Registry + RapidFuzz | DONE | ~1ms, optional LLM reranking |
| UI config from Pydantic schemas | DONE | Field types, required flags, views |
| Alembic migrations | DONE | Single initial migration, runs at startup |
| **Field relations (many2one)** | **MISSING** | Returns raw UUID, no eager loading |
| **Repository hooks** | **MISSING** | No before/after create/write/unlink |
| **Computed fields** | **MISSING** | No mechanism at all |
| **Onchange handlers** | **MISSING** | No auto-fill on field change |
| **Workflow engine** | **PARTIAL** | CRM-specific only, no generic engine, no guards |
| **Activity / chatter** | **MISSING** | No mail_message, mail_activity models |
| **Email integration** | **STUB** | ir_mail_template exists, no send function |
| **File attachments** | **STUB** | ir_attachment table exists, no upload/download |
| **Sequence generation** | **STUB** | ir_sequence table exists, no next_val() |
| **Audit trail** | **MISSING** | Only timestamps, no user/field tracking |
| **Import / export** | **MISSING** | No CSV/Excel support |
| **Reporting / aggregation** | **MISSING** | No aggregate query builder or PDF |
| **Server actions** | **STUB** | ir_action_server exists, no execution |
| **Record duplication** | **MISSING** | No copy/clone method |
| **Multi-company switcher** | **PARTIAL** | Basic filter works, no switch endpoint |
| **Currency conversion** | **MISSING** | currency_code field exists, no rates |
| **PDF generation** | **MISSING** | No report engine |
| **Cron execution** | **STUB** | worker.py exists, WORKFLOWS list empty |
| **Docker** | **BROKEN** | Crashes on RBAC cache JSON decode |
| **created_by / modified_by** | **MISSING** | No user attribution on records |
| **Tests** | **PARTIAL** | 41 tests, many gaps |

---

## 3. Specification

### 3.1 Field Relations

Every FK field (e.g. `customer_id`) must resolve to a nested object in API responses.

```python
# GET /api/crm/opportunity/123 — current (broken):
{"customer_id": "550e8400-e29b-..."}

# GET /api/crm/opportunity/123 — target:
{
  "customer_id": "550e8400-e29b-...",
  "customer_id__name": "ACME Corp",
  "customer_id__display": "ACME Corp"
}
```

Implementation:
- Detect FK fields by `_id` suffix in Pydantic schema
- After main query, batch-fetch related records (avoid N+1)
- Inject `{field}__name` and `{field}__display` into response
- In list view: same batch resolution for all rows
- UI config: `type: "many2one"` + `relation: "crm.customer"` in field metadata

### 3.2 Repository Hooks

BaseRepository emits hooks around every CRUD operation:

```python
class BaseRepository:
    async def create(self, vals):
        vals = await self._run_hooks("before_create", vals)
        record = await self._insert(vals)
        await self._run_hooks("after_create", record)
        return record

    async def write(self, record_id, vals):
        old = await self.get(record_id)
        vals = await self._run_hooks("before_write", old, vals)
        record = await self._update(record_id, vals)
        await self._run_hooks("after_write", old, record)
        return record

    async def unlink(self, record_id):
        record = await self.get(record_id)
        await self._run_hooks("before_unlink", record)
        await self._delete(record_id)
        await self._run_hooks("after_unlink", record)
```

Hook registration:
```python
# In module repository
class CustomerRepository(BaseRepository):
    async def _after_create(self, record):
        # send welcome email, create default pipeline, etc.
        await send_welcome_email(record)
```

### 3.3 Computed Fields

Fields that are calculated from other fields, not stored in DB:

```python
# In Pydantic Read schema:
class OpportunityRead(BaseModel):
    expected_revenue: float
    probability: float
    weighted_revenue: float  # computed: expected_revenue * probability / 100
```

Implementation:
- Mark fields as `computed=True` in schema metadata
- After loading record, run compute functions
- Optionally store computed values (for filtering/sorting)
- Aggregated fields: `total_opportunities` on Customer → COUNT query

### 3.4 Audit Trail

Every write operation records who changed what:

```
ir_audit_log:
  id, timestamp, user_id, model_name, record_id,
  operation (create|write|unlink),
  changes (JSONB: {"field": {"old": X, "new": Y}})
```

- Auto-wired via repository hooks (after_create, after_write, after_unlink)
- `created_by_id` and `modified_by_id` FK on every BaseModel
- API: `GET /api/base/audit-log?model=crm.customer&record_id=X`

### 3.5 Activity / Chatter

Communication and follow-up system attached to any record:

```
mail_message:
  id, res_model, res_id, author_id, body, message_type (comment|note|system),
  create_date, parent_id (threading)

mail_activity:
  id, res_model, res_id, activity_type (call|email|meeting|todo),
  summary, note, date_deadline, user_id (assigned to),
  state (planned|done|overdue|cancelled), done_date
```

API:
- `GET /api/base/messages?res_model=crm.customer&res_id=X` — thread
- `POST /api/base/messages` — add note/comment
- `GET /api/base/activities?user_id=me&state=planned` — my activities
- `POST /api/base/activities` — schedule follow-up
- `PUT /api/base/activities/{id}` — mark done

### 3.6 Email Integration

```python
# Config
SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, SMTP_TLS

# Service
async def send_mail(template_id, record_id, recipient_email):
    template = await get_template(template_id)
    body = render_jinja2(template.body_html, record)
    subject = render_jinja2(template.subject, record)
    await smtp_send(subject, body, recipient_email)

# Queue (via Temporal or simple table)
mail_queue: id, template_id, record_id, recipient, state (pending|sent|failed), error
```

### 3.7 File Attachments

```
POST   /api/base/attachment           — upload (multipart/form-data)
GET    /api/base/attachment/{id}/download  — stream file
DELETE /api/base/attachment/{id}       — remove
GET    /api/base/attachment?res_model=crm.customer&res_id=X — list attachments

Storage backends (configurable):
- disk (default): ATTACHMENT_PATH=/data/attachments
- s3: S3_BUCKET, S3_REGION, S3_ACCESS_KEY, S3_SECRET_KEY
```

### 3.8 Sequence Generation

Atomic document numbering:

```python
# Usage in service layer:
invoice_number = await sequence_next_val("account.invoice")
# → "INV/2026/00042"

# Implementation: SELECT FOR UPDATE + increment + format
async def sequence_next_val(code: str) -> str:
    async with session.begin():
        seq = await session.execute(
            select(IrSequence).where(IrSequence.code == code).with_for_update()
        )
        # increment, format with prefix/suffix/padding, return
```

### 3.9 Workflow Engine

Generic state machine:

```python
# Module declares workflow in manifest or dedicated file:
WORKFLOWS = {
    "crm.opportunity": {
        "field": "status",
        "states": ["draft", "qualified", "proposal", "won", "lost"],
        "transitions": [
            {"from": "draft", "to": "qualified", "guard": "has_customer"},
            {"from": "qualified", "to": "proposal", "guard": "has_revenue"},
            {"from": "proposal", "to": "won", "action": "on_won"},
            {"from": "proposal", "to": "lost", "action": "on_lost"},
            {"from": "*", "to": "lost", "action": "on_lost"},
        ]
    }
}

# Guard: function that returns True/False
async def has_customer(record) -> bool:
    return record.customer_id is not None

# Action: side effect on transition
async def on_won(record):
    await send_template("crm.won_notification", record)
    await create_activity(record, "Schedule onboarding call")
```

### 3.10 Import / Export

```
POST /api/base/import — upload CSV, map fields, dry-run, commit
GET  /api/{module}/{model}?format=csv — export as CSV
GET  /api/{module}/{model}?format=xlsx — export as Excel (optional)
```

### 3.11 Reporting

```
GET /api/base/report/aggregate?model=crm.opportunity&measure=expected_revenue&group_by=stage_id
→ [{"stage_id": "uuid", "stage_name": "Proposal", "sum": 150000, "count": 12, "avg": 12500}]

# PDF (Phase 2b — defer if needed):
GET /api/base/report/pdf?template=crm.pipeline_report&params=...
→ binary PDF stream
```

### 3.12 created_by / modified_by

Every BaseModel record tracks the user who created and last modified it:

```python
class BaseModel:
    created_by_id: UUID | None  # FK to base_users
    modified_by_id: UUID | None  # FK to base_users
    create_date: datetime
    write_date: datetime
```

Auto-populated from `RequestContext.user_id` in BaseRepository.create() and write().

---

## 4. Dependency Tree

```
PHASE 2 — BACKEND (COMPLETE)
│
├── 2.0 CORE ENGINE (existing, verified)
│   ├── [x] 2.0.1 FastAPI + SQLAlchemy 2.0 imperative mapping + asyncpg
│   ├── [x] 2.0.2 Pydantic v2 Read/Write schemas per model
│   ├── [x] 2.0.3 Auto-CRUD: 5 endpoints per registered model
│   ├── [x] 2.0.4 Query param filtering (eq, contains, gte, gt, lte, lt, in, ne)
│   ├── [x] 2.0.5 Query ordering (order_by + order_dir)
│   ├── [x] 2.0.6 Pagination (offset + limit + total count)
│   ├── [x] 2.0.7 Tenant isolation automatic in BaseRepository
│   ├── [x] 2.0.8 JWT auth + bcrypt + TOTP 2FA
│   ├── [x] 2.0.9 RBAC model access (ir_model_access + cache)
│   ├── [x] 2.0.10 RBAC record rules (ir_rule + domain filtering)
│   ├── [x] 2.0.11 RBAC feature check in AI resolver (_user_has_feature)
│   ├── [x] 2.0.12 Module lifecycle (register → bootstrap → routes)
│   ├── [x] 2.0.13 AI Action Registry + RapidFuzz resolver
│   ├── [x] 2.0.14 UI config builder (Pydantic introspection + XML views)
│   ├── [x] 2.0.15 Lifespan (replaced deprecated on_event)
│   ├── [x] 2.0.16 RBAC cache loaded at startup (_reload_rbac_cache)
│   └── [x] 2.0.17 Alembic migrations (initial migration + upgrade head)
│
├── 2.1 FIELD RELATIONS
│   ├── [ ] 2.1.1 Detect FK fields by _id suffix in registered models
│   │   └── In auto_router or repository, scan table columns for FK references
│   ├── [ ] 2.1.2 Batch-resolve FK → {field}__name in list responses
│   │   └── depends on: 2.1.1
│   │   └── After main SELECT, batch SELECT related records by collected IDs
│   │   └── Inject __name fields into each response dict
│   ├── [ ] 2.1.3 Resolve FK in single-record GET response
│   │   └── depends on: 2.1.1
│   ├── [ ] 2.1.4 UI config: mark many2one fields with relation model name
│   │   └── depends on: 2.1.1
│   │   └── /api/base/ui-config returns: {type: "many2one", relation: "crm.customer"}
│   ├── [ ] 2.1.5 Name search endpoint: GET /api/{model}?name__contains=X&limit=10
│   │   └── Already works via query param filtering — just document usage
│   └── [ ] 2.1.6 Tests: FK resolution in list and single GET
│       └── depends on: 2.1.2, 2.1.3
│
├── 2.2 REPOSITORY HOOKS
│   ├── [ ] 2.2.1 Hook infrastructure in BaseRepository
│   │   └── _before_create(vals), _after_create(record)
│   │   └── _before_write(old, vals), _after_write(old, new)
│   │   └── _before_unlink(record), _after_unlink(record)
│   │   └── Default implementations are no-ops, subclasses override
│   ├── [ ] 2.2.2 Wire hooks into create/write/unlink methods
│   │   └── depends on: 2.2.1
│   ├── [ ] 2.2.3 Tests: hook execution order and data flow
│   │   └── depends on: 2.2.2
│   └── [ ] 2.2.4 CRM: wire after_write hook for opportunity stage change → log activity
│       └── depends on: 2.2.2, 2.5.1
│
├── 2.3 CREATED_BY / MODIFIED_BY
│   ├── [ ] 2.3.1 Add created_by_id, modified_by_id columns to base_columns
│   │   └── File: orbiteus_core/mapper.py (make_base_columns)
│   │   └── Alembic migration to add columns
│   ├── [ ] 2.3.2 Auto-populate from RequestContext.user_id in BaseRepository
│   │   └── depends on: 2.3.1
│   │   └── create() → set created_by_id + modified_by_id
│   │   └── write() → set modified_by_id
│   ├── [ ] 2.3.3 Include in Read schemas (optional, don't break existing)
│   │   └── depends on: 2.3.1
│   └── [ ] 2.3.4 Tests: created_by set on create, modified_by updated on write
│       └── depends on: 2.3.2
│
├── 2.4 AUDIT TRAIL
│   ├── [ ] 2.4.1 ir_audit_log table: model, record_id, operation, user_id, changes (JSONB)
│   │   └── New table, new domain class, new mapping
│   ├── [ ] 2.4.2 Auto-log in repository hooks (after_create, after_write, after_unlink)
│   │   └── depends on: 2.2.2, 2.4.1
│   │   └── Compute JSON diff of old vs new values
│   ├── [ ] 2.4.3 GET /api/base/audit-log?model=X&record_id=Y
│   │   └── depends on: 2.4.1
│   ├── [ ] 2.4.4 Opt-in per model via manifest flag: audit=True
│   │   └── depends on: 2.4.2
│   └── [ ] 2.4.5 Tests: audit log entries created on CRUD
│       └── depends on: 2.4.2
│
├── 2.5 ACTIVITY / CHATTER
│   ├── [ ] 2.5.1 mail_message table + domain + schema + repository
│   │   └── res_model, res_id, author_id, body, message_type, parent_id
│   ├── [ ] 2.5.2 mail_activity table + domain + schema + repository
│   │   └── res_model, res_id, activity_type, summary, date_deadline,
│   │       user_id, state (planned|done|overdue|cancelled)
│   ├── [ ] 2.5.3 GET /api/base/messages?res_model=X&res_id=Y — message thread
│   │   └── depends on: 2.5.1
│   ├── [ ] 2.5.4 POST /api/base/messages — add note/comment to record
│   │   └── depends on: 2.5.1
│   ├── [ ] 2.5.5 GET /api/base/activities?user_id=me&state=planned — my todo
│   │   └── depends on: 2.5.2
│   ├── [ ] 2.5.6 POST /api/base/activities — schedule follow-up
│   │   └── depends on: 2.5.2
│   ├── [ ] 2.5.7 PUT /api/base/activities/{id} — mark done/cancel
│   │   └── depends on: 2.5.2
│   └── [ ] 2.5.8 Tests: message thread, activity lifecycle
│       └── depends on: 2.5.3, 2.5.6
│
├── 2.6 SEQUENCE GENERATION
│   ├── [ ] 2.6.1 sequence_next_val(code) — atomic SELECT FOR UPDATE + increment
│   │   └── File: orbiteus_core/sequence.py (new)
│   │   └── Format: {prefix}{year}/{padded_number}{suffix}
│   ├── [ ] 2.6.2 Seed default sequences (via module manifest)
│   │   └── depends on: 2.6.1
│   │   └── CRM: "crm.opportunity" → OPP/2026/00001
│   ├── [ ] 2.6.3 Auto-assign sequence on create (via hook or BaseRepository)
│   │   └── depends on: 2.6.1, 2.2.2
│   │   └── If model has `sequence_code` in manifest → auto-fill `reference` field
│   └── [ ] 2.6.4 Tests: concurrent next_val returns unique numbers
│       └── depends on: 2.6.1
│
├── 2.7 FILE ATTACHMENTS
│   ├── [ ] 2.7.1 POST /api/base/attachment — multipart upload
│   │   └── Store to disk (ATTACHMENT_PATH config)
│   │   └── Create ir_attachment record with res_model, res_id, mimetype, file_size
│   ├── [ ] 2.7.2 GET /api/base/attachment/{id}/download — stream file
│   │   └── depends on: 2.7.1
│   ├── [ ] 2.7.3 GET /api/base/attachment?res_model=X&res_id=Y — list attachments
│   │   └── depends on: 2.7.1
│   ├── [ ] 2.7.4 Config: ATTACHMENT_PATH, MAX_FILE_SIZE_MB
│   │   └── File: orbiteus_core/config.py
│   └── [ ] 2.7.5 Tests: upload, download, list, delete
│       └── depends on: 2.7.1, 2.7.2
│
├── 2.8 EMAIL INTEGRATION
│   ├── [ ] 2.8.1 SMTP config in settings (host, port, user, password, from, tls)
│   │   └── File: orbiteus_core/config.py
│   ├── [ ] 2.8.2 send_mail(to, subject, body_html) — low-level SMTP send
│   │   └── depends on: 2.8.1
│   │   └── File: orbiteus_core/mail.py (new)
│   │   └── Use aiosmtplib for async
│   ├── [ ] 2.8.3 send_template(template_code, record_id, recipient) — Jinja2 render + send
│   │   └── depends on: 2.8.2
│   │   └── Load ir_mail_template, render body with record context
│   ├── [ ] 2.8.4 mail_queue table — persist pending/sent/failed emails
│   │   └── depends on: 2.8.2
│   │   └── Cron job retries failed emails
│   └── [ ] 2.8.5 Tests: template rendering, send (with mock SMTP)
│       └── depends on: 2.8.3
│
├── 2.9 WORKFLOW ENGINE
│   ├── [ ] 2.9.1 Workflow definition format in module
│   │   └── WORKFLOWS dict in module manifest or workflows.py
│   │   └── States, transitions, guards, actions
│   ├── [ ] 2.9.2 WorkflowEngine.transition(record, target_state) — validate + execute
│   │   └── depends on: 2.9.1
│   │   └── Check guard conditions
│   │   └── Execute transition action
│   │   └── Update state field
│   │   └── Log to audit trail (depends on 2.4)
│   ├── [ ] 2.9.3 POST /api/{module}/{model}/{id}/transition?state=X
│   │   └── depends on: 2.9.2
│   ├── [ ] 2.9.4 GET /api/{module}/{model}/{id}/allowed_transitions
│   │   └── depends on: 2.9.2
│   │   └── Return list of valid next states (for UI statusbar)
│   ├── [ ] 2.9.5 Registry loads workflows from modules at bootstrap
│   │   └── depends on: 2.9.1
│   └── [ ] 2.9.6 Tests: valid transition, blocked guard, action execution
│       └── depends on: 2.9.2
│
├── 2.10 COMPUTED FIELDS
│   ├── [ ] 2.10.1 @computed decorator on Read schema fields
│   │   └── Mark fields that should be computed post-load
│   ├── [ ] 2.10.2 Compute engine: after loading record, run compute functions
│   │   └── depends on: 2.10.1
│   │   └── In auto_router, after repo.get/search, run compute pipeline
│   ├── [ ] 2.10.3 Aggregated fields: COUNT/SUM on related records
│   │   └── depends on: 2.10.1
│   │   └── Example: Customer.opportunity_count = COUNT(opportunities)
│   └── [ ] 2.10.4 Tests: computed field in GET response
│       └── depends on: 2.10.2
│
├── 2.11 IMPORT / EXPORT
│   ├── [ ] 2.11.1 GET /api/{module}/{model}?format=csv — export records to CSV
│   │   └── Stream response with csv.writer
│   ├── [ ] 2.11.2 POST /api/base/import — upload CSV + field mapping + commit
│   │   └── Parse CSV, validate against Pydantic schema, batch create
│   │   └── Return: {created: N, errors: [{row: X, field: Y, message: Z}]}
│   └── [ ] 2.11.3 Tests: export CSV, import CSV, import with errors
│       └── depends on: 2.11.1, 2.11.2
│
├── 2.12 REPORTING / AGGREGATION
│   ├── [ ] 2.12.1 GET /api/base/aggregate?model=X&measure=Y&group_by=Z
│   │   └── Generic aggregation endpoint
│   │   └── Measures: sum, count, avg, min, max
│   │   └── Group by: any field, including date trunc (day/week/month)
│   ├── [ ] 2.12.2 CRM stats endpoint using aggregate
│   │   └── depends on: 2.12.1
│   │   └── Revenue by stage, conversion rate, pipeline velocity
│   └── [ ] 2.12.3 Tests: aggregate queries
│       └── depends on: 2.12.1
│
├── 2.13 RECORD DUPLICATION
│   ├── [ ] 2.13.1 POST /api/{module}/{model}/{id}/copy — duplicate record
│   │   └── Copy all fields except: id, create_date, write_date, reference
│   │   └── Optionally copy related records (configurable per model)
│   │   └── Auto-append "(copy)" to name field
│   └── [ ] 2.13.2 Tests: copy with and without relations
│       └── depends on: 2.13.1
│
├── 2.14 MULTI-COMPANY
│   ├── [ ] 2.14.1 POST /api/auth/switch-company — change active company
│   │   └── Validate user has access to target company
│   │   └── Issue new JWT with updated company_id
│   ├── [ ] 2.14.2 Header: X-Company-Id for per-request company override
│   │   └── depends on: 2.14.1
│   └── [ ] 2.14.3 Tests: company switch, data isolation per company
│       └── depends on: 2.14.1
│
├── 2.15 SERVER ACTIONS / CRON
│   ├── [ ] 2.15.1 Server action executor — run Python code or Temporal workflow
│   │   └── Sandboxed execution context
│   │   └── Available: record, env (repos), user
│   ├── [ ] 2.15.2 Cron scheduler — create Temporal schedules from ir_cron records
│   │   └── depends on: 2.15.1
│   │   └── At startup: sync ir_cron → Temporal scheduled workflows
│   ├── [ ] 2.15.3 POST /api/base/action/{id}/execute — trigger server action manually
│   │   └── depends on: 2.15.1
│   └── [ ] 2.15.4 Tests: action execution, cron scheduling
│       └── depends on: 2.15.1
│
├── 2.16 DOCKER
│   ├── [ ] 2.16.1 Fix RBAC cache JSON decode crash in api.py
│   │   └── _to_list() helper for roles/domain_force fields
│   ├── [ ] 2.16.2 Verify docker compose up --build from clean checkout
│   │   └── depends on: 2.16.1
│   │   └── Health check + login + create customer + Cmd+K
│   ├── [ ] 2.16.3 Add Temporal service to docker-compose.yml (optional)
│   └── [ ] 2.16.4 Add worker service for cron/workflow execution (optional)
│       └── depends on: 2.15.2
│
├── 2.17 ONCHANGE (API-LEVEL)
│   ├── [ ] 2.17.1 POST /api/{module}/{model}/onchange — field dependency engine
│   │   └── Body: {field_changed: "customer_id", current_values: {...}}
│   │   └── Response: {updated_values: {email: "...", phone: "..."}}
│   ├── [ ] 2.17.2 Onchange declarations in model or schema
│   │   └── depends on: 2.17.1
│   │   └── @onchange("customer_id") → auto-fill email, phone
│   └── [ ] 2.17.3 Tests: onchange field auto-fill
│       └── depends on: 2.17.1
│
├── 2.18 CURRENCY (defer to Phase 4 if no multi-currency CRM needed)
│   ├── [ ] 2.18.1 ir_currency table (code, name, symbol, rounding)
│   ├── [ ] 2.18.2 ir_currency_rate table (currency_id, date, rate)
│   ├── [ ] 2.18.3 convert(amount, from_currency, to_currency, date) function
│   └── [ ] 2.18.4 Tests: currency conversion
│
├── 2.19 PDF GENERATION (defer to Phase 4)
│   ├── [ ] 2.19.1 Report template engine (Jinja2 + HTML → PDF via WeasyPrint)
│   ├── [ ] 2.19.2 GET /api/base/report/pdf?template=X&record_id=Y
│   └── [ ] 2.19.3 Tests: PDF generation from template
│
└── 2.20 TESTS
    ├── [x] 2.20.1 Auth tests (register, login, refresh, TOTP) — 8 tests
    ├── [x] 2.20.2 CRM CRUD tests (create, list, get, update, delete) — 8 tests
    ├── [x] 2.20.3 Phase 1+2 tests (ui-config, filtering, AI actions) — 10+ tests
    ├── [x] 2.20.4 RBAC tests (cache, tenant isolation, superadmin) — 3 tests
    ├── [x] 2.20.5 CRM custom endpoint tests (stats, kanban, move) — 3 tests
    ├── [x] 2.20.6 Module lifecycle tests (registry, models, actions) — 5 tests
    ├── [ ] 2.20.7 Tests for FK resolution (many2one in response)
    │   └── depends on: 2.1.6
    ├── [ ] 2.20.8 Tests for repository hooks
    │   └── depends on: 2.2.3
    ├── [ ] 2.20.9 Tests for audit trail
    │   └── depends on: 2.4.5
    ├── [ ] 2.20.10 Tests for activities/messages
    │   └── depends on: 2.5.8
    ├── [ ] 2.20.11 Tests for sequences
    │   └── depends on: 2.6.4
    ├── [ ] 2.20.12 Tests for attachments
    │   └── depends on: 2.7.5
    ├── [ ] 2.20.13 Tests for workflow
    │   └── depends on: 2.9.6
    └── [ ] 2.20.14 Target: 100+ tests passing before Phase 3
```

---

## 5. Implementation Priority

### Wave 1 — Foundation (unblocks everything else)
```
2.2.*  Repository hooks          ← everything depends on this
2.3.*  created_by / modified_by  ← basic audit, needed everywhere
2.16.1 Fix Docker crash          ← devs can't run without this
```

### Wave 2 — Core CRM features
```
2.1.*  Field relations (many2one)  ← UI is unusable without this
2.5.*  Activity / chatter          ← CRM table stakes
2.6.*  Sequence generation         ← document numbering
2.4.*  Audit trail                 ← who changed what
```

### Wave 3 — Business logic
```
2.9.*  Workflow engine             ← status transitions with guards
2.10.* Computed fields             ← aggregations, calculated values
2.7.*  File attachments            ← upload proposals, contracts
2.12.* Reporting / aggregation     ← dashboards, stats
```

### Wave 4 — Communication
```
2.8.*  Email integration           ← send quotes, notifications
2.11.* Import / export (CSV)       ← onboarding data
2.14.* Multi-company switcher      ← holding companies
2.17.* Onchange                    ← auto-fill on field change
```

### Wave 5 — Advanced (can defer to Phase 4)
```
2.13.* Record duplication
2.15.* Server actions / cron execution
2.18.* Currency conversion
2.19.* PDF generation
```

---

## 6. Verification

When all Wave 1-3 are done, this scenario must work:

```bash
# 1. Docker
docker compose up --build  # works, no crashes

# 2. Login
POST /api/auth/login → token

# 3. Create customer with auto-sequence
POST /api/crm/customer {name: "ACME"}
→ {id: "...", reference: "CUST/2026/00001", created_by_id: "admin-uuid"}

# 4. GET customer resolves FK
GET /api/crm/customer/{id}
→ {assigned_user_id: "uuid", assigned_user_id__name: "John Smith"}

# 5. Add note to customer
POST /api/base/messages {res_model: "crm.customer", res_id: "...", body: "Called, interested"}
→ 201

# 6. Schedule follow-up
POST /api/base/activities {res_model: "crm.customer", res_id: "...", activity_type: "call", date_deadline: "2026-03-25"}
→ 201

# 7. Create opportunity with workflow
POST /api/crm/opportunity {name: "Deal", customer_id: "..."}
→ {status: "draft"}

# 8. Transition with guard
POST /api/crm/opportunity/{id}/transition?state=qualified
→ 400 "Guard failed: customer required"  (if customer_id is null)
→ 200 (if customer_id is set)

# 9. Audit log
GET /api/base/audit-log?model=crm.opportunity&record_id={id}
→ [{operation: "create", user: "admin", changes: {...}}, {operation: "write", user: "admin", changes: {status: {old: "draft", new: "qualified"}}}]

# 10. Aggregate
GET /api/base/aggregate?model=crm.opportunity&measure=expected_revenue&group_by=stage_id
→ [{stage_name: "Draft", sum: 50000, count: 3}]

# 11. Upload attachment
POST /api/base/attachment (multipart) → {id, filename, size}

# 12. 100+ tests pass
pytest tests/ -v → all green
```
