"""Connectivity tests — RBAC validation, role purge, UI field wiring."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import login_user, unique_email


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    token = await login_user(client, "admin@example.com", "admin1234")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_ui_config_user_has_company_many2many(client: AsyncClient):
    resp = await client.get("/api/base/ui-config")
    assert resp.status_code == 200
    base = next(m for m in resp.json()["modules"] if m["name"] == "base")
    user = next(m for m in base["models"] if m["name"] == "base.user")
    company_field = next(f for f in user["fields"] if f["name"] == "company_ids")
    assert company_field["type"] == "many2many"
    assert company_field["relation"] == "base.company"
    field_names = {f["name"] for f in user["fields"]}
    assert "partner_id" not in field_names


@pytest.mark.asyncio
async def test_model_access_rejects_unknown_role(client: AsyncClient):
    headers = await _admin_headers(client)
    resp = await client.post(
        "/api/base/model-access",
        headers=headers,
        json={
            "model_name": "base.company",
            "role_name": "does.not.exist",
            "perm_read": True,
        },
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_record_rule_rejects_unknown_role(client: AsyncClient):
    headers = await _admin_headers(client)
    resp = await client.post(
        "/api/base/record-rule",
        headers=headers,
        json={
            "name": "Bad rule",
            "model_name": "base.company",
            "roles": ["does.not.exist"],
        },
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_custom_role_delete_purges_references(client: AsyncClient):
    headers = await _admin_headers(client)
    code = f"base.group_test_{uuid.uuid4().hex[:8]}"

    create_role = await client.post(
        "/api/base/role",
        headers=headers,
        json={"name": "Test purge role", "code": code},
    )
    assert create_role.status_code == 201, create_role.text

    email = unique_email("rolepurge")
    user = await client.post(
        "/api/base/user",
        headers=headers,
        json={
            "email": email,
            "name": "Role Purge User",
            "password": "Secret1234!",
            "role_ids": [code, "base.group_user"],
        },
    )
    assert user.status_code == 201, user.text
    user_id = user.json()["id"]

    access = await client.post(
        "/api/base/model-access",
        headers=headers,
        json={
            "model_name": "base.company",
            "role_name": code,
            "perm_read": True,
        },
    )
    assert access.status_code == 201, access.text
    access_id = access.json()["id"]

    delete = await client.delete(f"/api/base/role/{create_role.json()['id']}", headers=headers)
    assert delete.status_code == 204, delete.text

    refreshed = await client.get(f"/api/base/user/{user_id}", headers=headers)
    assert refreshed.status_code == 200
    assert code not in refreshed.json()["role_ids"]

    gone = await client.get(f"/api/base/model-access/{access_id}", headers=headers)
    assert gone.status_code == 404
