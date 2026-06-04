# 11 — Realtime

Live updates so users see each other's changes without refresh.

## Transport: Server-Sent Events (SSE)

- Default and required transport.
- One-way (server → client), text/event-stream, HTTP/1.1.
- Survives intermediaries that block WebSockets.
- Supported natively by browsers (`EventSource`).

## Why not WebSockets first

- Most CRM/ERP traffic is server → client.
- WebSocket upgrade often fails behind corporate proxies.
- SSE is cheaper to debug; a senior dev can `curl` the stream.

WebSockets are a future opt-in for bidirectional cases (collaborative cursors).
Long-polling is the fallback only when SSE is broken at the network layer.

## Endpoint

```
GET /api/realtime/subscribe
  ?topic=tenant:{tenant_id}:model:crm.lead:record:{id}
  &topic=tenant:{tenant_id}:model:crm.lead:list
```

- One request can subscribe to many topics.
- Server validates each topic against the `RequestContext` RBAC.
- Heartbeat: `event: ping` every 25 s.

## Topics

```
tenant:{tenant_id}:model:{model}:record:{id}    # one record changed
tenant:{tenant_id}:model:{model}:list           # collection changed (create/delete)
tenant:{tenant_id}:user:{user_id}:notify        # personal notifications
tenant:{tenant_id}:presence:model:{model}:record:{id}   # who is viewing
```

Tenants are isolated at the topic prefix; the SSE handler refuses topics
whose `tenant_id` does not match the request context.

## Backplane: Redis Pub/Sub

- Multiple FastAPI replicas → events from one replica must reach clients on
  another.
- Each replica subscribes to Redis Pub/Sub channels matching active topics.
- An emitter publishes once; Redis fans out.

ADR `0014` covers the choice of Pub/Sub over Streams.

## Emission points

| Source | Emits |
|---|---|
| `BaseRepository.create()` | `model.created` on record + list topic |
| `BaseRepository.update()` | `model.updated` on record + list topic |
| `BaseRepository.delete()` | `model.deleted` on record + list topic |
| Workflow transitions | `workflow.transition` on record topic |
| AI tool execution | `ai.tool.invoked` on user notify topic |
| Manual `emit()` calls in services | custom `event` strings |

Emissions go through the EventBus (in-process). For events that must survive
crashes, the emit is paired with an Outbox row (see `12-events-and-queues.md`).

## Event payload

```json
{
  "event": "model.updated",
  "model": "crm.lead",
  "record_id": "5b4d...-...",
  "tenant_id": "...",
  "actor": "user|ai|system",
  "request_id": "req_...",
  "ts": "2026-05-03T12:34:56Z",
  "diff": { "stage_id": ["draft", "qualified"] }
}
```

## nginx requirements

For SSE to actually stream, nginx in front must:

```nginx
location /api/realtime/ {
    proxy_pass http://backend:8000;
    proxy_http_version 1.1;
    proxy_buffering off;
    proxy_cache off;
    proxy_set_header Connection "";
    proxy_read_timeout 1h;
    add_header X-Accel-Buffering no;
}
```

Without `proxy_buffering off`, events get glued in the buffer until disconnect.

## Connection limits

- One worker holds 5 000–10 000 idle SSE connections comfortably (FD-limited).
- Use `worker_rlimit_nofile` and `LimitNOFILE` accordingly in compose.
- Frontend reconnects with exponential backoff on disconnect.

## Multi-tab (admin UI)

Browsers do **not** open one SSE stream per tab. `admin-ui/src/lib/realtimeHub.ts`:

1. **Leader election** — one tab per origin holds the sole `EventSource` (localStorage heartbeat).
2. **BroadcastChannel** — the leader fan-outs events to other tabs; followers never connect.
3. **Topic union** — the leader multiplexes every tab’s topics on one
   `GET /api/realtime/subscribe?topic=…&topic=…` URL.

A user with 150 tabs therefore keeps **one** idle SSE connection (plus Redis
fan-out on the server), not 150. List views use `useRealtimeList`; pages that
need many topics (audit log) use `useRealtimeTopics`.

If `BroadcastChannel` is unavailable, the hub falls back to one connection per
tab (legacy behaviour).

## RBAC enforcement

- On subscribe, the topic is validated against `BaseRepository._can_read()`.
- If the user loses access while subscribed (e.g. role removed), the next
  message triggers re-validation; on failure the connection is closed.
- Cross-tenant topics return `403`.
