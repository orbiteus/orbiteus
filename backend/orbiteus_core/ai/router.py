"""AI actions API — Command Palette backend."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from orbiteus_core.context import RequestContext
from orbiteus_core.security.middleware import require_auth

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/actions")
async def get_actions(
    q: str = Query("", description="Search query for command palette"),
    limit: int = Query(8, ge=1, le=50),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Resolve Command Palette query to ranked Actions.

    Uses RapidFuzz scoring on label + keywords.
    Filtered by user's RBAC features.
    Max ~1ms, zero LLM API calls in happy path.
    """
    from orbiteus_core.ai.resolver import resolve
    results = resolve(q, ctx, limit=limit)
    return {"results": results, "query": q, "total": len(results)}
