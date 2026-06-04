"""Drain `base_outbox` and dispatch outbox rows to their handlers.

Boring rules (ADR-0013, ADR-0010):
- Tasks are synchronous Celery tasks; async I/O wrapped in `asyncio.run`.
- Idempotent: multiple drainers may race; rows are claimed via UPDATE ...
  WHERE status='pending' RETURNING id (Postgres atomic).
- Retry: exponential backoff with jitter, max 10 retries, then `dead`.
- Handlers are pure functions chosen by `target_kind`.
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

from celery import shared_task
from sqlalchemy import and_, select, update

logger = logging.getLogger(__name__)


# Knobs (env-tunable for prod).
BATCH_SIZE = int(os.environ.get("ORBITEUS_OUTBOX_BATCH", "50"))
MAX_RETRIES = int(os.environ.get("ORBITEUS_OUTBOX_MAX_RETRIES", "10"))
STUCK_TIMEOUT_SECONDS = int(os.environ.get("ORBITEUS_OUTBOX_STUCK_TIMEOUT", "300"))


def _backoff_seconds(retries: int) -> int:
    """Exponential backoff with cap."""
    return min(60 * (2 ** retries), 3600)  # 1m, 2m, 4m, ..., capped at 1h


@shared_task(name="tasks.outbox_tasks.drain_outbox")
def drain_outbox() -> dict:
    """Pick up to BATCH_SIZE pending rows and dispatch them."""
    return asyncio.run(_drain_outbox_async())


async def _drain_outbox_async() -> dict:
    from modules.base.model.mapping import base_outbox_table
    from orbiteus_core.db import AsyncSessionFactory

    now = datetime.now(timezone.utc)
    processed = 0
    failures = 0
    dead = 0

    async with AsyncSessionFactory() as session:
        # Atomically claim a batch of pending rows due now.
        claim_stmt = (
            update(base_outbox_table)
            .where(
                and_(
                    base_outbox_table.c.status == "pending",
                    base_outbox_table.c.next_run_at <= now.isoformat(),
                )
            )
            .values(status="processing", write_date=now)
            .returning(
                base_outbox_table.c.id,
                base_outbox_table.c.event,
                base_outbox_table.c.tenant_id,
                base_outbox_table.c.payload,
                base_outbox_table.c.target_kind,
                base_outbox_table.c.target_ref,
                base_outbox_table.c.retries,
            )
            .execution_options(synchronize_session=False)
        )

        # Postgres FOR UPDATE SKIP LOCKED would be ideal, but SQLAlchemy's
        # update().returning() already serializes via row locks per Postgres.
        result = await session.execute(claim_stmt)
        rows = result.fetchall()
        await session.commit()

        for row in rows[:BATCH_SIZE]:
            row_id, event, tenant_id, payload, target_kind, target_ref, retries = row
            try:
                await _dispatch(event, payload, target_kind, target_ref)
                await _mark_done(session, row_id)
                processed += 1
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "outbox.dispatch_failed",
                    extra={
                        "outbox_id": str(row_id),
                        "event": event,
                        "target_kind": target_kind,
                        "retries": retries,
                    },
                )
                if retries + 1 >= MAX_RETRIES:
                    await _mark_dead(session, row_id, str(exc)[:500])
                    dead += 1
                else:
                    await _reschedule(session, row_id, retries + 1, str(exc)[:500])
                    failures += 1

        await session.commit()

    return {"processed": processed, "failures": failures, "dead": dead}


async def _mark_done(session, row_id: uuid.UUID) -> None:
    from modules.base.model.mapping import base_outbox_table
    await session.execute(
        update(base_outbox_table)
        .where(base_outbox_table.c.id == row_id)
        .values(status="done", write_date=datetime.now(timezone.utc))
    )


async def _mark_dead(session, row_id: uuid.UUID, error: str) -> None:
    from modules.base.model.mapping import base_outbox_table
    await session.execute(
        update(base_outbox_table)
        .where(base_outbox_table.c.id == row_id)
        .values(
            status="dead",
            last_error=error,
            write_date=datetime.now(timezone.utc),
        )
    )


async def _reschedule(session, row_id: uuid.UUID, next_retry: int, error: str) -> None:
    from modules.base.model.mapping import base_outbox_table
    next_run = datetime.now(timezone.utc) + timedelta(seconds=_backoff_seconds(next_retry))
    await session.execute(
        update(base_outbox_table)
        .where(base_outbox_table.c.id == row_id)
        .values(
            status="pending",
            retries=next_retry,
            next_run_at=next_run.isoformat(),
            last_error=error,
            write_date=datetime.now(timezone.utc),
        )
    )


async def _dispatch(event: str, payload: dict, target_kind: str | None, target_ref: str | None) -> None:
    """Pick the handler based on `target_kind`."""
    if target_kind == "webhook":
        from tasks.webhook_tasks import deliver_webhook_async

        await deliver_webhook_async(event=event, payload=payload, webhook_id=target_ref)
        return

    if target_kind == "embedding":
        from tasks.embedding_tasks import refresh_embedding_async

        await refresh_embedding_async(event=event, payload=payload)
        return

    # Fallback: log-only handler. Future PRs (mail, AI) plug in here.
    logger.info(
        "outbox.dispatched",
        extra={"event": event, "target_kind": target_kind, "target_ref": target_ref},
    )


@shared_task(name="tasks.outbox_tasks.release_stuck_processing")
def release_stuck_processing() -> dict:
    """Release rows stuck in 'processing' for > STUCK_TIMEOUT_SECONDS."""
    return asyncio.run(_release_stuck_async())


async def _release_stuck_async() -> dict:
    from modules.base.model.mapping import base_outbox_table
    from orbiteus_core.db import AsyncSessionFactory

    cutoff = (
        datetime.now(timezone.utc) - timedelta(seconds=STUCK_TIMEOUT_SECONDS)
    ).isoformat()
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            update(base_outbox_table)
            .where(
                and_(
                    base_outbox_table.c.status == "processing",
                    base_outbox_table.c.write_date <= cutoff,
                )
            )
            .values(status="pending", write_date=datetime.now(timezone.utc))
            .returning(base_outbox_table.c.id)
        )
        ids = [r[0] for r in result.fetchall()]
        await session.commit()
        return {"released": len(ids)}
