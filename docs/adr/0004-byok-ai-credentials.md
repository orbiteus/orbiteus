# ADR-0004: BYOK AI credentials with Fernet

- **Status:** Accepted
- **Date:** 2026-05-03
- **Context tags:** backend, security, ai

## Context

Engine cannot ship shared AI provider keys. Each tenant supplies their own.
Keys must be encrypted at rest and inaccessible from logs or audit dumps.

## Decision

Provider credentials live in `base_ai_credential` (one row per tenant ×
provider), encrypted with Fernet using `AI_SECRET_KEY` from environment.
Endpoints `POST /api/ai/credentials` (set + ping), `GET` (list without
secrets), `DELETE` (remove).

## Consequences

- Adopters need to supply `AI_SECRET_KEY` at deploy time and back it up
  separately.
- Rotating `AI_SECRET_KEY` requires re-encryption of existing rows; offer a
  CLI helper.
- Provider integration code never sees plaintext keys outside the
  `providers/` boundary.

## Alternatives considered

- External KMS (Vault / AWS KMS) — adds an operational dependency too big for
  MVP. Compatible later via a `KmsProvider`.
- Storing keys in env vars per tenant — does not scale beyond a handful of
  tenants and rotates poorly.

## References

- `docs/15-ai-layer.md`
- `docs/18-security.md`
