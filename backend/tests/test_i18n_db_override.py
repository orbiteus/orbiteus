"""DB ui-translation overrides merge into API catalogs."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from orbiteus_core.i18n_registry import clear_ui_translation_cache
from tests.conftest import login_user


@pytest.mark.asyncio
async def test_db_override_overrides_module_catalog(client: AsyncClient):
    token = await login_user(client, "admin@example.com", "admin1234")
    headers = {"Authorization": f"Bearer {token}"}
    override_key = "test.i18n.db.override"

    create = await client.post(
        "/api/base/ui-translation",
        headers=headers,
        json={
            "lang": "pl",
            "module": "test",
            "msg_key": override_key,
            "value": "Z bazy",
        },
    )
    assert create.status_code == 201, create.text
    record_id = create.json()["id"]
    try:
        clear_ui_translation_cache()
        resp = await client.get("/api/base/i18n/messages/pl", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["messages"][override_key] == "Z bazy"
    finally:
        clear_ui_translation_cache()
        await client.delete(f"/api/base/ui-translation/{record_id}", headers=headers)
        clear_ui_translation_cache()
