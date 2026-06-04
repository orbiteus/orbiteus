# 28 — Open Questions

> Active design questions awaiting an ADR. When a question is resolved,
> create an ADR in `docs/adr/` and remove the entry here (or strike it through
> with a link to the ADR).

## Q1 — Embedding dimension default

Provider-dependent: 1536 (OpenAI ada-002), 1024 (Cohere), 768 (sentence-transformers).
Decision: store `dim` per row and create separate HNSW indexes per dim used,
or pick a normalized projection.

Status: drafting ADR-0005 with `dim INT` column.

## Q2 — Field-level RBAC representation

YAML in `security/fields.yaml` per module, vs centralized table `base_field_access`.

Status: undecided.

## Q3 — Recovery codes for 2FA

Encrypted at rest with `AI_SECRET_KEY` (already in env), or a separate key.

Status: undecided. Trade-off: more keys vs blast radius on rotation.

## Q4 — Magic links for portal users

TTL, single-use, IP pinning. How to handle email forwarding (link sent to
forwarding alias).

Status: undecided.

## Q5 — `custom_fields` schema validation

Currently free-form JSONB. Declarative schema per tenant in
`custom_fields_def`?

Status: needs PoC before ADR.

## Q6 — Multi-region demo

Demo is single-region. For prospects in different regions, do we deploy
multi-region with read replicas, or rely on CDN for the static admin UI and
keep API regional?

Status: low priority.

## Q7 — Telemetry opt-in

Anonymous usage stats sent to `telemetry.orbiteus.com` (planned)?
Strict opt-in only, never PII.

Status: undecided. Privacy-first default would be off.

## Q8 — AI streaming protocol

Server-side streaming over chunked HTTP (`text/event-stream`) vs WebSocket.
SSE is the default for realtime; reusing it for AI streaming keeps one
mechanism.

Status: leaning SSE; tracking in tree-spec rather than ADR until proven.

## How to use this file

- Add a new `Qn` entry when a question is concrete enough to debate but not
  yet ready for a decision.
- Cross-reference from `pre-prompt.md` doc map only when the question becomes
  immediately relevant for AI agents.
- When resolved, replace the entry with `~~Q1 — ...~~` and link the new ADR
  in `docs/adr/`. (Example: ADR-0005 covers embedding storage decisions.)
