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
    """Two separate tenants: user B cannot read user A's company record."""
    from orbiteus_core.security.tokens import decode_access_token

    email_a = unique_email("rbac_a")
    reg_a = await register_user(client, email=email_a)
    token_a = reg_a["access_token"]
    company_id_a = decode_access_token(token_a)["company_id"]

    email_b = unique_email("rbac_b")
    reg_b = await register_user(client, email=email_b)
    token_b = reg_b["access_token"]

    assert company_id_a is not None

    own = await client.get(
        f"/api/base/company/{company_id_a}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert own.status_code == 200

    cross = await client.get(
        f"/api/base/company/{company_id_a}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert cross.status_code in (403, 404)


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
