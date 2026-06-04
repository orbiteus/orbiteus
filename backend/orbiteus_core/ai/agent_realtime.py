"""SSE notifications for agent run status changes."""
from __future__ import annotations

import json
import logging
from typing import Any

from orbiteus_core.cache import get_redis
from orbiteus_core.realtime import topic_for_list, topic_for_record

logger = logging.getLogger(__name__)

AGENT_RUN_MODEL = "base.agent-run"


async def publish_agent_run_update(
    tenant_id,
    run_id,
    payload: dict[str, Any],
) -> None:
    """Fan-out run status to record + list SSE topics."""
    msg = json.dumps(
        {
            "event": "agent_run.updated",
            "model": AGENT_RUN_MODEL,
            "record_id": str(run_id),
            "tenant_id": str(tenant_id),
            **payload,
        },
        default=str,
    )
    client = get_redis()
    try:
        await client.publish(topic_for_record(tenant_id, AGENT_RUN_MODEL, run_id), msg)
        await client.publish(topic_for_list(tenant_id, AGENT_RUN_MODEL), msg)
    except Exception:  # noqa: BLE001
        logger.exception("agent_realtime.publish_failed run_id=%s", run_id)
