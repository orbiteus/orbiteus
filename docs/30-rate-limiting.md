# 30 — Rate Limiting

Token bucket per tenant, user, and IP — implemented with Redis counters.

## Buckets

| Bucket | Default | Applies to |
|---|---|---|
| Tenant | 5000 / minute | Authenticated mutations + expensive GETs |
| User (mutations) | 600 / minute | POST/PUT/PATCH/DELETE with valid session |
| User (expensive GET) | 120 / minute | Authenticated `/api/ai/*` reads |
| IP | 300 / minute | Anonymous traffic + auth mutations |
| Anonymous endpoints | 30 / minute | `rl:anon:{route}:{ip}:{minute}` |
| Auth login | 5 / minute / email + 20 / minute / IP | `rl:auth:login:{email}:{minute}` |

**Authenticated SPA reads are not rate-limited.** `GET`/`HEAD` on normal
API routes (list views, record fetch, `/api/auth/me`) bypass all buckets so
rapid navigation in admin-ui never surfaces HTTP 429. Exempt paths include
`/api/base/ui-config` and `/api/realtime/subscribe` (SSE handshake).

Limits are configurable per environment via env vars
(`RATE_LIMIT_TENANT_PER_MINUTE`, `RATE_LIMIT_USER_MUTATIONS_PER_MINUTE`, etc.).

## Algorithm

Sliding window using counters bucketed by minute:

```
INCR rl:user:{id}:{minute}
EXPIRE rl:user:{id}:{minute} 120
```

Effective rate over 60 s = sum of current and previous minute weighted by
elapsed seconds.

For higher precision, use Redis sorted sets with scores=timestamps. Default is
the counter-based approach for simplicity.

## Response on exceed

```
HTTP/1.1 429 Too Many Requests
Retry-After: 12
Content-Type: application/json

{ "detail": "Rate limit exceeded", "code": "rate_limit.exceeded", "request_id": "..." }
```

`Retry-After` is the seconds until the next bucket starts.

## Special cases

- **AI calls** have an additional budget guard (token-based) — see `15-ai-layer.md`.
- **Webhook deliveries** are rate-limited per subscriber URL to avoid hammering
  partners that are slow to respond.
- **Bulk import** routes accept a higher limit but require an Idempotency-Key.

## Authentication path

Login attempts are rate-limited per email + IP to mitigate credential stuffing:

- 5 failed attempts / minute / email → 429 + 60 s lockout
- 20 failed attempts / minute / IP → 429 + 120 s lockout

Successful login resets the counter.

## What rate limiting does NOT do

- It is not the audit log. Excessive 429s should appear in metrics, not in
  `base_audit_log`.
- It is not abuse detection. Use a separate component for IP reputation,
  fingerprinting, or behavioral analysis.
