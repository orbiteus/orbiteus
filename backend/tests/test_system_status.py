"""Tests for expanded Orbiteus stack component catalogue."""
from __future__ import annotations

import pytest

from orbiteus_core.system_status_catalog import COMPONENT_ORDER
from tests.conftest import login_user, register_user


@pytest.mark.asyncio
async def test_system_status_requires_auth(client):
    resp = await client.get("/api/base/system-status")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_system_status_includes_full_engine_stack(client):
    token = await login_user(client, "admin@example.com", "admin1234")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/base/system-status", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("version")
    by_id = {c["id"]: c for c in data["components"]}

    required = (
        "orbiteus",
        "python",
        "fastapi",
        "sqlalchemy",
        "asyncpg",
        "alembic",
        "pydantic",
        "postgresql",
        "module_registry",
        "rbac",
        "audit",
        "event_bus",
        "celery_lib",
    )
    for cid in required:
        assert cid in by_id, f"missing component {cid}"

    assert by_id["orbiteus"]["message"].startswith("v")
    assert by_id["orbiteus"]["detail"]["version"] == data["version"]
    assert by_id["fastapi"]["message"].startswith("v")
    assert "module_versions" in by_id["module_registry"]["detail"]
    assert by_id["cache"]["message"].startswith("v")
    assert by_id["alembic"]["status"] in ("ok", "degraded")
    assert "modules" in by_id["module_registry"]["detail"] or "modules" in str(
        by_id["module_registry"]["message"]
    )

    ids = [c["id"] for c in data["components"]]
    assert ids.index("orbiteus") < ids.index("python") < ids.index("sqlalchemy") < ids.index("postgresql")
    assert ids.index("auth_jwt") < ids.index("ai_module_config") < ids.index("ai_tooling")
    assert len(data["components"]) >= len(COMPONENT_ORDER) - 2


@pytest.mark.asyncio
async def test_system_status_ai_layer_is_own_category(client):
    token = await login_user(client, "admin@example.com", "admin1234")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/base/system-status", headers=headers)
    assert resp.status_code == 200
    ai_tiles = [c for c in resp.json()["components"] if c["group"] == "ai"]
    assert len(ai_tiles) >= 8
    assert "ai_layer" not in {c["id"] for c in resp.json()["components"]}
    assert any(c["id"] == "ai_module_config" for c in ai_tiles)
    assert any(c["id"] == "ai_credentials" for c in ai_tiles)


@pytest.mark.asyncio
async def test_system_status_accessible_to_authenticated_tenant_user(client):
    reg = await register_user(client)
    headers = {"Authorization": f"Bearer {reg['access_token']}"}

    resp = await client.get("/api/base/system-status", headers=headers)
    assert resp.status_code == 200
