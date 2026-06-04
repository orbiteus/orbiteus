"""Resolve and sync user ↔ role assignments via `base_user_roles` junction (ADR-0022)."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.exceptions import ValidationError


async def resolve_role_codes(session: AsyncSession, user_id: uuid.UUID) -> list[str]:
    """Return active role codes for a user from the junction table."""
    from modules.base.model.mapping import base_roles_table, user_roles_table

    result = await session.execute(
        select(base_roles_table.c.code)
        .select_from(
            user_roles_table.join(
                base_roles_table,
                user_roles_table.c.role_id == base_roles_table.c.id,
            )
        )
        .where(
            user_roles_table.c.user_id == user_id,
            base_roles_table.c.active == True,  # noqa: E712
        )
        .order_by(base_roles_table.c.code)
    )
    codes = [row.code for row in result]
    if codes:
        return codes

    # Fallback: legacy JSON column until all rows are migrated.
    from modules.base.model.mapping import users_table

    row = (
        await session.execute(
            select(users_table.c.role_ids).where(users_table.c.id == user_id)
        )
    ).first()
    if row is None:
        return []
    legacy = row.role_ids or []
    if isinstance(legacy, list):
        return [str(c) for c in legacy if c]
    return []


async def sync_user_roles(
    session: AsyncSession,
    user_id: uuid.UUID,
    role_codes: list[str],
) -> list[str]:
    """Replace junction rows for a user; sync legacy JSON column; return codes."""
    from orbiteus_core.rbac_roles import normalize_role_codes
    from modules.base.model.mapping import base_roles_table, user_roles_table, users_table

    normalized = await normalize_role_codes(session, role_codes, allow_empty=True)
    if not normalized:
        normalized = ["base.group_user"]

    result = await session.execute(
        select(base_roles_table.c.id, base_roles_table.c.code).where(
            base_roles_table.c.code.in_(normalized),
            base_roles_table.c.active == True,  # noqa: E712
        )
    )
    rows = result.all()
    found_codes = {r.code for r in rows}
    missing = set(normalized) - found_codes
    if missing:
        raise ValidationError(f"Unknown role codes: {', '.join(sorted(missing))}")

    role_ids = [r.id for r in rows]

    await session.execute(
        delete(user_roles_table).where(user_roles_table.c.user_id == user_id)
    )
    for role_id in role_ids:
        await session.execute(
            insert(user_roles_table).values(user_id=user_id, role_id=role_id)
        )

    await session.execute(
        update(users_table)
        .where(users_table.c.id == user_id)
        .values(role_ids=normalized)
    )
    return normalized


async def hydrate_user_role_ids(session: AsyncSession, user: Any) -> None:
    """Set `user.role_ids` on a loaded User domain object from junction."""
    if user is None or not getattr(user, "id", None):
        return
    user.role_ids = await resolve_role_codes(session, user.id)
