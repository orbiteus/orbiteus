"""i18n API respects module.<name>.enabled flags."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from orbiteus_core.i18n_registry import active_language_codes
from tests.conftest import login_user


def test_active_language_codes_filters_disabled_owner():
    enabled_map = {"locales": False}
    codes = active_language_codes(enabled_map)
    assert codes == frozenset({"en"})


@pytest.mark.asyncio
async def test_locales_api_omits_disabled_pack(client: AsyncClient):
    token = await login_user(client, "admin@example.com", "admin1234")
    headers = {"Authorization": f"Bearer {token}"}

    disable = await client.patch(
        "/api/base/modules/locales",
        headers=headers,
        json={"enabled": False},
    )
    assert disable.status_code == 200, disable.text

    resp = await client.get("/api/base/i18n/locales", headers=headers)
    assert resp.status_code == 200
    codes = {row["code"] for row in resp.json()["locales"]}
    assert codes == {"en"}

    pl_resp = await client.get("/api/base/i18n/messages/pl", headers=headers)
    assert pl_resp.status_code == 200
    assert pl_resp.json()["lang"] == "en"

    await client.patch(
        "/api/base/modules/locales",
        headers=headers,
        json={"enabled": True},
    )


@pytest.mark.asyncio
async def test_messages_endpoint_sets_cache_control(client: AsyncClient):
    token = await login_user(client, "admin@example.com", "admin1234")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/base/i18n/messages/en", headers=headers)
    assert resp.status_code == 200
    assert "max-age=300" in resp.headers.get("cache-control", "").lower()
