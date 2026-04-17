"""Temporal.io client helper."""
from __future__ import annotations

import logging

from temporalio.client import Client

from orbiteus_core.config import settings

logger = logging.getLogger(__name__)

_client: Client | None = None


async def get_temporal_client() -> Client:
    """Return the shared Temporal client, creating it on first call."""
    global _client
    if _client is None:
        _client = await Client.connect(settings.temporal_host, namespace=settings.temporal_namespace)
        logger.info("Connected to Temporal at %s", settings.temporal_host)
    return _client
