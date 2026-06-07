# 06 — Authentication

## Tokens

- **Access token** — JWT signed HS256, TTL **15 minutes**, claims:
  - `sub` (user_id), `tenant_id`, `scope` (`internal` | `portal` | `ai`),
    `roles`, `jti`, `iat`, `exp`.
- **Refresh token** — JWT signed HS256, TTL **7 days**, rotates on use.
  - On refresh, the old `jti` is added to a Redis revocation list with
    `EXPIRE = remaining_exp` so it cannot be replayed.
- **Share-link token** — JWT signed HS256, custom TTL (default 7 days),
  `scope = portal`, `aud` claim set to the resource URI.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/login` | Email + password (+ optional `totp_code`) → access + refresh |
| POST | `/api/auth/refresh` | Refresh token → new pair (rotation) |
| POST | `/api/auth/logout` | Revokes current `jti` (Redis blacklist) |
| POST | `/api/auth/2fa/enroll` | TOTP secret + QR code |
| POST | `/api/auth/2fa/verify` | One-time code; promotes session |
| POST | `/api/auth/password/reset` | Email-driven reset link |
| POST | `/api/auth/share` | Mints a portal share-link token |

## 2FA

- TOTP via `pyotp`, secrets stored in `users.totp_secret` (encrypted at rest).
- When `users.totp_enabled` is true, `POST /api/auth/login` with email + password
  alone returns **HTTP 200** and JSON `{ "requires_totp": true, "access_token": "", ... }`
  **without** setting session cookies. Submit the same email + password again with
  `totp_code` (6-digit TOTP or a normalized recovery code); on success the handler
  issues tokens and sets cookies like a normal login.
- The admin UI `/login` page shows a second step when `requires_totp` is true.
- Recovery codes are bcrypt-hashed, single-use; see `orbiteus_core.security.recovery_codes`.

## Session model

The browser-facing **Admin UI** uses an httpOnly cookie session driven by the
backend; non-browser clients keep using `Authorization: Bearer …`. See
[ADR 0017](./adr/0017-httponly-cookie-session.md) for the full rationale.

- **Stateless JWT.** Tokens are unchanged; only the *transport* differs.
- **Cookies** (set by `/api/auth/login`, `/api/auth/refresh`, cleared by
  `/api/auth/logout`):
  - `orbiteus_token`   — access JWT, `Path=/`, `HttpOnly`, `SameSite=Lax`,
    `Secure` in production, TTL = 15 minutes.
  - `orbiteus_refresh` — refresh JWT, `Path=/api/auth`, `HttpOnly`,
    `SameSite=Lax`, `Secure` in production, TTL = 7 days.
- **Resolution order** (`backend/orbiteus_core/security/middleware.py`):
  1. `Authorization: Bearer …` header.
  2. `orbiteus_token` cookie.
- **Edge gate.** `admin-ui/src/proxy.ts` (Next 16 successor of
  `middleware.ts`) redirects every protected route
  to `/login?next=<path>` when the cookie is missing — except `/`, which
  redirects to `/welcome` — eliminates the Flash Of Authenticated Content the
  previous client-only gate produced.
- **Admin `/api` hop.** `admin-ui/src/app/api/[[...path]]/route.ts` proxies to
  FastAPI (`BACKEND_URL`) so responses keep `Set-Cookie` (plain `next.config`
  rewrites to an external host can drop auth cookies).
- **Portal**: cookie + JWT hybrid (share-link exchanged for a portal-scoped
  cookie); CSRF token required on state-changing requests.
- **Revocation list** (`jti` blacklist) lives in Redis, scoped by tenant_id;
  middleware checks every request, including refresh rotation and logout.

## Password storage

- bcrypt direct (passlib 4.x is incompatible).
- `bcrypt.gensalt(rounds=12)` minimum; configurable per environment.
- Failed login attempts: rate-limited per email + IP via Redis token bucket
  (see `30-rate-limiting.md`).

## Share-link flow (portal scope)

```
1. Internal user opens a record (e.g. crm.lead/123)
2. Clicks "Share with client" → modal: TTL, allowed actions (read/comment)
3. POST /api/auth/share { resource: "crm.lead/123", ttl: 7d, perms: ["read","comment"] }
4. Server returns a signed URL: https://portal.example.com/s/<base64-token>
5. External user opens link → portal-ui exchanges token for cookie session
   bound to scope=portal and the specific resource
```

The share-link grants no other access. RBAC layer 5 (scope) restricts the
token to the resource URI in `aud`.

## Admin UI vs Portal UI auth boundary

- Admin UI lives on a single origin per deployment (e.g. `app.example.com`).
- Portal UI lives on a separate origin (e.g. `portal.example.com` or
  `*.portal.example.com` per tenant).
- CORS allows only declared origins; `cors_origins` is a JSON list per env.
- Cookies are never shared between `app.*` and `portal.*` (different domains).

## What's mandatory

- All endpoints require auth except: `/api/auth/login`, `/api/auth/refresh`,
  `/api/auth/password/reset`, `/api/base/health`, `/api/base/branding`,
  `/api/base/ui-config` (anonymous read of public metadata).
- Password reset emails go through the mail engine; tokens are single-use.
- 2FA is optional per user but enforced per role via `users.is_2fa_required`.
