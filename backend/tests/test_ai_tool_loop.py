"""Unit tests for AgentLoop and read tool execution."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orbiteus_core.ai.config import AIModuleConfig, ai_registry
from orbiteus_core.ai.loop import run_agent_loop
from orbiteus_core.ai.providers.base import ChatResult
from orbiteus_core.ai.query_executor import normalize_domain, resolve_model_from_read_tool
from orbiteus_core.ai.tools import build_tools_for_agent
from orbiteus_core.context import RequestContext


@pytest.mark.asyncio
async def test_agent_loop_executes_read_tool_then_completes():
    ai_registry._configs.clear()
    ai_registry.register(
        "base",
        AIModuleConfig(enabled=True, accessible_models=["base.user"]),
    )

    calls = {"n": 0}

    async def fake_chat(api_key, *, messages, tools=None, model=None, max_tokens=1024, temperature=0.2):
        calls["n"] += 1
        if calls["n"] == 1:
            return ChatResult(
                text="",
                tool_calls=[
                    {"id": "tc1", "name": "read_base_user", "arguments": {"limit": 5}},
                ],
                usage_tokens=10,
            )
        return ChatResult(text="You have users in the tenant.", usage_tokens=5)

    provider = MagicMock()
    provider.chat = fake_chat

    read_outcome = {
        "status": "ok",
        "model": "base.user",
        "total": 1,
        "items": [{"id": str(uuid.uuid4()), "name": "Admin"}],
    }

    session = AsyncMock()
    ctx = RequestContext(tenant_id=uuid.uuid4(), user_id=uuid.uuid4(), is_superadmin=True)

    with patch(
        "orbiteus_core.ai.loop.execute_read_tool",
        AsyncMock(return_value=read_outcome),
    ), patch(
        "orbiteus_core.ai.loop._audit_tool_step",
        AsyncMock(),
    ):
        result = await run_agent_loop(
            session,
            ctx,
            provider=provider,
            api_key="k",
            messages=[{"role": "user", "content": "How many users?"}],
            tools=[{"name": "read_base_user"}],
        )

    assert result.text == "You have users in the tenant."
    assert result.turns == 2
    assert len(result.tool_trace) == 1
    assert result.tool_trace[0]["name"] == "read_base_user"


def test_resolve_model_from_read_tool():
    ai_registry._configs.clear()
    ai_registry.register(
        "base",
        AIModuleConfig(enabled=True, accessible_models=["base.user", "base.company"]),
    )
    assert resolve_model_from_read_tool("read_base_user") == "base.user"
    assert resolve_model_from_read_tool("read_base_company") == "base.company"
    assert resolve_model_from_read_tool("read_unknown") is None


def test_normalize_domain_accepts_dict_and_tuples():
    assert normalize_domain({"status": "open"}) == [("status", "=", "open")]
    assert normalize_domain([("name", "ilike", "%acme%")]) == [("name", "ilike", "%acme%")]


def test_build_tools_for_agent_filters_models():
    ai_registry._configs.clear()
    ai_registry.register(
        "base",
        AIModuleConfig(
            enabled=True,
            accessible_models=["base.user", "base.company"],
            callable_actions=["base.user.create"],
            embed_models=["base.user"],
        ),
    )
    ctx = RequestContext(is_superadmin=True)
    tools = build_tools_for_agent(
        ctx,
        module_scope="base",
        allowed_models=["base.user"],
        allowed_actions=[],
        can_delegate=True,
    )
    names = {t["name"] for t in tools}
    assert "read_base_user" in names
    assert "read_base_company" not in names
    assert "semantic_search" in names
    assert "delegate_agent" in names
