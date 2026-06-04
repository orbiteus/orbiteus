"""Postgres Outbox for durable side effects.

Side effects that must survive a process crash (webhook delivery, email send,
embeddings refresh) are committed atomically with the business transaction
into `base_outbox`. A Celery worker (PR 5) drains the table with idempotent
retry and exponential backoff.

Public API:

    from orbiteus_core.outbox import enqueue

    await enqueue(
        session,
        tenant_id=ctx.tenant_id,
        event="record.created",
        payload={"model": "crm.lead", "id": "..."},
    )

The function INSERTs a row in `base_outbox` using the same `AsyncSession` so
the business commit and the queue commit are one transaction.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# Status enum used by the table — string columns are fine; enum kept here for
# Python-side discoverability.
class OutboxStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    DEAD = "dead"


def _serialize(payload: dict[str, Any]) -> dict[str, Any]:
    """Make payload JSON-safe (uuid, datetime → str)."""

    def _coerce(value: Any) -> Any:
        if isinstance(value, dict):
            return {k: _coerce(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [_coerce(v) for v in value]
        if isinstance(value, uuid.UUID):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    return _coerce(payload)


async def enqueue(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
    event: str,
    payload: dict[str, Any],
    target_kind: str | None = None,
    target_ref: str | None = None,
    not_before: datetime | None = None,
) -> uuid.UUID:
    """Persist an outbox row inside the current transaction.

    Args:
        session: AsyncSession from the request context (atomic with business writes).
        tenant_id: Tenant scope of the event. Required for tenant-isolated drains.
        event: Logical event name, e.g. "record.created", "webhook.deliver".
        payload: JSON-serializable dict (uuid/datetime are coerced).
        target_kind: Optional dispatcher hint, e.g. "webhook", "email".
        target_ref: Optional dispatcher reference, e.g. webhook subscriber id.
        not_before: Optional UTC timestamp; worker skips rows until this time.

    Returns:
        The new outbox row id.
    """
    # Lazy import to avoid circular imports during module load.
    from modules.base.model.mapping import base_outbox_table

    row_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    # `next_run_at` is a String(50) (Postgres VARCHAR) so the drainer can do
    # cheap text comparisons; coerce to ISO 8601 here.
    next_run_iso = (not_before or now).isoformat()
    stmt = insert(base_outbox_table).values(
        id=row_id,
        create_date=now,
        write_date=now,
        tenant_id=tenant_id,
        status=OutboxStatus.PENDING,
        event=event,
        payload=_serialize(payload),
        target_kind=target_kind,
        target_ref=target_ref,
        retries=0,
        next_run_at=next_run_iso,
        last_error=None,
    )
    await session.execute(stmt)
    logger.debug(
        "outbox.enqueued",
        extra={
            "outbox_id": str(row_id),
            "event": event,
            "tenant_id": str(tenant_id) if tenant_id else None,
            "target_kind": target_kind,
        },
    )
    return row_id
