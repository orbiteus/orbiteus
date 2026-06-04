"""Remove attachment rows when the linked business record is unlinked."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from orbiteus_core.events import event_bus

logger = logging.getLogger(__name__)

_REGISTERED = False


def register_attachment_dispatcher() -> None:
    """Subscribe once: cascade attachment cleanup on ``record.deleted``."""
    global _REGISTERED
    if _REGISTERED:
        return
    event_bus.subscribe("record.deleted", _on_record_deleted)
    _REGISTERED = True
    logger.info("attachment_dispatcher.registered")


async def _on_record_deleted(payload: dict[str, Any]) -> None:
    model = payload.get("model")
    record_id = payload.get("id")
    tenant_id = payload.get("tenant_id")
    if not model or not record_id:
        return
    try:
        rid = uuid.UUID(str(record_id))
    except ValueError:
        return

    from orbiteus_core.db import AsyncSessionFactory
    from modules.base.controller.attachment_service import AttachmentService

    tid = uuid.UUID(str(tenant_id)) if tenant_id else None
    async with AsyncSessionFactory() as session:
        try:
            removed = await AttachmentService(session).delete_for_linked_record(
                tenant_id=tid,
                res_model=str(model),
                res_id=rid,
            )
            await session.commit()
            if removed:
                logger.info(
                    "attachment_dispatcher.removed",
                    extra={"model": model, "record_id": str(rid), "count": removed},
                )
        except Exception:  # noqa: BLE001
            await session.rollback()
            logger.exception(
                "attachment_dispatcher.failed",
                extra={"model": model, "record_id": str(rid)},
            )
