"""Enqueue embedding refresh outbox rows on CRUD for `embed_models`."""
from __future__ import annotations

import logging
from typing import Any

from orbiteus_core.ai.config import ai_registry
from orbiteus_core.events import event_bus

logger = logging.getLogger(__name__)

_REGISTERED = False


def register_embedding_dispatcher() -> None:
    """Idempotently subscribe embedding refresh to record CRUD events."""
    global _REGISTERED
    if _REGISTERED:
        return
    for name in ("record.created", "record.updated", "record.deleted"):
        event_bus.subscribe(name, _make_handler(name))
    _REGISTERED = True
    logger.info("embedding_dispatcher.registered")


def _make_handler(event_name: str):
    async def _handler(payload: dict[str, Any]) -> None:
        tagged = dict(payload)
        tagged["__event_name__"] = event_name
        await _on_record_event(tagged)

    _handler.__name__ = f"embedding_dispatch_{event_name.replace('.', '_')}"
    return _handler


async def _on_record_event(payload: dict[str, Any]) -> None:
    tenant_id = payload.get("tenant_id")
    model = payload.get("model")
    record_id = payload.get("id")
    if not tenant_id or not model or not record_id:
        return
    if model not in ai_registry.embed_models():
        return

    event_name = payload.get("__event_name__", "record.changed")

    from orbiteus_core.db import AsyncSessionFactory
    from orbiteus_core.outbox import enqueue

    async with AsyncSessionFactory() as session:
        try:
            await enqueue(
                session,
                tenant_id=tenant_id,
                event=event_name,
                payload=payload,
                target_kind="embedding",
                target_ref=str(record_id),
            )
            await session.commit()
        except Exception:  # noqa: BLE001
            await session.rollback()
            logger.exception(
                "embedding_dispatcher.enqueue_failed",
                extra={"event": event_name, "model": model},
            )
