# ADR-0017: httpOnly cookie session for the Admin UI (no FOAC)

- **Status:** Accepted
- **Date:** 2026-05-03
- **Context tags:** frontend, auth, security
- **Deciders:** Engine team
- **Supersedes:** —

## Context

The Admin UI initially stored the JWT in `localStorage` and added it to every
request via an axios interceptor. This had two drawbacks:

1. **Flash Of Authenticated Content (FOAC).** The protected SSR HTML was
   served before the client-side `useEffect` had a chance to read
   `localStorage` and redirect to `/login`. Users saw the dashboard for ~1
   frame before being kicked out. Unprofessional and leaks layout details.
2. **XSS surface area.** Any third-party script ever loaded by the Admin UI
   would have full read access to the access token via `localStorage`.

We considered three approaches:

- **A. Server-set httpOnly cookie + Next.js Edge middleware.** The backend
  emits `Set-Cookie: orbiteus_token=…; HttpOnly; SameSite=Lax` on
  `/api/auth/login`. The browser sends it back automatically; the Next
  proxy (`admin-ui/src/proxy.ts`, the Next 16 successor of
  `middleware.ts`) inspects the cookie *before* rendering and redirects to
  `/login` when missing.
- **B. Client-side gate with `next/script` blocking strategy.** Continues to
  read `localStorage`, but blocks paint until the gate runs. Hacky, can't
  reach SSR, and still leaves XSS exposure.
- **C. Server-side session table.** Centralised, but stateful — adds a
  hot-path read on every request, fights our stateless JWT model, and
  duplicates Redis JTI revocation.

## Decision

Adopt **Option A**. The backend writes two httpOnly cookies on login:

| Cookie               | Path           | TTL                  | Purpose                        |
|----------------------|----------------|----------------------|--------------------------------|
| `orbiteus_token`     | `/`            | 15 min (access TTL)  | Auth on every API call         |
| `orbiteus_refresh`   | `/api/auth`    | 7 days (refresh TTL) | Reissues access without prompt |

Cookies are `HttpOnly`, `SameSite=Lax`, and `Secure` automatically when
`settings.environment == "production"`.

The backend security middleware reads the access token from
`Authorization: Bearer …` **first** (preserves machine clients and the
`@cursor/sdk`-style integrations), then falls back to the cookie.

The Admin UI ships an Edge proxy at `admin-ui/src/proxy.ts` (Next 16 file
convention — do not add a separate `middleware.ts`; Next rejects both).
In npm workspaces, set `turbopack.root` in `admin-ui/next.config.js` to the
monorepo root so Turbopack resolves `next` and still picks up this app’s
`src/proxy.ts`; otherwise the gate may not run and `/` loads without a session.

`/api/*` is **not** a `next.config` rewrite: it is proxied by
`admin-ui/src/app/api/[[...path]]/route.ts` so responses (including
`Set-Cookie` from `POST /api/auth/login`) reach the browser reliably.

- Allows `/login`, `/welcome`, `/_next/*`, `/api/*`, `/branding/*`.
- For every other path, redirects to `/login?next=<path>` if `orbiteus_token`
  is absent. **`GET /` without a cookie** redirects to `/welcome` (marketing
  landing), not `/login?next=/`.

The login page no longer touches `localStorage`. Logout posts to
`/api/auth/logout` which clears both cookies and revokes the JTI in Redis.

## Consequences

- **No FOAC.** SSR never renders authenticated routes for unauthenticated
  users — the redirect happens at the Edge.
- **No XSS token theft.** httpOnly cookies cannot be read from JS.
- **CSRF is bounded.** `SameSite=Lax` blocks cross-site form posts. State-
  changing portal links pass an additional CSRF token (existing).
- **Backwards compatibility.** Bearer token still works for non-browser
  clients; the body of `/api/auth/login` still includes both tokens for
  scripts and CI tooling.
- **One legacy cleanup.** Returning users had a `localStorage["token"]` from
  the previous deployment; `lib/api.ts` removes it on first import.

## Alternatives considered

- **B. Client-side blocking gate** — rejected: doesn't address XSS, fights
  Next App Router SSR model.
- **C. DB-backed session** — rejected: extra hot-path read, contradicts
  stateless JWT and Redis JTI revocation already in place.
- **httpOnly cookie + cross-domain (BFF on a separate origin)** — overkill
  for a single-origin deployment; reconsider if Admin UI ever moves to a
  different origin from `/api`.

## References

- `backend/orbiteus_core/security/cookies.py`
- `backend/orbiteus_core/security/middleware.py` (cookie fallback)
- `backend/modules/auth/controller/router.py` (`/login`, `/refresh`,
  `/logout`)
- `admin-ui/src/proxy.ts`
- `admin-ui/src/app/api/[[...path]]/route.ts` (server proxy; preserves `Set-Cookie`)
- `tests/test_auth_cookies.py`
- `docs/06-auth.md` § Session model
