"""User ↔ role junction table (ADR-0022)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import login_user, unique_email


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    token = await login_user(client, "admin@example.com", "admin1234")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_ui_config_hides_registry_model_field(client: AsyncClient):
    resp = await client.get("/api/base/ui-config")
    base = next(m for m in resp.json()["modules"] if m["name"] == "base")
    names = {m["name"] for m in base["models"]}
    assert "base.registry-model-field" not in names


@pytest.mark.asyncio
async def test_ui_config_includes_hidden_technical_models(client: AsyncClient):
    resp = await client.get("/api/base/ui-config")
    base = next(m for m in resp.json()["modules"] if m["name"] == "base")
    by_name = {m["name"]: m for m in base["models"]}
    for technical in (
        "base.registry-model",
        "base.record-rule",
        "base.config-param",
        "base.model-access",
    ):
        assert technical in by_name, technical
        assert by_name[technical].get("ui_hidden") is True
        assert len(by_name[technical]["fields"]) >= 1
        assert by_name[technical]["views"]["list"] is not None


@pytest.mark.asyncio
async def test_ui_config_no_crm_module(client: AsyncClient):
    resp = await client.get("/api/base/ui-config")
    names = {m["name"] for m in resp.json()["modules"]}
    assert "crm" not in names


@pytest.mark.asyncio
async def test_user_roles_junction_synced_on_create(client: AsyncClient):
    email = unique_email("junction")
    headers = await _admin_headers(client)
    create = await client.post(
        "/api/base/user",
        headers=headers,
        json={
            "email": email,
            "name": "Junction User",
            "password": "Secret1234!",
            "role_ids": ["base.group_user"],
        },
    )
    assert create.status_code == 201, create.text
    user_id = create.json()["id"]
    assert create.json()["role_ids"] == ["base.group_user"]

    detail = await client.get(f"/api/base/user/{user_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["role_ids"] == ["base.group_user"]


@pytest.mark.asyncio
async def test_auth_me_includes_rbac_version(client: AsyncClient):
    token = await login_user(client, "admin@example.com", "admin1234")
    resp = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "rbac_version" in body
    assert isinstance(body["rbac_version"], int)
    assert "roles" in body
