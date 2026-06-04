"""Demo seed — reset junk and apply curated dataset."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from orbiteus_core.config import settings
from orbiteus_core.demo_seed import DEMO_PASSWORD, run_demo_seed_pipeline
from tests.conftest import login_user


@pytest.mark.asyncio
async def test_demo_seed_reset_and_apply(client: AsyncClient, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "attachment_storage_path", str(tmp_path))
    from orbiteus_core.storage import get_storage

    get_storage.cache_clear()

    result = await run_demo_seed_pipeline(reset=True, force=True)
    assert result["seed"]["status"] == "seeded"
    assert result["seed"]["companies"] == 2
    assert result["seed"]["attachments"] == 2

    token = await login_user(
        client,
        settings.bootstrap_admin_email,
        settings.bootstrap_admin_password,
    )
    headers = {"Authorization": f"Bearer {token}"}

    companies = await client.get("/api/base/company?limit=10", headers=headers)
    assert companies.status_code == 200
    names = {row["name"] for row in companies.json()["items"]}
    assert "Orbiteus HQ" in names
    assert result["seed"]["companies"] == 2

    users = await client.get("/api/base/user?limit=50", headers=headers)
    assert users.status_code == 200
    emails = {row["email"] for row in users.json()["items"]}
    assert "demo.manager@example.com" in emails
    assert len(emails) <= 5

    hq_id = next(r["id"] for r in companies.json()["items"] if r["name"] == "Orbiteus HQ")
    attachments = await client.get(
        "/api/base/attachments",
        headers=headers,
        params={"res_model": "base.company", "res_id": hq_id},
    )
    assert attachments.status_code == 200
    assert attachments.json()["total"] == 2
    for item in attachments.json()["items"]:
        assert item["file_size"] > 0
        assert item["name"].endswith(".txt")


@pytest.mark.asyncio
async def test_demo_seed_idempotent_skip(client: AsyncClient):
    await run_demo_seed_pipeline(reset=True, force=True)
    second = await run_demo_seed_pipeline(reset=False, force=False)
    assert second["seed"]["status"] == "skipped"
