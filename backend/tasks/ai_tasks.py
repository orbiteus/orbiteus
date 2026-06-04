"""Celery tasks for async AI agent runs (ADR-0018)."""
from __future__ import annotations

import asyncio
import logging
import uuid

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="tasks.ai_tasks.run_agent_run")
def run_agent_run(
    run_id: str,
    tenant_id: str,
    user_id: str,
    roles: list[str] | None = None,
    is_superadmin: bool = False,
) -> dict:
    return asyncio.run(
        _run_agent_run_async(run_id, tenant_id, user_id, roles or [], is_superadmin),
    )


async def _run_agent_run_async(
    run_id: str,
    tenant_id: str,
    user_id: str,
    roles: list[str],
    is_superadmin: bool,
) -> dict:
    from modules.base.controller.repositories import AgentRunRepository
    from orbiteus_core.ai.executor import execute_agent_run
    from orbiteus_core.ai.providers import ProviderError
    from orbiteus_core.context import RequestContext
    from orbiteus_core.db import AsyncSessionFactory

    ctx = RequestContext(
        tenant_id=uuid.UUID(tenant_id),
        user_id=uuid.UUID(user_id) if user_id else None,
        roles=list(roles),
        is_superadmin=is_superadmin,
        actor="ai",
        scope="ai",
    )

    async with AsyncSessionFactory() as session:
        run_repo = AgentRunRepository(session, ctx)
        run = await run_repo.get(uuid.UUID(run_id))
        prompt = run.input_prompt or ""

        try:
            result = await execute_agent_run(
                session,
                ctx,
                agent_id=run.agent_id,
                prompt=prompt,
                run_id=run.id,
                depth=int(run.depth or 0),
                parent_run_id=run.parent_run_id,
            )
        except ProviderError as exc:
            await run_repo.update(
                run.id,
                {"status": "failed", "error_message": str(exc)[:500]},
            )
            await session.commit()
            logger.exception("ai.run_agent_run.provider_failed run_id=%s", run_id)
            return {"status": "failed", "run_id": run_id}
        except Exception as exc:  # noqa: BLE001
            await run_repo.update(
                run.id,
                {"status": "failed", "error_message": str(exc)[:500]},
            )
            await session.commit()
            logger.exception("ai.run_agent_run.failed run_id=%s", run_id)
            return {"status": "failed", "run_id": run_id}

        return {"status": "completed", "run_id": run_id, "usage_tokens": result.get("usage_tokens")}


@shared_task(name="tasks.ai_tasks.poll_scheduled_agents")
def poll_scheduled_agents() -> dict:
    return asyncio.run(_poll_scheduled_agents_async())


async def _poll_scheduled_agents_async() -> dict:
    """Run agents whose schedule_interval_minutes has elapsed."""
    from sqlalchemy import select

    from modules.base.model.domain import Agent
    from modules.base.model.mapping import base_agents_table
    from orbiteus_core.ai.executor import run_scheduled_agent
    from orbiteus_core.context import RequestContext
    from orbiteus_core.db import AsyncSessionFactory

    started = 0
    async with AsyncSessionFactory() as session:
        stmt = select(Agent).where(
            base_agents_table.c.active == True,  # noqa: E712
            base_agents_table.c.schedule_interval_minutes.isnot(None),
        )
        agents = (await session.execute(stmt)).scalars().all()
        for agent in agents:
            if agent.tenant_id is None:
                continue
            ctx = RequestContext(
                tenant_id=agent.tenant_id,
                is_superadmin=True,
                actor="system",
                scope="internal",
            )
            try:
                result = await run_scheduled_agent(session, ctx, agent)
                if result is not None:
                    started += 1
            except Exception:  # noqa: BLE001
                logger.exception(
                    "ai.poll_scheduled_agents.failed agent_id=%s", agent.id,
                )
    return {"started": started}
