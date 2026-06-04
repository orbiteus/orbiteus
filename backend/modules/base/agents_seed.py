"""Default AI agents — upserted per tenant at startup."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Showcase agents ship with domain modules. Engine-only installs start empty.
DEFAULT_AGENTS: list[dict[str, Any]] = []


async def seed_default_agents(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> int:
    """Insert showcase agents when missing. Returns new row count."""
    from modules.base.model.domain import Agent
    from modules.base.model.mapping import base_agents_table

    created = 0
    for spec in DEFAULT_AGENTS:
        stmt = select(Agent).where(
            base_agents_table.c.tenant_id == tenant_id,
            base_agents_table.c.slug == spec["slug"],
        )
        existing = (await session.execute(stmt)).scalars().first()
        if existing is not None:
            continue

        row = Agent(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            slug=spec["slug"],
            name=spec["name"],
            module_scope=spec["module_scope"],
            system_prompt=spec["system_prompt"],
            allowed_models=list(spec.get("allowed_models") or []),
            allowed_actions=list(spec.get("allowed_actions") or []),
            can_delegate=bool(spec.get("can_delegate", False)),
            allowed_delegate_slugs=list(spec.get("allowed_delegate_slugs") or []),
            schedule_interval_minutes=spec.get("schedule_interval_minutes"),
            schedule_prompt=str(spec.get("schedule_prompt") or ""),
            is_system=bool(spec.get("is_system", False)),
            active=True,
        )
        session.add(row)
        created += 1

    if created:
        await session.flush()
        logger.info("Seeded %d default AI agents for tenant %s", created, tenant_id)

    return created
