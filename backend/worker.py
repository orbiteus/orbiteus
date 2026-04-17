"""Orbiteus Temporal Worker – runs all background workflows and activities."""
from __future__ import annotations

import asyncio
import logging

from temporalio.worker import Worker

from orbiteus_core.config import settings
from orbiteus_core.temporal import get_temporal_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Import all workflows and activities here
# ---------------------------------------------------------------------------

# Workflows are defined in module services and registered below.
# Example structure – expand as modules are built out.

WORKFLOWS: list = []
ACTIVITIES: list = []

# CRM workflows (placeholder)
try:
    from modules.crm.workflows import OpportunityWorkflow
    WORKFLOWS.append(OpportunityWorkflow)
except ImportError:
    logger.debug("CRM workflows not yet defined – skipping.")

TASK_QUEUE = "orbiteus-main"


async def main() -> None:
    client = await get_temporal_client()

    if not WORKFLOWS and not ACTIVITIES:
        logger.warning(
            "No workflows or activities registered. Worker running in idle mode."
        )

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=WORKFLOWS,
        activities=ACTIVITIES,
    )

    logger.info("Temporal worker started on task queue: %s", TASK_QUEUE)
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
