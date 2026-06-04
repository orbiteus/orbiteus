"""Bridge between EventBus (in-process) and Outbox (durable).

When `BaseRepository` publishes `record.{created,updated,deleted}` on the
EventBus, this subscriber inspects active `Webhook` rows for the tenant
and enqueues an `Outbox` entry per matching subscriber. Celery workers
(PR 5) drain the table and deliver the webhook with HMAC signing.

Idempotency: every outbox row carries the `request_id` of the originating
event, so retries never duplicate from the dispatcher side.

Subscribe once at app startup:

    from orbiteus_core.outbox_dispatcher import register_dispatchers
    register_dispatchers()
"""
from __future__ import annotations

import logging
from typing import Any

from orbiteus_core.events import event_bus

logger = logging.getLogger(__name__)


_REGISTERED = False


def register_dispatchers() -> None:
    """Idempotently subscribe outbox dispatchers to the EventBus."""
    global _REGISTERED
    if _REGISTERED:
        return
    for name in ("record.created", "record.updated", "record.deleted"):
        event_bus.subscribe(name, _make_handler(name))
    _REGISTERED = True
    logger.info("outbox_dispatcher.registered")


def _make_handler(event_name: str):
    """Return a subscriber that injects the event name into payload."""

    async def _handler(payload: dict[str, Any]) -> None:
        tagged = dict(payload)
        tagged["__event_name__"] = event_name
        await _on_record_event(tagged)

    _handler.__name__ = f"outbox_dispatch_{event_name.replace('.', '_')}"
    return _handler


async def _on_record_event(payload: dict[str, Any]) -> None:
    """Fan out a CRUD event to all active webhooks for the tenant.

    Best-effort: if there is no active session in the request scope or no
    webhooks match, this is a no-op. Errors are logged and swallowed; the
    EventBus already isolates handler errors from the request flow.
    """
    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        return

    # Lazy imports — avoid cycles at module load time.
    from sqlalchemy import select

    from modules.base.model.mapping import base_webhooks_table
    from orbiteus_core.db import AsyncSessionFactory
    from orbiteus_core.outbox import enqueue

    event_name = _infer_event_name(payload)

    async with AsyncSessionFactory() as session:
        try:
            stmt = select(
                base_webhooks_table.c.id,
                base_webhooks_table.c.event_mask,
                base_webhooks_table.c.model_filter,
                base_webhooks_table.c.field_filter,
            ).where(
                base_webhooks_table.c.tenant_id == tenant_id,
                base_webhooks_table.c.is_active == True,  # noqa: E712
                base_webhooks_table.c.active == True,     # noqa: E712
            )
            rows = (await session.execute(stmt)).all()
            payload_model = payload.get("model")
            payload_diff = payload.get("diff") or {}
            for webhook_id, mask, model_filter, field_filter in rows:
                # 1) Event mask — empty list means "all events".
                if mask and event_name not in mask:
                    continue
                # 2) Model filter — NULL/empty means "all models".
                if model_filter and model_filter != payload_model:
                    continue
                # 3) Field filter — only meaningful for `record.updated`.
                #    Empty list means "any field change fires".
                if (
                    event_name == "record.updated"
                    and field_filter
                    and not (set(field_filter) & set(payload_diff.keys()))
                ):
                    continue
                await enqueue(
                    session,
                    tenant_id=tenant_id,
                    event=event_name,
                    payload=payload,
                    target_kind="webhook",
                    target_ref=str(webhook_id),
                )
            await session.commit()
        except Exception:  # noqa: BLE001
            await session.rollback()
            logger.exception("outbox_dispatcher.dispatch_failed", extra={"event": event_name})


def _infer_event_name(payload: dict[str, Any]) -> str:
    """Map a BaseRepository payload to its source event name.

    The wrappers in `_make_handler` inject `__event_name__` so the outbox
    row records which logical event the row came from.
    """
    return payload.get("__event_name__", "record.changed")
