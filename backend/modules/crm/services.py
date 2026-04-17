"""CRM business logic + Temporal workflow triggers."""
from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext

logger = logging.getLogger(__name__)


async def move_opportunity_to_stage(
    session: AsyncSession,
    ctx: RequestContext,
    opportunity_id: uuid.UUID,
    stage_id: uuid.UUID,
) -> None:
    """Move an opportunity to a new stage and trigger Temporal workflow."""
    from modules.crm.repositories import OpportunityRepository, StageRepository

    opp_repo = OpportunityRepository(session, ctx)
    stage_repo = StageRepository(session, ctx)

    opportunity = await opp_repo.get(opportunity_id)
    stage = await stage_repo.get(stage_id)

    # Update stage
    await opp_repo.update(opportunity_id, {
        "stage_id": stage_id,
        "probability": stage.probability,
    })

    # Trigger Temporal workflow for won/lost transitions
    if stage.is_won or stage.is_lost:
        await _trigger_opportunity_workflow(opportunity_id, "won" if stage.is_won else "lost")

    logger.info("Opportunity %s moved to stage %s", opportunity_id, stage.name)


async def _trigger_opportunity_workflow(opportunity_id: uuid.UUID, event: str) -> None:
    """Send a signal to the Temporal opportunity workflow."""
    try:
        from orbiteus_core.temporal import get_temporal_client

        client = await get_temporal_client()
        handle = client.get_workflow_handle(f"opportunity-{opportunity_id}")
        await handle.signal("stage_changed", event)
        logger.info("Temporal signal sent: opportunity-%s → %s", opportunity_id, event)
    except Exception as e:
        logger.warning("Could not signal Temporal workflow: %s", e)
