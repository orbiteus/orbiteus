"""Module registry lifecycle tests.

Tests:
  - Registry has expected modules (base, auth, crm)
  - Load order is a valid topological sort
  - Model registry has all CRM models
  - UI config: every model has at least 1 field
  - Action registry has expected number of actions
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# 1. Registry has modules
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_registry_has_modules(client):
    """Registry should have 'base', 'auth', and 'crm' modules registered."""
    from orbiteus_core.registry import registry

    assert "base" in registry._modules, "Module 'base' not registered"
    assert "auth" in registry._modules, "Module 'auth' not registered"
    assert "crm" in registry._modules, "Module 'crm' not registered"


# ---------------------------------------------------------------------------
# 2. Load order is valid topological sort
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_registry_load_order(client):
    """Load order must respect dependencies: base < auth < crm."""
    from orbiteus_core.registry import registry

    load_order = registry._load_order
    assert len(load_order) >= 3, f"Expected at least 3 modules in load order, got {load_order}"

    base_idx = load_order.index("base")
    auth_idx = load_order.index("auth")
    crm_idx = load_order.index("crm")

    assert base_idx < auth_idx, (
        f"'base' (idx={base_idx}) should be loaded before 'auth' (idx={auth_idx})"
    )
    assert auth_idx < crm_idx, (
        f"'auth' (idx={auth_idx}) should be loaded before 'crm' (idx={crm_idx})"
    )


# ---------------------------------------------------------------------------
# 3. Model registry has CRM models
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_model_registry_has_crm_models(client):
    """Auto-router model registry should contain all CRM models."""
    from orbiteus_core.auto_router import _model_registry

    expected_models = ["crm.customer", "crm.opportunity", "crm.pipeline", "crm.stage"]
    for model_name in expected_models:
        assert model_name in _model_registry, (
            f"Model '{model_name}' not found in _model_registry. "
            f"Registered models: {list(_model_registry.keys())}"
        )


# ---------------------------------------------------------------------------
# 4. UI config: all registered models have fields
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ui_config_all_registered_models_have_fields(client):
    """GET /api/base/ui-config — every model in the response has at least 1 field."""
    resp = await client.get("/api/base/ui-config")
    assert resp.status_code == 200, f"ui-config failed: {resp.text}"
    data = resp.json()

    assert "modules" in data
    assert len(data["modules"]) > 0, "No modules returned from ui-config"

    for module in data["modules"]:
        for model in module.get("models", []):
            fields = model.get("fields", [])
            assert len(fields) >= 1, (
                f"Model '{model['name']}' in module '{module['name']}' has no fields"
            )


# ---------------------------------------------------------------------------
# 5. Action registry has actions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_action_registry_has_actions(client):
    """ActionRegistry should have at least 16 registered actions from all modules."""
    from orbiteus_core.ai.registry import action_registry

    all_actions = action_registry.get_all()
    assert len(all_actions) >= 16, (
        f"Expected at least 16 actions, got {len(all_actions)}. "
        f"Action IDs: {[a.id for a in all_actions]}"
    )
