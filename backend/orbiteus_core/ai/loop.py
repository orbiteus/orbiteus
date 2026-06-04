"""Multi-turn AI chat with automatic tool execution (ADR-0018, ADR-0019)."""
from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.ai.budget import increment
from orbiteus_core.ai.delegation import DELEGATE_TOOL_NAME, execute_delegate_agent
from orbiteus_core.ai.dispatcher import dispatch_tool_call
from orbiteus_core.ai.providers.base import ChatResult, ChatStreamEvent, Provider, ProviderError
from orbiteus_core.ai.query_executor import execute_read_tool, execute_semantic_search
from orbiteus_core.context import RequestContext

logger = logging.getLogger(__name__)

MAX_TURNS = 8


@dataclass
class DelegationContext:
    parent_agent: Any = None
    parent_run_id: UUID | None = None
    depth: int = 0


@dataclass
class AgentLoopResult:
    text: str = ""
    tool_trace: list[dict[str, Any]] = field(default_factory=list)
    usage_tokens: int = 0
    turns: int = 0


async def _audit_tool_step(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    tool_call: dict[str, Any],
    outcome: dict[str, Any],
    provider_name: str,
    agent_run_id: str | None = None,
) -> None:
    from orbiteus_core.audit import write_audit

    metadata: dict[str, Any] = {"provider": provider_name}
    if agent_run_id:
        metadata["agent_run_id"] = agent_run_id

    await write_audit(
        session,
        actor="ai",
        operation="tool_call",
        model="ai.tool",
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
        diff={
            "name": tool_call.get("name"),
            "arguments": tool_call.get("arguments"),
            "tool_call_id": tool_call.get("id"),
            "outcome_status": outcome.get("status"),
        },
        metadata=metadata,
    )


async def _execute_tool(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    name: str,
    arguments: dict[str, Any] | None,
    embed_api_key: str | None,
    embed_provider_name: str,
    delegation: DelegationContext | None = None,
) -> dict[str, Any]:
    if name == DELEGATE_TOOL_NAME:
        if delegation is None or delegation.parent_agent is None:
            return {
                "status": "error",
                "code": "ai.delegate.unavailable",
                "message": "delegate_agent is only available in agent runs",
            }
        return await execute_delegate_agent(
            session,
            ctx,
            parent_agent=delegation.parent_agent,
            parent_run_id=delegation.parent_run_id,
            current_depth=delegation.depth,
            arguments=arguments,
        )
    if name.startswith("read_"):
        return await execute_read_tool(session, ctx, tool_name=name, arguments=arguments)
    if name == "semantic_search":
        return await execute_semantic_search(
            session,
            ctx,
            arguments=arguments,
            embed_api_key=embed_api_key,
            embed_provider_name=embed_provider_name,
        )
    return await dispatch_tool_call(session, ctx, name=name, arguments=arguments)


def _append_tool_results_to_messages(
    messages: list[dict[str, Any]],
    tool_calls: list[dict[str, Any]],
    outcomes: list[dict[str, Any]],
) -> None:
    for tc, outcome in zip(tool_calls, outcomes):
        messages.append(
            {
                "role": "user",
                "content": (
                    f"Tool `{tc.get('name')}` returned: "
                    f"{json.dumps(outcome, default=str)[:8000]}"
                ),
            }
        )


async def _process_tool_calls(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    tool_calls: list[dict[str, Any]],
    turn: int,
    embed_api_key: str | None,
    embed_provider_name: str,
    provider_name: str,
    agent_run_id: str | None,
    delegation: DelegationContext | None,
    tool_trace: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    outcomes: list[dict[str, Any]] = []
    for tool_call in tool_calls:
        name = str(tool_call.get("name", ""))
        args = tool_call.get("arguments") or {}
        outcome = await _execute_tool(
            session,
            ctx,
            name=name,
            arguments=args,
            embed_api_key=embed_api_key,
            embed_provider_name=embed_provider_name,
            delegation=delegation,
        )
        outcomes.append(outcome)
        tool_trace.append(
            {
                "turn": turn + 1,
                "name": name,
                "arguments": args,
                "status": outcome.get("status"),
            }
        )
        await _audit_tool_step(
            session,
            ctx,
            tool_call=tool_call,
            outcome=outcome,
            provider_name=provider_name,
            agent_run_id=agent_run_id,
        )
    return outcomes


async def run_agent_loop(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    provider: Provider,
    api_key: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    model: str | None = None,
    max_turns: int = MAX_TURNS,
    embed_api_key: str | None = None,
    embed_provider_name: str = "openai",
    provider_name: str = "anthropic",
    agent_run_id: str | None = None,
    delegation: DelegationContext | None = None,
) -> AgentLoopResult:
    working_messages = list(messages)
    total_tokens = 0
    tool_trace: list[dict[str, Any]] = []
    final_text = ""

    for turn in range(max_turns):
        result = await provider.chat(
            api_key,
            messages=working_messages,
            tools=tools or None,
            model=model,
        )
        total_tokens += result.usage_tokens or 0
        final_text = result.text or final_text

        if not result.tool_calls:
            return AgentLoopResult(
                text=final_text,
                tool_trace=tool_trace,
                usage_tokens=total_tokens,
                turns=turn + 1,
            )

        outcomes = await _process_tool_calls(
            session,
            ctx,
            tool_calls=result.tool_calls,
            turn=turn,
            embed_api_key=embed_api_key,
            embed_provider_name=embed_provider_name,
            provider_name=provider_name,
            agent_run_id=agent_run_id,
            delegation=delegation,
            tool_trace=tool_trace,
        )
        _append_tool_results_to_messages(working_messages, result.tool_calls, outcomes)

    return AgentLoopResult(
        text=final_text,
        tool_trace=tool_trace,
        usage_tokens=total_tokens,
        turns=max_turns,
    )


async def run_agent_loop_stream(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    provider: Provider,
    api_key: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    model: str | None = None,
    max_turns: int = MAX_TURNS,
    embed_api_key: str | None = None,
    embed_provider_name: str = "openai",
    provider_name: str = "anthropic",
    agent_run_id: str | None = None,
    delegation: DelegationContext | None = None,
) -> AsyncIterator[ChatStreamEvent]:
    """Streaming multi-turn loop — yields text/tool_call/tool_result/done events."""
    working_messages = list(messages)
    total_tokens = 0
    tool_trace: list[dict[str, Any]] = []
    final_text = ""

    for turn in range(max_turns):
        turn_text = ""
        turn_tool_calls: list[dict[str, Any]] = []
        turn_tokens = 0
        finish_reason = "stop"

        try:
            async for event in provider.chat_stream(
                api_key,
                messages=working_messages,
                tools=tools or None,
                model=model,
            ):
                if event.kind == "text":
                    turn_text += event.data.get("delta", "")
                    yield event
                elif event.kind == "tool_call":
                    turn_tool_calls.append(event.data)
                    yield event
                elif event.kind == "done":
                    turn_tokens = int(event.data.get("usage_tokens", 0) or 0)
                    finish_reason = str(event.data.get("finish_reason") or "stop")
        except ProviderError:
            raise

        total_tokens += turn_tokens
        final_text = turn_text or final_text

        if not turn_tool_calls:
            yield ChatStreamEvent(
                "done",
                {
                    "usage_tokens": total_tokens,
                    "finish_reason": finish_reason,
                    "turns": turn + 1,
                    "tool_trace": tool_trace,
                    "text": turn_text,
                },
            )
            return

        outcomes = await _process_tool_calls(
            session,
            ctx,
            tool_calls=turn_tool_calls,
            turn=turn,
            embed_api_key=embed_api_key,
            embed_provider_name=embed_provider_name,
            provider_name=provider_name,
            agent_run_id=agent_run_id,
            delegation=delegation,
            tool_trace=tool_trace,
        )
        for tc, outcome in zip(turn_tool_calls, outcomes):
            yield ChatStreamEvent(
                "tool_result",
                {
                    "tool_call_id": tc.get("id"),
                    "name": tc.get("name"),
                    **outcome,
                },
            )
        _append_tool_results_to_messages(working_messages, turn_tool_calls, outcomes)

    yield ChatStreamEvent(
        "done",
        {
            "usage_tokens": total_tokens,
            "finish_reason": "max_turns",
            "turns": max_turns,
            "tool_trace": tool_trace,
            "text": final_text,
        },
    )


async def apply_usage_budget(tenant_id, tokens: int) -> None:
    if tokens and tenant_id:
        await increment(tenant_id, tokens)
