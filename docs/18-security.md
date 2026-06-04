# 18 — Security

## Threat model (short)

| Threat | Mitigation |
|---|---|
| Cross-tenant data leak | `tenant_id` filter in `BaseRepository` (mandatory), automated test |
| Credential theft via JWT replay | `jti` revocation in Redis, 15 min access TTL |
| Brute force on login | Token bucket per email + IP, 2FA optional/enforced |
| SQL injection | SQLAlchemy parameterized queries; no raw SQL with f-strings |
| Path traversal in attachments | Filename allowlist + UUID-prefixed storage paths |
| RCE via dependency CVE | `pip-audit` + `npm audit` in CI; weekly Dependabot |
| Secrets in repo | Pre-commit hook (`detect-secrets`); CI enforced |
| CSRF on portal | Double-submit cookie + `SameSite=Strict` |
| XSS in user content | React escapes by default; sanitize HTML server-side before storage |
| SSRF from server-side rendering | Outbound calls go through allowlist, not user-provided URLs |
| Open redirects | Whitelist of `redirect_to` paths in auth routes |

## Secrets policy

- All secrets live in env files: `.env`, `.env.demo`, `.env.prod`. All git-ignored.
- `.env.example` files contain only placeholders and explanatory comments.
- Rotation cadence:
  - `SECRET_KEY` (JWT): on suspected compromise; planned rotation requires
    a token revocation strategy (see `06-auth.md`).
  - `AI_SECRET_KEY` (Fernet): on suspected compromise; rotation requires
    re-encryption of `base_ai_credential` rows.
  - Bootstrap admin password: must be changed on first login; production
    refuses to start with the default.

## CSP / Headers

Admin UI:

- `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self' wss: https:; font-src 'self' data:; frame-ancestors 'none';`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), microphone=(), camera=()`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`

Portal UI: same as admin, plus tighter `connect-src` (only the API origin).

`unsafe-inline` for `style-src` is required by Mantine's emotion-based styling.
Future: nonce-based or hashed inline styles.

## CORS

- `CORS_ORIGINS` is a JSON list per environment.
- Default in dev: `["http://localhost:3000"]`.
- Demo: `["https://demo.orbiteus.com"]`.
- Production: explicit list of admin and portal origins per tenant.

## Input validation

- All request payloads validated by Pydantic v2 schemas at the route layer.
- `BaseRepository.create()` / `update()` re-validate via the model's Write
  schema; it is the last line of defense before the database.
- File uploads: MIME sniff + extension allowlist + size cap.

## Auth hardening

- Bcrypt cost ≥ 12.
- 2FA TOTP supported per user; can be enforced per role.
- Recovery codes (planned, tracked in tree-spec).
- Failed login → exponential backoff per email + IP.

## Dependencies policy

- License: MIT / Apache-2 / BSD only (see `27-licenses.md`).
- Adding a runtime dependency requires:
  - Justification in the PR description.
  - License check.
  - Maintenance health check (release frequency, last commit, GitHub stars).
  - ADR if it crosses a stack-defining boundary (e.g. introducing a new server,
    a new ORM, a new AI provider).

## Logging hygiene

- Never log secrets (passwords, tokens, raw provider keys).
- Never log full PII unredacted.
- Use the redaction helper before passing payloads to logs.

## Incident response (short)

1. Identify (alert / customer report / monitor).
2. Contain (revoke tokens, rotate keys, block IPs).
3. Eradicate (patch, redeploy).
4. Recover (replay outbox, sync from backup if needed).
5. Post-mortem (blameless, written, shared internally within 5 days).

## Compliance hooks

- GDPR: see `33-data-retention-and-gdpr.md` for DSAR, RTBF, retention.
- Audit log retention configurable per tenant.
- Data export (per-tenant): JSON dump endpoint reserved for tenant admins.
