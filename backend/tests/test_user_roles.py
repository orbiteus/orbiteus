"""User create/update — role assignment and password hashing."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import login_user, unique_email


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    token = await login_user(client, "admin@example.com", "admin1234")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_user_rejects_invalid_language(client: AsyncClient):
    headers = await _admin_headers(client)
    resp = await client.post(
        "/api/base/user",
        headers=headers,
        json={
            "email": unique_email("badlang"),
            "name": "Bad Lang",
            "password": "Secret1234!",
            "language": "xx",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["language"] == "en"


@pytest.mark.asyncio
async def test_ui_config_user_has_language_timezone_selects(client: AsyncClient):
    resp = await client.get("/api/base/ui-config")
    assert resp.status_code == 200
    base = next(m for m in resp.json()["modules"] if m["name"] == "base")
    user = next(m for m in base["models"] if m["name"] == "base.user")
    lang = next(f for f in user["fields"] if f["name"] == "language")
    tz = next(f for f in user["fields"] if f["name"] == "timezone")
    assert lang["type"] == "select"
    assert {o["value"] for o in lang["options"]} == {"de", "en", "fr", "pl"}
    assert tz["type"] == "select"
    role_field = next(f for f in user["fields"] if f["name"] == "role_ids")
    assert role_field["type"] == "multi_select"
    assert role_field["optionsResource"] == "base/role"
    assert role_field["optionValue"] == "code"


@pytest.mark.asyncio
async def test_create_user_persists_role_ids(client: AsyncClient):
    email = unique_email("roles")
    headers = await _admin_headers(client)

    create = await client.post(
        "/api/base/user",
        headers=headers,
        json={
            "email": email,
            "name": "Role Test User",
            "password": "Secret1234!",
            "role_ids": ["base.group_user"],
        },
    )
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["role_ids"] == ["base.group_user"]

    listed = await client.get(
        "/api/base/user",
        headers=headers,
        params={"email": email},
    )
    assert listed.status_code == 200
    match = next(i for i in listed.json()["items"] if i["email"] == email)
    assert match["role_ids"] == ["base.group_user"]


@pytest.mark.asyncio
async def test_create_user_defaults_to_base_group_user(client: AsyncClient):
    email = unique_email("defaultrole")
    headers = await _admin_headers(client)

    create = await client.post(
        "/api/base/user",
        headers=headers,
        json={
            "email": email,
            "name": "Default Role User",
            "password": "Secret1234!",
            "role_ids": [],
        },
    )
    assert create.status_code == 201, create.text
    assert create.json()["role_ids"] == ["base.group_user"]


@pytest.mark.asyncio
async def test_create_user_rejects_unknown_role(client: AsyncClient):
    headers = await _admin_headers(client)
    resp = await client.post(
        "/api/base/user",
        headers=headers,
        json={
            "email": unique_email("badrole"),
            "name": "Bad Role User",
            "password": "Secret1234!",
            "role_ids": ["does.not.exist"],
        },
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_update_user_role_ids(client: AsyncClient):
    email = unique_email("updaterole")
    headers = await _admin_headers(client)

    create = await client.post(
        "/api/base/user",
        headers=headers,
        json={
            "email": email,
            "name": "Update Role User",
            "password": "Secret1234!",
            "role_ids": ["base.group_user"],
        },
    )
    assert create.status_code == 201, create.text
    user_id = create.json()["id"]

    update = await client.put(
        f"/api/base/user/{user_id}",
        headers=headers,
        json={"role_ids": ["base.group_system", "base.group_user"]},
    )
    assert update.status_code == 200, update.text
    roles = set(update.json()["role_ids"])
    assert roles == {"base.group_system", "base.group_user"}
