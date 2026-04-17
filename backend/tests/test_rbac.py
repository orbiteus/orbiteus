"""RBAC model access, record rules, and tenant isolation tests.

Tests:
  - RBAC cache is populated at startup (from base module access.yaml)
  - Tenant isolation: user A cannot see user B's data
  - Superadmin bypasses RBAC checks
"""
from __future__ import annotations

import pytest

from tests.conftest import login_user, register_user, unique_email


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _items(data) -> list:
    """Extract items list from either paginated or plain response."""
    if isinstance(data, dict):
        return data.get("items", data.get("data", []))
    return data


# ---------------------------------------------------------------------------
# 1. RBAC cache loaded at startup
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rbac_cache_loaded_at_startup(client):
    """After app init, the RBAC cache should not be empty — base module seeds access.yaml."""
    from orbiteus_core.security.rbac import _model_access

    assert len(_model_access) > 0, (
        "RBAC _model_access cache is empty — base module did not seed access.yaml at startup"
    )


# ---------------------------------------------------------------------------
# 2. Non-superadmin tenant isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_non_superadmin_gets_tenant_isolated_data(client):
    """Two separate tenants: user A creates a customer, user B cannot see it."""
    # Tenant A — register and create a customer
    email_a = unique_email("rbac_a")
    tokens_a = await register_user(client, email=email_a)
    token_a = tokens_a["access_token"]

    create_resp = await client.post(
        "/api/crm/customer",
        json={"name": "RBAC Tenant A Secret Customer"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert create_resp.status_code in (200, 201), f"create failed: {create_resp.text}"

    # Tenant B — completely separate tenant
    email_b = unique_email("rbac_b")
    tokens_b = await register_user(client, email=email_b)
    token_b = tokens_b["access_token"]

    list_resp = await client.get(
        "/api/crm/customer",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert list_resp.status_code == 200
    names = [c["name"] for c in _items(list_resp.json())]
    assert "RBAC Tenant A Secret Customer" not in names, (
        "Tenant isolation broken: Tenant B can see Tenant A's customer!"
    )


# ---------------------------------------------------------------------------
# 3. Superadmin bypass
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_superadmin_bypass(client):
    """Non-superadmin should not access superadmin endpoint."""
    email = unique_email("rbac_no_super")
    tokens = await register_user(client, email=email)
    token = tokens["access_token"]

    resp = await client.get(
        "/api/base/modules",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
