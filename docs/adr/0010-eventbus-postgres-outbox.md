# ADR-0010: EventBus + Postgres Outbox for side effects

- **Status:** Accepted
- **Date:** 2026-05-03
- **Context tags:** backend, reliability

## Context

We need three classes of work after a business operation:

1. Synchronous hooks within the same transaction (audit, cache invalidation).
2. Atomic asynchronous side effects after commit (webhooks, emails, embeddings).
3. Periodic schedules (cleanup, reports).

Mixing these into a single mechanism breeds bugs.

## Decision

- **EventBus** (in-process, async): synchronous hooks during a request.
- **Postgres Outbox** (`base_outbox` table): durable side-effect intents committed
  atomically with the business transaction; drained by Celery workers with
  idempotent retry.
- **Celery Beat**: schedules driven by `base_cron`.

## Consequences

- Audit and cache invalidation happen inside the transaction; consistent.
- Webhooks and emails survive crashes via Outbox, with bounded retry and a
  dead-letter status.
- Operationally simple — one new table, one Celery worker class.
- Easier to reason about than mixing in Temporal or queue brokers without
  durable backing.

## Alternatives considered

- Direct synchronous webhook delivery from request handlers — fragile, slow.
- Pure Celery task queue (no Outbox) — loses atomicity with business commit.
- Temporal — too heavy for MVP (see ADR-0015).

## References

- `docs/12-events-and-queues.md`
- `docs/adr/0013-celery-instead-of-arq.md`
- `docs/adr/0015-no-temporal-in-mvp.md`
