# 14 — Audit

## Policy: 100% mandatory, opt-out

Every CRUD operation through `BaseRepository` writes one row to `base_audit_log`.
Modules **cannot opt in** — they must explicitly **opt out** by setting
`Manifest.audit_optout = ["base_audit_log", "base_outbox", "..."]` for system log
tables that would otherwise loop.

Default tables that opt out:

- `base_audit_log` (logging the log creates infinite loops)
- `base_outbox` (transient queue)
- `base_embedding` (auto-generated, derivative)
- `presence:*` (Redis only, not in DB)

## Schema

```sql
CREATE TABLE base_audit_log (
    id           UUID PRIMARY KEY,
    tenant_id    UUID,
    actor        TEXT NOT NULL,        -- 'user' | 'ai' | 'portal' | 'system'
    user_id      UUID,
    request_id   TEXT,
    model        TEXT NOT NULL,
    record_id    UUID,
    operation    TEXT NOT NULL,        -- 'create' | 'update' | 'delete' | 'tool_call' | 'login'
    diff         JSONB,                -- {field: [old, new], ...}
    metadata     JSONB,                -- ip, user_agent, ai_prompt_id, etc.
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON base_audit_log (tenant_id, model, record_id, created_at DESC);
CREATE INDEX ON base_audit_log (tenant_id, user_id, created_at DESC);
CREATE INDEX ON base_audit_log (tenant_id, actor, operation, created_at DESC);
```

## What's logged

| Event | `operation` | Notes |
|---|---|---|
| `BaseRepository.create` | `create` | `diff = {field: [null, new]}` |
| `BaseRepository.update` | `update` | only changed fields |
| `BaseRepository.delete` | `delete` | full row snapshot in `metadata` |
| Auth login (success/fail) | `login` / `login_failed` | ip, user_agent in `metadata` |
| AI tool call | `tool_call` | `tool_name`, `args` (sanitized), `result_status` |
| Workflow transition | `workflow.transition` | `from_state`, `to_state` |

## Actor semantics

- `actor='user'` — direct human action (admin UI / portal UI).
- `actor='ai'` — AI tool call on behalf of a user; `metadata.provider` and
  optional `metadata.agent_run_id` tie it back to a chat session.
- `actor='portal'` — mutation through a share link (comment, attachment).
- `actor='system'` — scheduled jobs, internal bootstrap, migrations.
  Use `metadata.source`, `metadata.webhook_name`, or `metadata.cron_job`
  when the generic label is not enough.

## Initiator enrichment (API)

`GET /api/base/audit-log` enriches each row with an `initiator` object:

```json
{
  "kind": "user",
  "label": "Jane Doe (jane@acme.com)",
  "detail": "IP 10.0.0.1 · superadmin session",
  "user_email": "jane@acme.com",
  "user_name": "Jane Doe"
}
```

Labels are derived from `actor`, a batch join on `base_users` when
`user_id` is set, login `diff.email` for failed attempts, and
`metadata` (IP, provider, webhook/cron hints). Raw `user_id` and
`request_id` remain on the row for correlation.

AI is **never** treated as a privileged actor; the `RequestContext` of the
human user is the upper bound on permissions.

## Diff redaction

- Password / secret fields are redacted (`["***", "***"]`).
- PII can be redacted per-tenant policy (`base_audit_redaction` config table).
- Field-level RBAC (Layer 4) restricts who can read which diff fields.

## Retention

- Default: 365 days.
- Configurable per tenant in `base_config_param`.
- Old rows partitioned monthly; archived to S3-compatible storage; rehydrated
  on demand for compliance requests.

See `33-data-retention-and-gdpr.md`.

## API

```
GET /api/base/audit-log?model=crm.lead&record_id={id}
GET /api/base/audit-log?actor=ai&from=2026-01-01
```

Returns paginated rows. RBAC: `base.audit.read` feature required;
superadmins see all; tenant admins see their tenant only.

## What audit is NOT

- Not a log aggregation system. Use Loki / Vector / ClickHouse for that.
- Not a metric system. Use Prometheus.
- Not a tracing system. Use OpenTelemetry.

`base_audit_log` is for **business events** — answering "who changed what when".
