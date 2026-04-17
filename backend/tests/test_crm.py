"""Smoke tests: CRM endpoints + tenant isolation.

Test scenarios from the plan:
- CRUD (create, list, get, update, delete)
- Tenant isolation — Firma A cannot see Firma B's customers
- Unauthenticated access rejected
"""
from __future__ import annotations

import pytest

from tests.conftest import login_user, register_user, unique_email


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def create_customer(client, token: str, name: str, **kwargs) -> dict:
    payload = {"name": name, **kwargs}
    resp = await client.post(
        "/api/crm/customer",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201), f"create_customer failed: {resp.text}"
    return resp.json()


def _items(data) -> list:
    """Extract items list from either paginated or plain response."""
    if isinstance(data, dict):
        return data.get("items", data.get("data", []))
    return data


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_customer(client):
    tokens = await register_user(client)
    token = tokens["access_token"]
    customer = await create_customer(client, token, "ACME Corp", email="acme@test.pl")
    assert customer["name"] == "ACME Corp"
    assert "id" in customer


@pytest.mark.asyncio
async def test_list_customers(client):
    tokens = await register_user(client)
    token = tokens["access_token"]

    await create_customer(client, token, "Alpha Co")
    await create_customer(client, token, "Beta Co")

    resp = await client.get(
        "/api/crm/customer",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    names = [c["name"] for c in _items(resp.json())]
    assert "Alpha Co" in names
    assert "Beta Co" in names


@pytest.mark.asyncio
async def test_get_customer_by_id(client):
    tokens = await register_user(client)
    token = tokens["access_token"]
    created = await create_customer(client, token, "Delta Inc")

    resp = await client.get(
        f"/api/crm/customer/{created['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Delta Inc"


@pytest.mark.asyncio
async def test_update_customer(client):
    tokens = await register_user(client)
    token = tokens["access_token"]
    created = await create_customer(client, token, "Old Name")

    resp = await client.put(
        f"/api/crm/customer/{created['id']}",
        json={"name": "New Name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"


@pytest.mark.asyncio
async def test_delete_customer_soft(client):
    tokens = await register_user(client)
    token = tokens["access_token"]
    created = await create_customer(client, token, "To Delete")
    customer_id = created["id"]

    del_resp = await client.delete(
        f"/api/crm/customer/{customer_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_resp.status_code in (200, 204)

    # After soft delete, record should not appear in list
    list_resp = await client.get(
        "/api/crm/customer",
        headers={"Authorization": f"Bearer {token}"},
    )
    ids = [c["id"] for c in _items(list_resp.json())]
    assert customer_id not in ids


# ---------------------------------------------------------------------------
# Tenant isolation — Firma A must NOT see Firma B's data
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tenant_isolation(client):
    """Firma A registers, creates a customer. Firma B must not see it."""
    # Firma A
    tokens_a = await register_user(client, email=unique_email("firma_a"))
    token_a = tokens_a["access_token"]
    await create_customer(client, token_a, "Klient Firmy A – UNIQUE_ISOLATION_TEST")

    # Firma B — completely separate tenant
    tokens_b = await register_user(client, email=unique_email("firma_b"))
    token_b = tokens_b["access_token"]

    resp = await client.get(
        "/api/crm/customer",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 200
    names = [c["name"] for c in _items(resp.json())]
    assert "Klient Firmy A – UNIQUE_ISOLATION_TEST" not in names, (
        "Tenant isolation broken: Firma B can see Firma A's customer!"
    )


# ---------------------------------------------------------------------------
# Auth guards
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_customer_list_requires_auth(client):
    resp = await client.get("/api/crm/customer")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_customer_create_requires_auth(client):
    resp = await client.post("/api/crm/customer", json={"name": "No Auth"})
    assert resp.status_code == 401
