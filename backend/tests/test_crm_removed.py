"""CRM module removed — no runtime routes, registry, or palette leakage."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from orbiteus_core.config import settings
from tests.conftest import login_user


@pytest.mark.asyncio
async def test_crm_not_in_module_registry(client: AsyncClient):
    from orbiteus_core.registry import registry

    assert "crm" not in registry.loaded_modules


@pytest.mark.asyncio
async def test_crm_api_not_mounted(client: AsyncClient):
    token = await login_user(
        client,
        settings.bootstrap_admin_email,
        settings.bootstrap_admin_password,
    )
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.get("/api/crm/lead", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_ui_config_has_no_crm_module(client: AsyncClient):
    resp = await client.get("/api/base/ui-config")
    assert resp.status_code == 200
    names = [m["name"] for m in resp.json()["modules"]]
    assert "crm" not in names


@pytest.mark.asyncio
async def test_registry_db_has_no_crm_models(client: AsyncClient):
    from orbiteus_core.db import AsyncSessionFactory

    async with AsyncSessionFactory() as session:
        rows = await session.execute(
            text("SELECT model_name FROM base_models WHERE model_name LIKE 'crm.%'")
        )
        assert list(rows) == []


@pytest.mark.asyncio
async def test_actions_palette_has_no_crm_lead(client: AsyncClient):
    token = await login_user(
        client,
        settings.bootstrap_admin_email,
        settings.bootstrap_admin_password,
    )
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.get("/api/ai/actions", headers=headers, params={"q": "lead"})
    assert resp.status_code == 200
    for item in resp.json().get("items", []):
        action = item.get("action", item)
        assert "crm" not in action.get("id", "")
        assert "/crm/" not in action.get("target_url", "")
