"""Unit tests for RBAC role helpers."""
from __future__ import annotations

import pytest

from orbiteus_core.exceptions import ValidationError
from orbiteus_core.rbac_roles import normalize_role_codes


@pytest.mark.asyncio
async def test_normalize_role_codes_empty_allowed(client):
    from orbiteus_core.db import AsyncSessionFactory

    async with AsyncSessionFactory() as session:
        assert await normalize_role_codes(session, [], allow_empty=True) == []


@pytest.mark.asyncio
async def test_normalize_role_codes_unknown_raises(client):
    from orbiteus_core.db import AsyncSessionFactory

    async with AsyncSessionFactory() as session:
        with pytest.raises(ValidationError):
            await normalize_role_codes(session, ["nope.group_x"], allow_empty=False)
