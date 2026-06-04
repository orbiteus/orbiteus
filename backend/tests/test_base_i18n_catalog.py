"""Canonical UI catalogs ship in modules/base/i18n (en required)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from orbiteus_core.i18n_registry import file_catalog_for, require_base_english_catalog
from tests.conftest import login_user


def test_base_en_catalog_loaded_at_bootstrap():
    require_base_english_catalog()
    en = file_catalog_for("en")
    assert len(en) > 100
    assert en["common.save"] == "Save"
    assert en["nav.dashboard"] == "Dashboard"


@pytest.mark.asyncio
async def test_messages_api_returns_base_catalog(client: AsyncClient):
    token = await login_user(client, "admin@example.com", "admin1234")
    resp = await client.get(
        "/api/base/i18n/messages/en",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    messages = resp.json()["messages"]
    assert messages["common.save"] == "Save"


@pytest.mark.asyncio
async def test_pl_inherits_missing_keys_from_en(client: AsyncClient):
    token = await login_user(client, "admin@example.com", "admin1234")
    resp = await client.get(
        "/api/base/i18n/messages/pl",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    messages = resp.json()["messages"]
    assert messages["nav.dashboard"] == "Pulpit"
    assert len(messages) > 500


@pytest.mark.asyncio
async def test_i18n_locales_hide_disabled_module_languages(client: AsyncClient):
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

    # Re-enable for other tests in same session (optional)
    await client.patch("/api/base/modules/locales", headers=headers, json={"enabled": True})


@pytest.mark.asyncio
async def test_i18n_locales_mark_pl_as_module_pack(client: AsyncClient):
    token = await login_user(client, "admin@example.com", "admin1234")
    resp = await client.get(
        "/api/base/i18n/locales",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    by_code = {row["code"]: row for row in resp.json()["locales"]}
    assert by_code["en"]["source"] == "core"
    assert by_code["en"]["module"] == "base"
    assert by_code["pl"]["source"] == "module"
    assert by_code["pl"]["module"] == "locales"


@pytest.mark.asyncio
async def test_de_and_fr_locales_served(client: AsyncClient):
    token = await login_user(client, "admin@example.com", "admin1234")
    headers = {"Authorization": f"Bearer {token}"}
    cases = (
        ("de", "Speichern", "Abbrechen"),
        ("fr", "Enregistrer", "Annuler"),
    )
    for lang, save_label, cancel_label in cases:
        resp = await client.get(f"/api/base/i18n/messages/{lang}", headers=headers)
        assert resp.status_code == 200, resp.text
        messages = resp.json()["messages"]
        assert messages["common.save"] == save_label
        assert messages["common.cancel"] == cancel_label
