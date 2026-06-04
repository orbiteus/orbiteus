# 12 — Events and Queues

Three mechanisms with clear, non-overlapping roles.

## EventBus (in-process)

- Synchronous publish/subscribe within one request lifecycle.
- Used for hooks that must run with the same DB transaction:
  - audit log entries
  - cache invalidation
  - embeddings refresh signals
  - in-memory derived state updates
- Implemented as a simple registry of async callables keyed by event name.

## Postgres Outbox

- Durable side-effect queue stored in the `base_outbox` table.
- Atomic with the business transaction (`INSERT INTO base_outbox ...` in the
  same `BEGIN/COMMIT`).
- Drained by Celery workers with idempotent retry.

```sql
CREATE TABLE base_outbox (
    id          UUID PRIMARY KEY,
    tenant_id   UUID NOT NULL,
    event       TEXT NOT NULL,
    payload     JSONB NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',  -- pending|processing|done|dead
    retries     INT NOT NULL DEFAULT 0,
    next_run_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON base_outbox (status, next_run_at) WHERE status IN ('pending','processing');
```

## Celery 5

- Broker: Redis. Result backend: Redis.
- Workers run as a separate `worker` service in compose.
- Beat scheduler reads `base_cron` and publishes periodic tasks.
- Idempotent task design: every task accepts `outbox_id` and updates the row.

```python
@app.task(bind=True, max_retries=10, default_retry_delay=10, autoretry_for=(Exception,),
          retry_backoff=True, retry_backoff_max=3600, retry_jitter=True)
def deliver_webhook(self, outbox_id: str) -> None:
    ...
```

## Decision matrix

| Need | Use |
|---|---|
| Hook in same transaction (audit, cache invalidation) | EventBus |
| Atomic side effect after commit (webhook, email) | Outbox + Celery |
| Long-running orchestration with state | Outbox + Celery (custom state machine) |
| Periodic schedule | Celery Beat (driven by `base_cron`) |
| Multi-step saga with compensation | Outbox + saga implementation in service layer |

## Why no Temporal in MVP

Temporal is excellent but adds:
- own server + own database
- additional SDK with its own quirks
- operational learning curve

Senior fluency is uneven; AI assistants vary in correctness across versions.
We achieve the same outcomes with Outbox + Celery for the MVP scope. Temporal
returns as an opt-in profile if real sagas appear (multi-step billing,
multi-week onboarding flows).

ADR `0015` records the choice.

## Event taxonomy

| Event | Source | Payload |
|---|---|---|
| `record.created` | BaseRepository.create | model, id, tenant_id, actor, fields |
| `record.updated` | BaseRepository.update | model, id, tenant_id, actor, diff |
| `record.deleted` | BaseRepository.delete | model, id, tenant_id, actor |
| `workflow.transition` | workflow engine | model, id, from_state, to_state |
| `auth.login` | auth router | user_id, ip, user_agent |
| `ai.tool.invoked` | AI executor | user_id, tool_name, args, result_status |
| `mail.send_requested` | mail engine | template_id, recipient, payload |

All events carry: `tenant_id`, `request_id`, `ts`.

## Idempotency keys

- Tasks that hit external systems must be idempotent.
- Use `(outbox_id, task_name)` as the dedup key in Redis with TTL = 24h.
- Webhook deliveries include the `outbox_id` in the signature header so the
  receiver can also dedup.

## Backpressure

- Outbox drainer respects `max_in_flight = 100` per worker.
- Failed events go to `status='dead'` after exceeding `retries=10`.
- Dead-letter rows raise an Action visible to admins.
