"""Integration tests for base.agent and /api/ai/runs (ADR-0018)."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from orbiteus_core.config import settings
from tests.conftest import login_user


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _superadmin_token(client) -> str:
    return await login_user(
        client,
        settings.bootstrap_admin_email,
        settings.bootstrap_admin_password,
    )


@pytest.mark.asyncio
async def test_base_agent_list_includes_seeded_crm_assistant(client):
    token = await _superadmin_token(client)
    r = await client.get("/api/base/agent", headers=_h(token))
    assert r.status_code == 200
    slugs = {row["slug"] for row in r.json()["items"]}
    assert "crm-assistant" in slugs


@pytest.mark.asyncio
async def test_base_agent_create_and_delete_custom_agent(client):
    token = await _superadmin_token(client)
    slug = f"test-agent-{uuid.uuid4().hex[:8]}"
    create = await client.post(
        "/api/base/agent",
        headers=_h(token),
        json={
            "slug": slug,
            "name": "Test agent",
            "module_scope": "crm",
            "system_prompt": "Test persona",
            "allowed_models": ["base.user"],
            "allowed_actions": [],
        },
    )
    assert create.status_code == 201, create.text
    agent_id = create.json()["id"]

    delete = await client.delete(f"/api/base/agent/{agent_id}", headers=_h(token))
    assert delete.status_code == 204


@pytest.mark.asyncio
async def test_base_agent_cannot_delete_system_agent(client):
    token = await _superadmin_token(client)
    listing = await client.get("/api/base/agent", headers=_h(token), params={"limit": 50})
    system = next(
        row for row in listing.json()["items"] if row["slug"] == "crm-assistant"
    )

    delete = await client.delete(f"/api/base/agent/{system['id']}", headers=_h(token))
    assert delete.status_code == 400
    assert "System agents cannot be deleted" in delete.json()["detail"]


@pytest.mark.asyncio
async def test_agent_run_requires_credential(client):
    token = await _superadmin_token(client)
    listing = await client.get("/api/base/agent", headers=_h(token), params={"limit": 50})
    agent = next(row for row in listing.json()["items"] if row["slug"] == "crm-assistant")

    r = await client.post(
        "/api/ai/runs",
        headers=_h(token),
        json={"agent_id": agent["id"], "prompt": "Hello"},
    )
    # No BYOK in test DB → validation error from executor
    assert r.status_code in (400, 412)


@pytest.mark.asyncio
async def test_agent_run_sync_with_mocked_loop(client):
    token = await _superadmin_token(client)
    listing = await client.get("/api/base/agent", headers=_h(token), params={"limit": 50})
    agent = next(row for row in listing.json()["items"] if row["slug"] == "crm-assistant")

    from orbiteus_core.ai.loop import AgentLoopResult

    mock_result = AgentLoopResult(
        text="Pipeline looks healthy.",
        tool_trace=[{"turn": 1, "name": "read_crm_lead", "status": "ok"}],
        usage_tokens=42,
        turns=1,
    )

    with patch(
        "orbiteus_core.ai.executor.run_agent_loop",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        with patch(
            "orbiteus_core.ai.executor.fetch_credential",
            new_callable=AsyncMock,
            return_value={
                "secret": "test-key",
                "model_default": "claude-test",
                "monthly_token_budget": None,
            },
        ):
            with patch(
                "orbiteus_core.ai.executor.has_budget",
                new_callable=AsyncMock,
                return_value=True,
            ):
                r = await client.post(
                    "/api/ai/runs",
                    headers=_h(token),
                    json={
                        "agent_id": agent["id"],
                        "prompt": "Summarize leads",
                    },
                )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "completed"
    assert body["text"] == "Pipeline looks healthy."
    assert body["usage_tokens"] == 42

    run_id = body["id"]
    get_run = await client.get(f"/api/ai/runs/{run_id}", headers=_h(token))
    assert get_run.status_code == 200
    assert get_run.json()["status"] == "completed"
