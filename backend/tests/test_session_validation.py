"""Session validation — stale JWT after DB reset must not yield empty lists."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from orbiteus_core.config import settings
from orbiteus_core.security.tokens import create_access_token
from tests.conftest import login_user, register_user, unique_email


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_stale_user_token_returns_401_on_protected_route(client: AsyncClient):
    ghost_id = uuid.uuid4()
    token = create_access_token({
        "sub": str(ghost_id),
        "tenant_id": str(uuid.uuid4()),
        "roles": [],
        "is_superadmin": False,
    })

    r = await client.get("/api/base/user", headers=_h(token))
    assert r.status_code == 401
    assert "Session invalid" in r.json()["detail"]


@pytest.mark.asyncio
async def test_auth_me_returns_401_for_deleted_user_token(client: AsyncClient):
    ghost_id = uuid.uuid4()
    token = create_access_token({
        "sub": str(ghost_id),
        "tenant_id": str(uuid.uuid4()),
        "roles": [],
        "is_superadmin": False,
    })

    r = await client.get("/api/auth/me", headers=_h(token))
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_base_user_list_returns_bootstrap_admin(client: AsyncClient):
    token = await login_user(
        client,
        settings.bootstrap_admin_email,
        settings.bootstrap_admin_password,
    )
    r = await client.get("/api/base/user", headers=_h(token))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert any(row["email"] == settings.bootstrap_admin_email for row in body["items"])
