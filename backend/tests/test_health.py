"""Smoke test: health check endpoint."""
import pytest


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    resp = await client.get("/api/base/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_health_no_auth_required(client):
    """Health endpoint must be reachable without a token."""
    resp = await client.get("/api/base/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_branding_no_auth_required(client):
    """Branding endpoint is public."""
    resp = await client.get("/api/base/branding")
    assert resp.status_code == 200
    data = resp.json()
    assert "name" in data
