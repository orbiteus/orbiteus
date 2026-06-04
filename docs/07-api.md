# 07 — API Conventions

## Auto-CRUD

Every registered model automatically exposes:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/{module}/{model}` | Search, filter, sort, paginate |
| GET | `/api/{module}/{model}/{id}` | Get one |
| POST | `/api/{module}/{model}` | Create |
| PUT | `/api/{module}/{model}/{id}` | Update |
| DELETE | `/api/{module}/{model}/{id}` | Delete (soft, sets `active=false`) |

Implementation in `orbiteus_core/auto_router.py`. Extra endpoints live in the
module's `controller/router.py`.

## Query parameters (list endpoints)

| Operator | Example | Domain |
|---|---|---|
| (none) | `?status=active` | `("status", "=", "active")` |
| `__contains` | `?name__contains=acme` | ilike `%acme%` |
| `__gt` / `__gte` / `__lt` / `__lte` | `?amount__gte=100` | numeric / date |
| `__in` | `?stage_id__in=a,b,c` | IN |
| `__ne` | `?status__ne=draft` | `!=` |
| `created_after` / `created_before` | `?created_after=2026-01-01` | aliases on `create_date` |
| `updated_after` / `updated_before` | — | aliases on `write_date` |
| `order_by`, `order_dir` | `?order_by=name&order_dir=asc` | sort |
| `limit`, `offset` | default 100, max 1000 | pagination |
| `name__contains=` + `limit=10` | name search for autocomplete | |

## Pagination response shape

```json
{
  "items": [ ... ],
  "total": 4321,
  "limit": 100,
  "offset": 0
}
```

## Error format

```json
{
  "detail": "Human-readable message",
  "code": "machine.code",
  "field_errors": { "email": "Invalid email" },
  "request_id": "req_..."
}
```

`request_id` is mandatory on every response (logged in nginx and app logs).

## OpenAPI

- `/api/openapi.json` — machine-readable
- `/api/docs` — Swagger UI
- Module routers are tagged by module name

Custom extensions:

- `x-orbiteus-action-id` on endpoints registered as Actions
- `x-orbiteus-realtime-topic` on endpoints that emit SSE events
- `x-orbiteus-rbac-feature` on endpoints with `requires_feature`

## Webhooks

- Outbound webhooks are **never synchronous**. They go through the Outbox.
- `base_webhook` table: subscriber URL, secret, event mask, status.
- Standard headers: `X-Orbiteus-Event`, `X-Orbiteus-Request-Id`,
  `X-Orbiteus-Signature` (HMAC-SHA256 of payload).
- Retries: exponential backoff up to 24h; after that the row goes to
  `dead_letter` and emits an Action for an admin to review.

## Idempotency

State-changing endpoints accept an `Idempotency-Key` header. The key is hashed
with `(tenant_id, user_id, route, body_hash)` and stored in Redis for 24h.
Replays return the original response.

## Rate limits

See `30-rate-limiting.md`. Default token buckets:

- `1000 / minute / tenant`
- `60 / minute / user`
- `120 / minute / IP` (anonymous endpoints)

Exceeded → `429` with `Retry-After` header.

## Webhooks vs SSE

- Webhooks go to **machines** (other systems, scripts).
- SSE goes to **browsers** of users currently viewing the resource.
- Both share the same internal event stream.

## Aggregation endpoint (planned)

```
GET /api/base/aggregate?model=crm.lead&measure=expected_revenue&group_by=stage_id
```

Returns rows of `{group_key, group_label, count, sum}`. Used by `<ResourceGraph>`
and `<AIDashboard>`. Tracked in `23-tree-spec-framework.md`.

## Attachments (filestore)

Record-linked files stored outside PostgreSQL (local path or S3-compatible
backend). Metadata lives in `base_attachments`.

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/base/attachments` | List — `?res_model=` + `?res_id=` (any user with record read), or tenant-wide `?q=` (requires `base.group_system`) |
| `POST` | `/api/base/attachments` | Multipart upload: `file`, `res_model`, `res_id`, optional `description` |
| `GET` | `/api/base/attachments/{id}` | Metadata |
| `GET` | `/api/base/attachments/{id}/download` | Binary stream |
| `DELETE` | `/api/base/attachments/{id}` | Soft-delete row + remove binary |

RBAC: model `base.attachment` plus read/write on the linked record.
Portal uploads reuse the same storage via `POST /api/portal/attachment`.

Env: `ATTACHMENT_STORAGE=local`, `ATTACHMENT_STORAGE_PATH=./data/attachments`,
`ATTACHMENT_MAX_BYTES` (default 50 MiB).
