"""CRM custom endpoint tests: stats, pipeline kanban, opportunity move.

Tests:
  - GET /api/crm/stats returns dashboard statistics
  - Pipeline kanban returns stages with grouped opportunities
  - POST /api/crm/opportunity/{id}/move changes the stage
"""
from __future__ import annotations

import pytest

from tests.conftest import login_user, register_user, unique_email


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _auth_headers(client) -> dict[str, str]:
    """Register a new user and return Authorization headers."""
    email = unique_email("crm_ep")
    tokens = await register_user(client, email=email)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _create_pipeline(client, headers: dict, name: str = "Test Pipeline") -> dict:
    resp = await client.post(
        "/api/crm/pipeline",
        json={"name": name},
        headers=headers,
    )
    assert resp.status_code in (200, 201), f"create pipeline failed: {resp.text}"
    return resp.json()


async def _create_stage(
    client, headers: dict, pipeline_id: str, name: str, sequence: int = 10
) -> dict:
    resp = await client.post(
        "/api/crm/stage",
        json={
            "name": name,
            "pipeline_id": pipeline_id,
            "sequence": sequence,
        },
        headers=headers,
    )
    assert resp.status_code in (200, 201), f"create stage failed: {resp.text}"
    return resp.json()


async def _create_opportunity(
    client, headers: dict, name: str, pipeline_id: str, stage_id: str,
    expected_revenue: float = 1000.0,
) -> dict:
    resp = await client.post(
        "/api/crm/opportunity",
        json={
            "name": name,
            "pipeline_id": pipeline_id,
            "stage_id": stage_id,
            "expected_revenue": expected_revenue,
        },
        headers=headers,
    )
    assert resp.status_code in (200, 201), f"create opportunity failed: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# 1. CRM stats
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_crm_stats(client):
    """GET /api/crm/stats returns JSON with customer/opportunity counts."""
    headers = await _auth_headers(client)

    # Create some data so stats are not empty
    await client.post(
        "/api/crm/customer",
        json={"name": "Stats Customer"},
        headers=headers,
    )

    resp = await client.get("/api/crm/stats", headers=headers)
    assert resp.status_code == 200, f"stats failed: {resp.text}"
    data = resp.json()

    assert "total_customers" in data
    assert "total_opportunities" in data
    assert isinstance(data["total_customers"], int)
    assert isinstance(data["total_opportunities"], int)
    assert data["total_customers"] >= 1


# ---------------------------------------------------------------------------
# 2. Pipeline kanban
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_crm_pipeline_kanban(client):
    """Create a pipeline + stage + opportunity, then verify kanban endpoint."""
    headers = await _auth_headers(client)

    # Setup: pipeline -> stage -> opportunity
    pipeline = await _create_pipeline(client, headers, "Kanban Pipeline")
    stage = await _create_stage(client, headers, pipeline["id"], "Qualification", sequence=10)
    opp = await _create_opportunity(
        client, headers, "Big Deal", pipeline["id"], stage["id"], expected_revenue=5000.0,
    )

    # Fetch kanban
    resp = await client.get(
        f"/api/crm/pipeline/{pipeline['id']}/kanban",
        headers=headers,
    )
    assert resp.status_code == 200, f"kanban failed: {resp.text}"
    data = resp.json()

    assert data["pipeline_id"] == str(pipeline["id"])
    assert len(data["columns"]) >= 1

    # Find our stage column
    col = next(
        (c for c in data["columns"] if c["stage_id"] == str(stage["id"])),
        None,
    )
    assert col is not None, "Stage column not found in kanban response"
    assert col["stage_name"] == "Qualification"
    assert col["count"] >= 1

    # Verify opportunity is inside the column
    opp_ids = [o["id"] for o in col["opportunities"]]
    assert str(opp["id"]) in opp_ids, "Opportunity not found in kanban column"


# ---------------------------------------------------------------------------
# 3. Opportunity move
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_crm_opportunity_move(client):
    """Move an opportunity from stage 1 to stage 2."""
    headers = await _auth_headers(client)

    # Setup: pipeline -> 2 stages -> opportunity in stage 1
    pipeline = await _create_pipeline(client, headers, "Move Pipeline")
    stage1 = await _create_stage(client, headers, pipeline["id"], "New", sequence=10)
    stage2 = await _create_stage(client, headers, pipeline["id"], "Qualified", sequence=20)
    opp = await _create_opportunity(
        client, headers, "Move Deal", pipeline["id"], stage1["id"],
    )

    # Move opportunity to stage 2
    move_resp = await client.post(
        f"/api/crm/opportunity/{opp['id']}/move",
        params={"stage_id": str(stage2["id"])},
        headers=headers,
    )
    assert move_resp.status_code == 200, f"move failed: {move_resp.text}"

    # Verify the opportunity is now in stage 2
    get_resp = await client.get(
        f"/api/crm/opportunity/{opp['id']}",
        headers=headers,
    )
    assert get_resp.status_code == 200
    updated = get_resp.json()
    assert str(updated["stage_id"]) == str(stage2["id"]), (
        f"Opportunity stage_id should be {stage2['id']} but is {updated['stage_id']}"
    )
