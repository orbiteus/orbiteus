"""Shared helpers for RBAC role code validation and cleanup."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.exceptions import ValidationError


async def fetch_known_role_codes(session: AsyncSession) -> set[str]:
    from modules.base.model.mapping import base_roles_table as roles

    result = await session.execute(select(roles.c.code))
    return {row.code for row in result}


async def normalize_role_codes(
    session: AsyncSession,
    codes: list[Any] | None,
    *,
    allow_empty: bool = True,
) -> list[str]:
    """Return trimmed role codes that exist in ``base_roles``."""
    cleaned = [str(c).strip() for c in (codes or []) if str(c).strip()]
    if not cleaned:
        if allow_empty:
            return []
        raise ValidationError("At least one role code is required")

    known = await fetch_known_role_codes(session)
    unknown = set(cleaned) - known
    if unknown:
        raise ValidationError(
            f"Unknown role codes: {', '.join(sorted(unknown))}",
        )
    return cleaned


async def purge_role_references(session: AsyncSession, role_code: str) -> dict[str, int]:
    """Remove ``role_code`` from users, model-access rows, and record rules."""
    from sqlalchemy import delete, update

    from modules.base.model.mapping import (
        base_model_access_table as access,
        base_rules_table as rules,
        users_table as users,
    )

    stats = {"users": 0, "model_access": 0, "record_rules": 0}

    user_rows = (await session.execute(select(users.c.id, users.c.role_ids))).all()
    for row in user_rows:
        current = list(row.role_ids or [])
        if role_code not in current:
            continue
        next_roles = [c for c in current if c != role_code]
        await session.execute(
            update(users)
            .where(users.c.id == row.id)
            .values(role_ids=next_roles)
        )
        stats["users"] += 1

    ma = await session.execute(
        delete(access).where(access.c.role_name == role_code)
    )
    stats["model_access"] = int(ma.rowcount or 0)

    rule_rows = (
        await session.execute(select(rules.c.id, rules.c.roles))
    ).all()
    for row in rule_rows:
        current = list(row.roles or [])
        if role_code not in current:
            continue
        next_roles = [c for c in current if c != role_code]
        await session.execute(
            update(rules).where(rules.c.id == row.id).values(roles=next_roles)
        )
        stats["record_rules"] += 1

    return stats
