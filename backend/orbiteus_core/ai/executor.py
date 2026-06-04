"""Execute `base.agent` definitions under caller RBAC (ADR-0018, ADR-0019)."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.ai.agent_realtime import publish_agent_run_update
from orbiteus_core.ai.budget import has_budget
from orbiteus_core.ai.keys import fetch_credential
from orbiteus_core.ai.loop import AgentLoopResult, DelegationContext, apply_usage_budget, run_agent_loop
from orbiteus_core.ai.providers import ProviderError, get_provider
from orbiteus_core.ai.redaction import redact_payload
from orbiteus_core.ai.tools import build_tools_for_agent
from orbiteus_core.context import RequestContext
from orbiteus_core.exceptions import ValidationError

logger = logging.getLogger(__name__)


async def load_agent(session: AsyncSession, ctx: RequestContext, agent_id: uuid.UUID):
    from modules.base.controller.repositories import AgentRepository

    repo = AgentRepository(session, ctx)
    return await repo.get(agent_id)


async def _notify_run(
    tenant_id: uuid.UUID | None,
    run_id: uuid.UUID | None,
    *,
    status: str,
    output_text: str | None = None,
    tokens_used: int | None = None,
    error_message: str | None = None,
    tool_trace: list | None = None,
) -> None:
    if tenant_id is None or run_id is None:
        return
    payload: dict[str, Any] = {
        "run_id": str(run_id),
        "status": status,
        "output_text": output_text,
        "tokens_used": tokens_used,
        "error_message": error_message,
    }
    if tool_trace is not None:
        payload["tool_trace"] = tool_trace
    await publish_agent_run_update(tenant_id, run_id, payload)


async def execute_agent_run(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    agent_id: uuid.UUID,
    prompt: str,
    run_id: uuid.UUID | None = None,
    depth: int = 0,
    parent_run_id: uuid.UUID | None = None,
    parent_agent: Any | None = None,
) -> dict[str, Any]:
    if ctx.tenant_id is None:
        raise ValidationError("tenant context required")

    agent = await load_agent(session, ctx, agent_id)
    if not agent.active:
        raise ValidationError("Agent is inactive")

    provider_name = (agent.provider or "anthropic").lower()
    cred = await fetch_credential(session, tenant_id=ctx.tenant_id, provider=provider_name)
    if cred is None:
        raise ValidationError(
            f"No active {provider_name} credential for this tenant",
        )

    if not await has_budget(ctx.tenant_id, cred.get("monthly_token_budget")):
        raise ValidationError("Monthly AI token budget exceeded")

    embed_cred = await fetch_credential(session, tenant_id=ctx.tenant_id, provider="openai")
    embed_key = embed_cred["secret"] if embed_cred else None

    tools = build_tools_for_agent(
        ctx,
        module_scope=agent.module_scope or "*",
        allowed_models=list(agent.allowed_models or []),
        allowed_actions=list(agent.allowed_actions or []),
        can_delegate=bool(agent.can_delegate),
    )

    messages = redact_payload([
        {"role": "system", "content": agent.system_prompt or ""},
        {"role": "user", "content": prompt},
    ])

    run_repo = None
    if run_id is not None:
        from modules.base.controller.repositories import AgentRunRepository

        run_repo = AgentRunRepository(session, ctx)
        await run_repo.update(
            run_id,
            {"status": "running", "input_prompt": prompt, "depth": depth},
        )
        await session.commit()
        await _notify_run(ctx.tenant_id, run_id, status="running")

    provider = get_provider(provider_name)
    model = agent.model_default or cred.get("model_default")
    delegation = DelegationContext(
        parent_agent=agent,
        parent_run_id=run_id or parent_run_id,
        depth=depth,
    )

    try:
        loop_result: AgentLoopResult = await run_agent_loop(
            session,
            ctx,
            provider=provider,
            api_key=cred["secret"],
            messages=messages,
            tools=tools,
            model=model,
            embed_api_key=embed_key,
            provider_name=provider_name,
            agent_run_id=str(run_id) if run_id else None,
            delegation=delegation,
        )
    except ProviderError as exc:
        if run_repo and run_id:
            await run_repo.update(
                run_id,
                {"status": "failed", "error_message": str(exc)[:500]},
            )
            await session.commit()
            await _notify_run(
                ctx.tenant_id, run_id, status="failed", error_message=str(exc)[:500],
            )
        raise

    await apply_usage_budget(ctx.tenant_id, loop_result.usage_tokens)

    if run_repo and run_id:
        await run_repo.update(
            run_id,
            {
                "status": "completed",
                "output_text": loop_result.text,
                "tool_trace": loop_result.tool_trace,
                "tokens_used": loop_result.usage_tokens,
            },
        )
        await session.commit()
        await _notify_run(
            ctx.tenant_id,
            run_id,
            status="completed",
            output_text=loop_result.text,
            tokens_used=loop_result.usage_tokens,
            tool_trace=loop_result.tool_trace,
        )

    return {
        "agent_id": str(agent_id),
        "run_id": str(run_id) if run_id else None,
        "text": loop_result.text,
        "tool_trace": loop_result.tool_trace,
        "usage_tokens": loop_result.usage_tokens,
        "turns": loop_result.turns,
    }


async def create_and_execute_run(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    agent_id: uuid.UUID,
    prompt: str,
    parent_run_id: uuid.UUID | None = None,
    depth: int = 0,
) -> dict[str, Any]:
    from modules.base.controller.repositories import AgentRunRepository

    if not prompt.strip():
        raise ValidationError("prompt is required")

    run_repo = AgentRunRepository(session, ctx)
    run = await run_repo.create(
        {
            "agent_id": agent_id,
            "parent_run_id": parent_run_id,
            "depth": depth,
            "triggered_by_user_id": ctx.user_id,
            "input_prompt": prompt.strip(),
            "status": "pending",
        }
    )
    await session.commit()
    await _notify_run(ctx.tenant_id, run.id, status="pending")
    return await execute_agent_run(
        session,
        ctx,
        agent_id=agent_id,
        prompt=prompt.strip(),
        run_id=run.id,
        depth=depth,
        parent_run_id=parent_run_id,
    )


async def run_scheduled_agent(
    session: AsyncSession,
    ctx: RequestContext,
    agent: Any,
) -> dict[str, Any] | None:
    """Execute one agent on its schedule prompt if interval elapsed."""
    interval = agent.schedule_interval_minutes
    if not interval or interval < 1:
        return None
    if not (agent.schedule_prompt or "").strip():
        return None

    now = datetime.now(timezone.utc)
    last = agent.schedule_last_run_at
    if last is not None:
        elapsed_min = (now - last).total_seconds() / 60.0
        if elapsed_min < interval:
            return None

    from modules.base.controller.repositories import AgentRepository

    agent_repo = AgentRepository(session, ctx)
    result = await create_and_execute_run(
        session,
        ctx,
        agent_id=agent.id,
        prompt=agent.schedule_prompt.strip(),
    )
    await agent_repo.update(agent.id, {"schedule_last_run_at": now})
    await session.commit()
    return result
