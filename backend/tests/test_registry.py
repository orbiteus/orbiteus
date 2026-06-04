"""Module registry lifecycle tests."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_registry_has_modules(client):
    from orbiteus_core.registry import registry

    assert "base" in registry._modules
    assert "auth" in registry._modules
    assert "crm" not in registry._modules


@pytest.mark.asyncio
async def test_registry_load_order(client):
    from orbiteus_core.registry import registry

    load_order = registry._load_order
    assert "base" in load_order
    assert "auth" in load_order
    base_idx = load_order.index("base")
    auth_idx = load_order.index("auth")
    assert base_idx < auth_idx


@pytest.mark.asyncio
async def test_model_registry_has_base_models(client):
    from orbiteus_core.auto_router import _model_registry

    for model_name in ("base.user", "base.company"):
        assert model_name in _model_registry


@pytest.mark.asyncio
async def test_ui_config_all_registered_models_have_fields(client):
    resp = await client.get("/api/base/ui-config")
    assert resp.status_code == 200
    data = resp.json()

    for mod in data["modules"]:
        for model in mod["models"]:
            assert len(model["fields"]) >= 1, (
                f"Model {model['name']} has no fields in ui-config"
            )


@pytest.mark.asyncio
async def test_ui_config_fk_relation_hints(client):
    """base.user company_ids many2many should resolve to base.company."""
    resp = await client.get("/api/base/ui-config")
    assert resp.status_code == 200
    base = next(m for m in resp.json()["modules"] if m["name"] == "base")
    user = next(m for m in base["models"] if m["name"] == "base.user")
    company_field = next((f for f in user["fields"] if f["name"] == "company_ids"), None)
    assert company_field is not None
    assert company_field.get("type") == "many2many"
    assert company_field.get("relation") == "base.company"


@pytest.mark.asyncio
async def test_base_ai_config_registered():
    from orbiteus_core.ai.config import ai_registry

    cfg = ai_registry.get("base")
    assert cfg is not None
    assert cfg.enabled
    assert "base.company" in cfg.accessible_models
