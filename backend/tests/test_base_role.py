"""CRUD tests for base.role — RBAC groups."""
from __future__ import annotations

import uuid

import pytest

from orbiteus_core.config import settings
from tests.conftest import login_user


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _superadmin_token(client) -> str:
    return await login_user(
        client,
        settings.bootstrap_admin_email,
        settings.bootstrap_admin_password,
    )


@pytest.mark.asyncio
async def test_base_role_list_includes_seeded_roles(client):
    token = await _superadmin_token(client)
    r = await client.get("/api/base/role", headers=_h(token))
    assert r.status_code == 200
    codes = {row["code"] for row in r.json()["items"]}
    assert "base.group_system" in codes
    assert "base.group_user" in codes


@pytest.mark.asyncio
async def test_base_role_create_and_delete_custom_role(client):
    token = await _superadmin_token(client)
    code = f"base.group_test_{uuid.uuid4().hex[:8]}"
    create = await client.post(
        "/api/base/role",
        headers=_h(token),
        json={
            "name": "Test role",
            "code": code,
            "description": "Temporary role for integration test",
        },
    )
    assert create.status_code == 201, create.text
    role_id = create.json()["id"]

    delete = await client.delete(f"/api/base/role/{role_id}", headers=_h(token))
    assert delete.status_code == 204


@pytest.mark.asyncio
async def test_base_role_cannot_delete_system_role(client):
    token = await _superadmin_token(client)
    listing = await client.get(
        "/api/base/role",
        headers=_h(token),
        params={"limit": 50},
    )
    system = next(
        row for row in listing.json()["items"] if row["code"] == "base.group_system"
    )

    delete = await client.delete(f"/api/base/role/{system['id']}", headers=_h(token))
    assert delete.status_code == 400
    assert "System roles cannot be deleted" in delete.json()["detail"]


@pytest.mark.asyncio
async def test_base_role_rejects_invalid_code(client):
    token = await _superadmin_token(client)
    r = await client.post(
        "/api/base/role",
        headers=_h(token),
        json={"name": "Bad", "code": "not-a-valid-code"},
    )
    assert r.status_code == 400
    assert "module.group_name" in r.json()["detail"]
