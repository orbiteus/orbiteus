"""Phase 1 + Phase 2 smoke tests.

PHASE 1:
  - GET /api/base/ui-config returns modules + fields
  - Query params filtering works on list endpoints

PHASE 2:
  - GET /api/ai/actions returns ranked actions
  - Command Palette resolves "nowy klient" → Utwórz klienta
"""
from __future__ import annotations

import pytest

from tests.conftest import login_user, register_user, unique_email


# ---------------------------------------------------------------------------
# Phase 1: ui-config
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ui_config_returns_modules(client):
    """GET /api/base/ui-config returns at least one module with models."""
    resp = await client.get("/api/base/ui-config")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "modules" in data
    assert len(data["modules"]) > 0


@pytest.mark.asyncio
async def test_ui_config_crm_fields(client):
    """crm.customer model has expected fields with correct types."""
    resp = await client.get("/api/base/ui-config")
    assert resp.status_code == 200
    data = resp.json()

    crm = next((m for m in data["modules"] if m["name"] == "crm"), None)
    assert crm is not None, "CRM module missing from ui-config"

    customer = next((m for m in crm["models"] if "customer" in m["name"]), None)
    assert customer is not None, "crm.customer model missing"

    field_names = [f["name"] for f in customer["fields"]]
    assert "name" in field_names
    assert "email" in field_names

    name_field = next(f for f in customer["fields"] if f["name"] == "name")
    assert name_field["required"] is True
    assert name_field["type"] == "text"

    email_field = next(f for f in customer["fields"] if f["name"] == "email")
    assert email_field["type"] == "email"


@pytest.mark.asyncio
async def test_ui_config_has_views(client):
    """crm.customer model has list/form view arch strings."""
    resp = await client.get("/api/base/ui-config")
    data = resp.json()
    crm = next(m for m in data["modules"] if m["name"] == "crm")
    customer = next(m for m in crm["models"] if "customer" in m["name"])
    assert customer["views"]["list"] is not None, "list view arch missing"
    assert customer["views"]["form"] is not None, "form view arch missing"


# ---------------------------------------------------------------------------
# Phase 1: Query params filtering
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_query_filter_by_field(client):
    """?status=prospect filters customers correctly."""
    tokens = await register_user(client)
    token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create one prospect and one customer
    await client.post("/api/crm/customer", json={"name": "QF Prospect", "status": "prospect"}, headers=headers)
    await client.post("/api/crm/customer", json={"name": "QF Customer", "status": "customer"}, headers=headers)

    # Filter only prospects
    resp = await client.get("/api/crm/customer", params={"status": "prospect"}, headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    statuses = {i["status"] for i in items}
    assert "prospect" in statuses
    assert "customer" not in statuses, "Non-prospect leaked through filter"


@pytest.mark.asyncio
async def test_query_filter_contains(client):
    """?name__contains=UniqueStr filters by substring (case-insensitive)."""
    tokens = await register_user(client)
    token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    unique = "XQZFILTERTEST"
    await client.post("/api/crm/customer", json={"name": f"Co {unique} Inc"}, headers=headers)
    await client.post("/api/crm/customer", json={"name": "Other Company"}, headers=headers)

    resp = await client.get("/api/crm/customer", params={"name__contains": unique.lower()}, headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    names = [i["name"] for i in items]
    assert any(unique in n for n in names), f"{unique} not found in {names}"
    assert not any("Other" in n for n in names), "Unrelated record leaked"


@pytest.mark.asyncio
async def test_query_ordering(client):
    """?order_by=name&order_dir=asc returns sorted results."""
    tokens = await register_user(client)
    token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    await client.post("/api/crm/customer", json={"name": "ZZZ Last"}, headers=headers)
    await client.post("/api/crm/customer", json={"name": "AAA First"}, headers=headers)

    resp = await client.get("/api/crm/customer",
                            params={"order_by": "name", "order_dir": "asc", "limit": 100},
                            headers=headers)
    assert resp.status_code == 200
    names = [i["name"] for i in resp.json()["items"]]
    aaa_idx = next((i for i, n in enumerate(names) if "AAA" in n), None)
    zzz_idx = next((i for i, n in enumerate(names) if "ZZZ" in n), None)
    assert aaa_idx is not None and zzz_idx is not None
    assert aaa_idx < zzz_idx, f"Ordering wrong: AAA at {aaa_idx}, ZZZ at {zzz_idx}"


# ---------------------------------------------------------------------------
# Phase 2: AI Actions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ai_actions_requires_auth(client):
    """GET /api/ai/actions requires a valid token."""
    resp = await client.get("/api/ai/actions", params={"q": "test"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ai_actions_returns_results(client):
    """GET /api/ai/actions?q=klient returns ranked actions."""
    tokens = await register_user(client)
    token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/ai/actions", params={"q": "klient", "limit": 5}, headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "results" in data
    assert len(data["results"]) > 0

    # First result should be about customers
    first = data["results"][0]["action"]
    assert "crm" in first["id"] or "klient" in first["label"].lower()


@pytest.mark.asyncio
async def test_ai_actions_command_palette_scenario(client):
    """Cmd+K scenario: 'nowy klient' → top result is 'Utwórz klienta'."""
    tokens = await register_user(client)
    token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/ai/actions", params={"q": "nowy klient", "limit": 8}, headers=headers)
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) > 0

    top = results[0]["action"]
    assert top["id"] == "crm.customer.create", (
        f"Expected 'crm.customer.create' as top result, got '{top['id']}'"
    )
    assert top["target_url"] == "/crm/customer/new"


@pytest.mark.asyncio
async def test_ai_actions_empty_query_returns_all(client):
    """Empty query returns all registered actions."""
    tokens = await register_user(client)
    token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/ai/actions", params={"q": "", "limit": 50}, headers=headers)
    assert resp.status_code == 200
    results = resp.json()["results"]
    # We have 3 modules with actions.py → at least 5 actions total
    assert len(results) >= 5
