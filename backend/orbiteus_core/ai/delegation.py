"""Agent-to-agent delegation (ADR-0019)."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext
from orbiteus_core.exceptions import ValidationError

logger = logging.getLogger(__name__)

MAX_DELEGATION_DEPTH = 3
DELEGATE_TOOL_NAME = "delegate_agent"


def delegate_tool_schema() -> dict[str, Any]:
    return {
        "name": DELEGATE_TOOL_NAME,
        "description": (
            "Delegate a sub-task to another registered agent. The child agent "
            "runs synchronously under the same RBAC scope and returns its output."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "agent_slug": {
                    "type": "string",
                    "description": "Slug of the target agent (e.g. crm-analyst)",
                },
                "prompt": {
                    "type": "string",
                    "description": "Task prompt for the delegated agent",
                },
            },
            "required": ["agent_slug", "prompt"],
        },
    }


async def resolve_delegate_target(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    parent_agent,
    agent_slug: str,
) -> Any:
    from modules.base.model.domain import Agent
    from modules.base.model.mapping import base_agents_table

    slug = agent_slug.strip().lower()
    if not slug:
        raise ValidationError("agent_slug is required")

    allowed = list(parent_agent.allowed_delegate_slugs or [])
    if allowed and slug not in allowed and "*" not in allowed:
        raise ValidationError(f"Agent {slug!r} is not in allowed_delegate_slugs")

    stmt = select(Agent).where(
        base_agents_table.c.tenant_id == ctx.tenant_id,
        base_agents_table.c.slug == slug,
        base_agents_table.c.active == True,  # noqa: E712
    )
    target = (await session.execute(stmt)).scalars().first()
    if target is None:
        raise ValidationError(f"No active agent with slug {slug!r}")
    if target.id == parent_agent.id:
        raise ValidationError("An agent cannot delegate to itself")
    return target


async def execute_delegate_agent(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    parent_agent,
    parent_run_id: uuid.UUID | None,
    current_depth: int,
    arguments: dict[str, Any] | None,
) -> dict[str, Any]:
    """Spawn and execute a child agent run."""
    if not parent_agent.can_delegate:
        return {
            "status": "error",
            "code": "ai.delegate.disabled",
            "message": "This agent is not allowed to delegate",
        }

    if current_depth >= MAX_DELEGATION_DEPTH:
        return {
            "status": "error",
            "code": "ai.delegate.max_depth",
            "message": f"Maximum delegation depth ({MAX_DELEGATION_DEPTH}) exceeded",
        }

    args = arguments or {}
    slug = str(args.get("agent_slug") or "")
    prompt = str(args.get("prompt") or "").strip()
    if not prompt:
        return {"status": "error", "code": "ai.delegate.no_prompt", "message": "prompt required"}

    try:
        target = await resolve_delegate_target(
            session, ctx, parent_agent=parent_agent, agent_slug=slug,
        )
    except ValidationError as exc:
        return {"status": "error", "code": "ai.delegate.invalid_target", "message": str(exc)}

    from modules.base.controller.repositories import AgentRunRepository
    from orbiteus_core.ai.executor import execute_agent_run

    run_repo = AgentRunRepository(session, ctx)
    child = await run_repo.create(
        {
            "agent_id": target.id,
            "parent_run_id": parent_run_id,
            "depth": current_depth + 1,
            "triggered_by_user_id": ctx.user_id,
            "input_prompt": prompt,
            "status": "pending",
        }
    )
    await session.commit()

    try:
        result = await execute_agent_run(
            session,
            ctx,
            agent_id=target.id,
            prompt=prompt,
            run_id=child.id,
            depth=current_depth + 1,
            parent_run_id=parent_run_id,
            parent_agent=parent_agent,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("ai.delegate.child_failed slug=%s", slug)
        return {
            "status": "error",
            "code": "ai.delegate.child_failed",
            "message": str(exc)[:500],
            "child_run_id": str(child.id),
        }

    return {
        "status": "ok",
        "agent_slug": slug,
        "child_run_id": str(child.id),
        "text": result.get("text"),
        "usage_tokens": result.get("usage_tokens"),
    }
