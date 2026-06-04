"""Celery handler for outbox rows with `target_kind=embedding`."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def refresh_embedding_async(
    *,
    event: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    from orbiteus_core.db import AsyncSessionFactory
    from orbiteus_core.embedding_refresh import refresh_embedding_from_payload

    async with AsyncSessionFactory() as session:
        return await refresh_embedding_from_payload(session, event=event, payload=payload)
