"""AI tool-call dispatcher (DoD §8.10).

The chat layer (`orbiteus_core/ai/router.py:_chat_oneshot`) receives a
list of `tool_calls` from the provider. Each `tool_call` carries:

  {"id": "<tool_call_id>", "name": "<tool_name>", "arguments": {...}}

The provider gives us "the AI **wants** to invoke X with these args".
That request travels through this dispatcher to get **executed** —
read tools route to repository searches, action tools route to the
Python handler the module registered, semantic search routes to
pgvector. Every path enforces the caller's RBAC: there is **no**
elevated AI context, ever.

Module integration
------------------
A module exposes a callable handler for an Action by calling
`register_handler` at import time, typically from `<module>/ai.py`:

    from orbiteus_core.ai.dispatcher import register_handler
    register_handler("crm.lead.move_stage", crm_lead_move_stage_handler)

The handler signature is:

    async def handler(
        session: AsyncSession,
        ctx: RequestContext,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        ...

Return value is JSON-serialisable; the chat endpoint passes it back
to the AI on the next turn (when we wire multi-turn — for v1.0 we
expose it as `tool_results` on the response so the test suite and
frontend can read it).
"""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext

logger = logging.getLogger(__name__)


HandlerSig = Callable[
    [AsyncSession, RequestContext, dict[str, Any]],
    Awaitable[dict[str, Any]],
]


_HANDLERS: dict[str, HandlerSig] = {}


def register_handler(action_id: str, handler: HandlerSig) -> None:
    """Register an executor for an Action id (e.g. "crm.lead.move_stage").

    Idempotent: re-registering with the same id replaces the previous
    handler. We log a warning on replacement so a stray import order
    surfaces explicitly.
    """
    if action_id in _HANDLERS:
        logger.warning("ai.dispatcher.handler_replaced action=%s", action_id)
    _HANDLERS[action_id] = handler


def is_registered(action_id: str) -> bool:
    return action_id in _HANDLERS


def list_registered() -> list[str]:
    return sorted(_HANDLERS.keys())


def _action_id_from_tool_name(name: str) -> str:
    """Reverse the `_action_tool_for` dotted-to-underscore conversion.

    The first underscore that separates `<module>_<rest>` becomes a
    dot; the rest stay literal so a model name with a hyphen
    survives. For canonical "crm.lead.move_stage" the tool name is
    "crm_lead_move_stage" — we restore the dots greedily.
    """
    return name.replace("_", ".")


async def dispatch_tool_call(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    name: str,
    arguments: dict[str, Any] | None,
) -> dict[str, Any]:
    """Execute one provider-issued tool call.

    Returns one of:
      {"status": "ok",      "result": {...}}
      {"status": "skipped", "reason": "<read tool / semantic search / unknown>"}
      {"status": "error",   "code": "...",  "message": "..."}

    Errors do NOT raise — the chat path persists every outcome (good
    or bad) in the audit log, and we don't want a transient handler
    error to turn the whole `POST /api/ai/chat` into a 500.
    """
    args = arguments or {}

    if name.startswith("read_"):
        from orbiteus_core.ai.query_executor import execute_read_tool
        return await execute_read_tool(session, ctx, tool_name=name, arguments=args)

    if name == "semantic_search":
        from orbiteus_core.ai.query_executor import execute_semantic_search
        return await execute_semantic_search(session, ctx, arguments=args)

    action_id = _action_id_from_tool_name(name)
    handler = _HANDLERS.get(action_id)

    # Try a few alternate spellings before giving up — the underscore-
    # to-dot conversion is greedy, so an action id with a literal
    # underscore (rare) would slip through. We prefer the longest
    # registered prefix.
    if handler is None:
        for registered in sorted(_HANDLERS.keys(), key=len, reverse=True):
            if registered.replace(".", "_") == name:
                handler = _HANDLERS[registered]
                action_id = registered
                break

    if handler is None:
        logger.info("ai.dispatcher.no_handler tool=%s action_id=%s", name, action_id)
        return {
            "status": "error",
            "code": "ai.dispatcher.no_handler",
            "message": f"No registered handler for action {action_id!r} "
                        f"(tool name {name!r}).",
        }

    try:
        result = await handler(session, ctx, args)
    except Exception as exc:  # noqa: BLE001
        logger.exception("ai.dispatcher.handler_failed action=%s", action_id)
        return {
            "status": "error",
            "code": "ai.dispatcher.handler_failed",
            "message": str(exc)[:500],
        }

    return {"status": "ok", "action_id": action_id, "result": result}
