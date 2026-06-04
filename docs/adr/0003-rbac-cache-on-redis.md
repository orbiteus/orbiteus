# ADR-0003: RBAC cache on Redis

- **Status:** Accepted
- **Date:** 2026-05-03
- **Context tags:** backend, security, performance

## Context

The current implementation caches `base_model_access` and `base_rule` in process
memory. With multiple FastAPI replicas, mutations require waiting for cache TTL
or restart, which is unacceptable.

## Decision

Move the RBAC cache to Redis with a 60-second TTL. Mutations to
`base_model_access` / `base_rule` publish `rbac.invalidated` on the EventBus,
which deletes affected keys.

## Consequences

- Multi-replica deployments see role changes within ≤ 60 s automatically.
- Lookup latency is one Redis round-trip (~0.5 ms in same DC).
- Need to handle Redis temporary unavailability with a fail-closed strategy.

## Alternatives considered

- Stick with in-memory + restart for changes — operationally painful.
- LDAP-style cache invalidation messages over Pub/Sub — added complexity for
  marginal latency gain.

## References

- `docs/05-rbac-multitenancy.md`
- `docs/13-cache.md`
