"""CRM custom endpoints – kanban view, stage move, pipeline stats."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext
from orbiteus_core.db import get_session
from orbiteus_core.security.middleware import require_auth

router = APIRouter(tags=["crm"])


@router.get("/pipeline/{pipeline_id}/kanban")
async def pipeline_kanban(
    pipeline_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Return pipeline stages with grouped opportunities for kanban board."""
    from modules.crm.controller.repositories import OpportunityRepository, StageRepository

    stage_repo = StageRepository(session, ctx)
    opp_repo = OpportunityRepository(session, ctx)

    stages, _ = await stage_repo.search(
        domain=[("pipeline_id", "=", pipeline_id)],
        limit=100,
    )

    all_opps, _ = await opp_repo.search(domain=[("pipeline_id", "=", pipeline_id)], limit=5000)
    by_stage: dict[str, list] = {}
    for opp in all_opps:
        if opp.stage_id is None:
            continue
        by_stage.setdefault(str(opp.stage_id), []).append(opp)

    columns = []
    total_revenue = 0.0
    for stage in sorted(stages, key=lambda s: s.sequence):
        opps = by_stage.get(str(stage.id), [])
        revenue = sum(o.expected_revenue for o in opps)
        total_revenue += revenue
        columns.append({
            "stage_id": str(stage.id),
            "stage_name": stage.name,
            "sequence": stage.sequence,
            "probability": stage.probability,
            "is_won": stage.is_won,
            "is_lost": stage.is_lost,
            "fold": stage.fold,
            "count": len(opps),
            "expected_revenue": revenue,
            "opportunities": [
                {
                    "id": str(o.id),
                    "name": o.name,
                    "expected_revenue": o.expected_revenue,
                    "probability": o.probability,
                    "customer_id": str(o.customer_id) if o.customer_id else None,
                    "assigned_user_id": str(o.assigned_user_id) if o.assigned_user_id else None,
                }
                for o in opps
            ],
        })

    return {
        "pipeline_id": str(pipeline_id),
        "columns": columns,
        "total_opportunities": sum(c["count"] for c in columns),
        "total_expected_revenue": total_revenue,
    }


@router.post("/opportunity/{opportunity_id}/move")
async def move_opportunity(
    opportunity_id: uuid.UUID,
    stage_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Move opportunity to a different stage."""
    from modules.crm.controller.services import move_opportunity_to_stage

    await move_opportunity_to_stage(session, ctx, opportunity_id, stage_id)
    return {"message": "Opportunity moved", "opportunity_id": str(opportunity_id), "stage_id": str(stage_id)}


@router.get("/stats")
async def crm_stats(
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Dashboard statistics for CRM."""
    from modules.crm.controller.repositories import CustomerRepository, OpportunityRepository

    customer_repo = CustomerRepository(session, ctx)
    opp_repo = OpportunityRepository(session, ctx)

    _, total_customers = await customer_repo.search(limit=1)
    all_opps, total_opps = await opp_repo.search(limit=1000)

    won_opps = [o for o in all_opps if o.probability == 100.0]
    total_won_revenue = sum(o.expected_revenue for o in won_opps)
    pipeline_value = sum(o.expected_revenue for o in all_opps)

    return {
        "total_customers": total_customers,
        "total_opportunities": total_opps,
        "won_opportunities": len(won_opps),
        "pipeline_value": pipeline_value,
        "won_revenue": total_won_revenue,
    }
