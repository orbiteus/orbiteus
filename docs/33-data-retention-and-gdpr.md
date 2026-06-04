# 33 — Data Retention & GDPR

## Principles

- Process only what's needed to deliver the service.
- Retain only as long as legally or operationally necessary.
- Make user rights (DSAR, RTBF) executable as engine endpoints.
- Tenants can configure retention within engine-level minimums.

## Categories of data

| Category | Examples | Default retention |
|---|---|---|
| Active business records | `crm.person`, `crm.lead`, attachments | While tenant is active |
| Soft-deleted records | `active=false` | 30 days, then hard delete |
| Audit log (`base_audit_log`) | every CRUD + auth event | 365 days |
| Logs (stdout) | request logs | 30 days |
| Metrics | Prometheus | 90 days |
| Backups | encrypted full + WAL | see `31-backups-and-dr.md` |
| AI prompts | only `prompt_id` + token counts in audit | no raw prompt retained beyond tool call |

## Configuration knobs

- `base_config_param "retention.audit_days"` (default 365).
- `base_config_param "retention.soft_delete_days"` (default 30).
- `base_config_param "retention.logs_days"` (default 30).
- Tenant admins can set tenant-level overrides; engine defaults are floors.

## DSAR (Data Subject Access Request)

```
POST /api/base/dsar/export
{ "subject_email": "user@example.com" }
→ 202 Accepted, returns DSAR job id
```

The job runs in Celery, gathers all rows referencing the subject across
modules (using `subject_resolver` registered per module), and produces a
JSON archive uploaded to a signed URL.

## RTBF (Right To Be Forgotten)

```
POST /api/base/dsar/erase
{ "subject_email": "user@example.com", "reason": "..." }
→ 202 Accepted
```

The job:

1. Pseudonymizes referencing rows (replaces name/email/phone with hashes).
2. Redacts the subject's diff entries in `base_audit_log`.
3. Removes raw PII from attachments where possible.
4. Records the erasure event with `actor=system`.

Some data is exempt (e.g. invoices required by tax law); the engine flags
them and explains in the report.

## Anonymization helpers

- `subject_resolver.py` per module declares how to find rows for a subject.
- `pseudonymize(field)` — deterministic SHA-256 with tenant pepper.
- `redact_diff(audit_row)` — replaces values in `diff` with `[redacted]`.

## Cross-border data

- Engine does not move data between regions automatically.
- Per-tenant `region` setting determines DB and S3 bucket location (in
  multi-region deployments).

## Telemetry and analytics

- Engine ships **no** outbound telemetry by default.
- Optional anonymous usage stats are opt-in per tenant; never PII.

## Audit log redaction

When required, audit rows can be redacted:

- The row remains (so the timeline is preserved).
- The `diff` JSON is replaced with `{"_redacted": true}`.
- A redaction marker logs `actor=system`, `metadata.reason`.

## Tests

- DSAR export contains rows referencing the subject from at least three
  modules.
- RTBF erasure pseudonymizes consistently across modules.
- Redacted audit rows still appear in queries but with redacted contents.
