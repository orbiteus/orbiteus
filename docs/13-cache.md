# 13 — Cache (Redis)

One Redis 7 instance plays many roles. Each role has a key prefix.

## Role map

| Role | Key prefix | TTL |
|---|---|---|
| RBAC cache | `rbac:` | 60 s, invalidated on `base_model_access` / `base_rule` updates |
| ui-config snapshot | local in-process (not Redis) | per-process, refreshed on registry changes |
| JWT revocation list | `jti:revoked:` | until token natural expiry |
| Idempotency keys | `idem:` | 24 h |
| Rate limit token buckets | `rl:tenant:`, `rl:user:`, `rl:ip:` | rolling window |
| AI budget counters | `ai:budget:tenant:` | monthly reset |
| Realtime backplane | Redis Pub/Sub channels | n/a (transient) |
| Presence (who is viewing) | `presence:topic:` (sorted set, score=ts) | 30 s sliding |
| Lock primitives | `lock:` (SET NX EX) | task-specific |
| Celery broker | reserved by Celery | n/a |

## Why ui-config is NOT cached in Redis

- It changes only on backend restart (modules registered/unregistered).
- In-process cache is enough; Redis would add a network hop with no win.
- Cache key: `ui_config:v=<git_sha>` invalidates on deploy.

## RBAC cache

- Loaded once at `registry.bootstrap()`.
- Stored as `rbac:role:{role}:model:{model}` → JSON of CRUD flags.
- 60 s TTL provides defense in depth even if invalidation fails.
- On `base_model_access` mutation, the EventBus emits `rbac.invalidated`
  which deletes the affected keys.

## Idempotency keys

```
SET idem:<sha256(tenant:user:route:body)> <response_payload> NX EX 86400
```

Replays return the stored payload; new ones execute and set the key.

## Rate limit (token bucket)

```
INCR rl:tenant:{id}:{minute}   EX 60
```

Limits checked in middleware; exceeded returns `429` with `Retry-After`.

## Presence

- Frontend sends `POST /api/realtime/presence` every 15 s while viewing a record.
- Server `ZADD presence:tenant:{}:model:{}:record:{} <ts> <user_id>`.
- Stale users (`ts < now-30`) are removed via `ZREMRANGEBYSCORE`.
- Subscribers see the live set via SSE.

## Locks

```
SET lock:migrate ${pid} NX EX 600
```

- Used for cron-style singletons (e.g. nightly cleanup).
- Critical for multi-replica deployments.

## Operational notes

- `appendonly yes` for durability of Outbox-adjacent dedup keys.
- Memory cap configured per environment; OOM eviction policy: `allkeys-lru`.
- Backup: redis-cli `BGSAVE` cron (rare; most data is reproducible).
- Monitoring: `redis_exporter` for Prometheus.

## Sentinel / Cluster

Single node is fine to ~20 k QPS. For HA, switch to Redis Sentinel (3 nodes)
or Redis Cluster. Tracked as deferral, not MVP. See `32-multi-host-migration.md`.
