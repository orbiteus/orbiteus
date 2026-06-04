"""Tests for agent delegation (ADR-0019)."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from orbiteus_core.ai.delegation import (
    DELEGATE_TOOL_NAME,
    MAX_DELEGATION_DEPTH,
    delegate_tool_schema,
    execute_delegate_agent,
)
from orbiteus_core.ai.tools import build_tools_for_agent
from orbiteus_core.context import RequestContext


def test_delegate_tool_schema_shape():
    schema = delegate_tool_schema()
    assert schema["name"] == DELEGATE_TOOL_NAME
    assert "agent_slug" in schema["parameters"]["properties"]


@pytest.mark.asyncio
async def test_delegate_rejects_when_disabled():
    parent = MagicMock()
    parent.can_delegate = False
    parent.id = uuid.uuid4()

    session = AsyncMock()
    ctx = RequestContext(tenant_id=uuid.uuid4(), is_superadmin=True)

    out = await execute_delegate_agent(
        session,
        ctx,
        parent_agent=parent,
        parent_run_id=None,
        current_depth=0,
        arguments={"agent_slug": "helper", "prompt": "Hi"},
    )
    assert out["status"] == "error"
    assert out["code"] == "ai.delegate.disabled"


@pytest.mark.asyncio
async def test_delegate_rejects_max_depth():
    parent = MagicMock()
    parent.can_delegate = True
    parent.allowed_delegate_slugs = ["helper"]
    parent.id = uuid.uuid4()

    session = AsyncMock()
    ctx = RequestContext(tenant_id=uuid.uuid4(), is_superadmin=True)

    out = await execute_delegate_agent(
        session,
        ctx,
        parent_agent=parent,
        parent_run_id=uuid.uuid4(),
        current_depth=MAX_DELEGATION_DEPTH,
        arguments={"agent_slug": "helper", "prompt": "Hi"},
    )
    assert out["code"] == "ai.delegate.max_depth"


def test_build_tools_includes_delegate_when_enabled():
    from orbiteus_core.ai.config import AIModuleConfig, ai_registry

    ai_registry._configs.clear()
    ai_registry.register(
        "base",
        AIModuleConfig(enabled=True, accessible_models=["base.user"]),
    )
    tools = build_tools_for_agent(
        RequestContext(is_superadmin=True),
        module_scope="base",
        allowed_models=["base.user"],
        allowed_actions=[],
        can_delegate=True,
    )
    assert DELEGATE_TOOL_NAME in {t["name"] for t in tools}
