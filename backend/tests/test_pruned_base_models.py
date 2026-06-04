"""Removed base models must not expose auto-CRUD routes."""
from __future__ import annotations

import pytest

from tests.conftest import login_user


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/api/base/partner",
        "/api/base/sequence",
        "/api/base/scheduled-job",
    ],
)
async def test_pruned_models_not_registered(client, path):
    token = await login_user(client, "admin@example.com", "admin1234")
    resp = await client.get(path, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_ui_config_excludes_pruned_models(client):
    resp = await client.get("/api/base/ui-config")
    assert resp.status_code == 200
    base = next(m for m in resp.json()["modules"] if m["name"] == "base")
    names = {m["name"] for m in base["models"]}
    assert "base.partner" not in names
    assert "base.sequence" not in names
    assert "base.scheduled-job" not in names
    assert "base.tenant" not in names
    assert "base.company" in names
    assert "base.user" in names
