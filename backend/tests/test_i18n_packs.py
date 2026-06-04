"""Module UI translation packs and merge API."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import AsyncClient

from orbiteus_core.i18n_loader import discover_module_i18n, load_json_catalog
from orbiteus_core.i18n_registry import (
    clear_ui_translation_cache,
    file_catalog_for,
    register_module_messages,
    register_locale_meta,
)
from tests.conftest import login_user


def test_load_json_catalog_flat_and_nested(tmp_path: Path):
    flat = tmp_path / "flat.json"
    flat.write_text(json.dumps({"common.save": "Zapisz"}), encoding="utf-8")
    assert load_json_catalog(flat) == {"common.save": "Zapisz"}

    nested = tmp_path / "nested.json"
    nested.write_text(json.dumps({"common": {"save": "Save"}}), encoding="utf-8")
    assert load_json_catalog(nested) == {"common.save": "Save"}


def test_discover_module_i18n_auto_glob(tmp_path: Path):
    i18n = tmp_path / "i18n"
    i18n.mkdir()
    (i18n / "pl.json").write_text('{"demo.hello": "Cześć"}', encoding="utf-8")
    manifest = {"name": "demo"}
    found = discover_module_i18n(tmp_path, manifest)
    assert len(found) == 1
    assert found[0][1] == "pl"
    assert found[0][2]["demo.hello"] == "Cześć"


def test_register_module_messages_merge_order():
    clear_ui_translation_cache()
    register_module_messages("base", "pl", {"demo.alpha": "A"})
    register_module_messages("crm", "pl", {"demo.alpha": "B"})
    assert file_catalog_for("pl")["demo.alpha"] == "B"


@pytest.mark.asyncio
async def test_i18n_locales_endpoint(client: AsyncClient):
    register_locale_meta([{"code": "es", "label": "Español", "dayjs": "es"}])
    token = await login_user(client, "admin@example.com", "admin1234")
    resp = await client.get(
        "/api/base/i18n/locales",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    codes = {row["code"] for row in resp.json()["locales"]}
    assert "en" in codes
    assert "es" in codes


@pytest.fixture(autouse=True)
def _fresh_db_i18n_cache():
    clear_ui_translation_cache()
    yield
    clear_ui_translation_cache()


@pytest.mark.asyncio
async def test_i18n_messages_endpoint(client: AsyncClient):
    register_module_messages("demo", "pl", {"custom.key": "Wartość"})
    token = await login_user(client, "admin@example.com", "admin1234")
    resp = await client.get(
        "/api/base/i18n/messages/pl",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["lang"] == "pl"
    assert body["messages"]["custom.key"] == "Wartość"
    # English fallback from base/i18n/en.json (module file catalog)
    assert body["messages"]["nav.dashboard"] == "Pulpit"
    assert "common.save" in body["messages"]


@pytest.mark.asyncio
async def test_i18n_messages_unknown_locale_falls_back_to_en(client: AsyncClient):
    token = await login_user(client, "admin@example.com", "admin1234")
    resp = await client.get(
        "/api/base/i18n/messages/xx",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["lang"] == "en"
    assert resp.json()["messages"]["common.save"] == "Save"
