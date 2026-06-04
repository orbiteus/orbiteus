"""Default RBAC roles — upserted at startup and in migrations."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext

logger = logging.getLogger(__name__)

DEFAULT_ROLES: list[dict[str, Any]] = [
    {
        "code": "base.group_system",
        "name": "System administrator",
        "description": "Full access to engine configuration and security.",
        "is_system": True,
    },
    {
        "code": "base.group_user",
        "name": "Internal user",
        "description": "Default employee role with read-only access to shared master data.",
        "is_system": True,
    },
]


async def seed_default_roles(session: AsyncSession, _ctx: RequestContext | None = None) -> int:
    """Insert built-in roles when missing. Returns count of newly created rows."""
    from modules.base.model.domain import Role
    from modules.base.model.mapping import base_roles_table

    created = 0

    for spec in DEFAULT_ROLES:
        stmt = select(Role).where(base_roles_table.c.code == spec["code"])
        existing = (await session.execute(stmt)).scalars().first()
        if existing is not None:
            continue

        row = Role(
            id=uuid.uuid4(),
            name=spec["name"],
            code=spec["code"],
            description=spec.get("description"),
            is_system=bool(spec.get("is_system", False)),
            active=True,
        )
        session.add(row)
        created += 1

    if created:
        await session.flush()
        logger.info("Seeded %d default RBAC roles", created)

    return created
