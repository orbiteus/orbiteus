"""User last_login metadata on successful auth."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import login_user, register_user, unique_email


@pytest.mark.asyncio
async def test_login_records_last_login_and_device(client: AsyncClient):
    email = unique_email("lastlogin")
    await register_user(client, email=email)

    resp = await client.post(
        "/api/auth/login",
        json={"email": email, "password": "test1234"},
        headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"},
    )
    assert resp.status_code == 200

    token = resp.json()["access_token"]
    me = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200
    user = me.json()
    assert user["last_login"] is not None
    assert user["last_login_device"] == "mobile"


@pytest.mark.asyncio
async def test_ui_config_user_form_excludes_last_login(client: AsyncClient):
    token = await login_user(client, "admin@example.com", "admin1234")
    resp = await client.get(
        "/api/base/ui-config",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    base = next(m for m in resp.json()["modules"] if m["name"] == "base")
    user = next(m for m in base["models"] if m["name"] == "base.user")
    field_names = {f["name"] for f in user["fields"]}
    assert "last_login" not in field_names
    assert "last_login_device" not in field_names
    list_view = user["views"]["list"]
    assert any(c.get("widget") == "last_login" for c in list_view["columns"])
