"""HTTP routes for the AI layer.

- /api/ai/actions       — Command Palette resolver (RapidFuzz, no LLM)
- /api/ai/credentials   — BYOK CRUD (POST/GET/DELETE)
- /api/ai/chat          — non-streaming chat (provider tool calling)
- /api/ai/dashboard     — NL → aggregate query → chart spec
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.ai.budget import has_budget, increment
from orbiteus_core.ai.config import ai_registry
from orbiteus_core.ai.keys import fetch_credential, store_credential
from orbiteus_core.ai.providers import PROVIDER_NAMES, ProviderError, get_provider
from orbiteus_core.exceptions import NotFound
from orbiteus_core.ai.redaction import redact_payload
from orbiteus_core.ai.resolver import resolve as resolve_actions
from orbiteus_core.ai.tools import build_tools
from orbiteus_core.context import RequestContext
from orbiteus_core.db import get_session
from orbiteus_core.security.middleware import (
    get_current_context,
    require_auth,
    require_superadmin,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai"])


# ---------------------------------------------------------------------------
# Command Palette resolver (already used by admin UI, kept for back-compat).
# ---------------------------------------------------------------------------

@router.get("/actions")
async def get_actions(
    q: str = Query(default=""),
    limit: int = Query(default=8, le=20, ge=1),
    ctx: RequestContext = Depends(get_current_context),
) -> dict:
    return {"items": resolve_actions(q, ctx, limit=limit)}


# ---------------------------------------------------------------------------
# BYOK credentials CRUD
# ---------------------------------------------------------------------------

@router.post("/credentials")
async def upsert_credential(
    body: dict = Body(...),
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Store or update a provider credential for the caller's tenant.

    Body: `{ "provider": "anthropic|openai|ollama|gemini",
             "secret": "<api-key>",
             "model_default": "claude-3-5-sonnet-latest",
             "monthly_token_budget": 1000000 }`
    """
    provider = (body.get("provider") or "").lower()
    secret = body.get("secret")
    if provider not in PROVIDER_NAMES:
        allowed = "|".join(sorted(PROVIDER_NAMES))
        raise HTTPException(status_code=400, detail=f"provider must be one of {allowed}")
    if not secret:
        raise HTTPException(status_code=400, detail="secret is required")
    if ctx.tenant_id is None:
        raise HTTPException(status_code=400, detail="tenant context required")

    # Provider ping with the supplied secret; fail-fast on bad keys.
    p = get_provider(provider)
    ok = await p.ping(secret)
    if not ok:
        raise HTTPException(status_code=400, detail="provider rejected the supplied credential")

    cred_id = await store_credential(
        session,
        tenant_id=ctx.tenant_id,
        provider=provider,
        secret=secret,
        model_default=body.get("model_default"),
        monthly_token_budget=body.get("monthly_token_budget"),
    )
    await session.commit()
    return {"id": str(cred_id), "provider": provider}


@router.get("/credentials")
async def list_credentials(
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """List configured providers for the tenant — never returns secrets."""
    from sqlalchemy import select

    from modules.base.model.mapping import base_ai_credentials_table as t

    if ctx.tenant_id is None:
        return {"items": []}

    rows = (
        await session.execute(
            select(
                t.c.id,
                t.c.provider,
                t.c.model_default,
                t.c.is_active,
                t.c.monthly_token_budget,
                t.c.usage_tokens,
            ).where(t.c.tenant_id == ctx.tenant_id)
        )
    ).all()
    return {
        "items": [
            {
                "id": str(r[0]),
                "provider": r[1],
                "model_default": r[2],
                "is_active": r[3],
                "monthly_token_budget": r[4],
                "usage_tokens": r[5],
            }
            for r in rows
        ]
    }


@router.delete("/credentials/{provider}")
async def delete_credential(
    provider: str,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    from sqlalchemy import delete

    from modules.base.model.mapping import base_ai_credentials_table as t

    if ctx.tenant_id is None:
        raise HTTPException(status_code=400, detail="tenant context required")
    await session.execute(
        delete(t).where(t.c.tenant_id == ctx.tenant_id, t.c.provider == provider.lower())
    )
    await session.commit()
    return {"deleted": provider}


# ---------------------------------------------------------------------------
# Chat — non-streaming + streaming (DoD §8.8)
# ---------------------------------------------------------------------------

async def _resolve_chat_inputs(
    body: dict,
    session: AsyncSession,
    ctx: RequestContext,
) -> tuple[Any, dict, list, list, str]:
    """Shared validation for both chat endpoints.

    Returns ``(provider, credential, messages, tools, provider_name)``.
    Raises ``HTTPException`` on missing tenant, missing credential, or
    exhausted budget — same shape both endpoints used to encode inline.
    """
    if ctx.tenant_id is None:
        raise HTTPException(status_code=400, detail="tenant context required")

    provider_name = (body.get("provider") or "anthropic").lower()
    cred = await fetch_credential(session, tenant_id=ctx.tenant_id, provider=provider_name)
    if cred is None:
        raise HTTPException(
            status_code=412,
            detail={
                "code": "ai.no_credential",
                "message": f"No active {provider_name} credential for this tenant. "
                           "POST /api/ai/credentials first.",
            },
        )

    if not await has_budget(ctx.tenant_id, cred.get("monthly_token_budget")):
        raise HTTPException(
            status_code=429,
            detail={"code": "ai.budget_exceeded", "message": "Monthly AI token budget exceeded"},
            headers={"Retry-After": "3600"},
        )

    messages = redact_payload(body.get("messages") or [])
    tools = build_tools(ctx, scope=body.get("scope") or "all")
    p = get_provider(provider_name)
    return p, cred, messages, tools, provider_name


async def _audit_tool_calls(
    session: AsyncSession,
    ctx: RequestContext,
    tool_calls: list[dict[str, Any]],
    *,
    provider_name: str,
    body: dict,
    cred: dict,
    usage_tokens: int,
) -> None:
    """Append one `actor=ai, operation=tool_call` row per invocation."""
    if not tool_calls:
        return
    from orbiteus_core.audit import write_audit

    for tool_call in tool_calls:
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
            },
            metadata={
                "provider": provider_name,
                "ai_model": body.get("model") or cred.get("model_default"),
                "scope": body.get("scope") or "all",
                "usage_tokens": usage_tokens,
            },
        )
    await session.commit()


@router.post("/chat")
async def chat(
    body: dict = Body(...),
    stream: int = Query(0, description="Pass 1 for SSE streaming response"),
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> Any:
    """Chat with the tenant's configured provider.

    Body: `{ "messages": [...], "scope": "module:crm" | "global", "model": optional }`

    With ``?stream=1`` the response is `text/event-stream` (SSE):

      event: text          → {"delta": "..."}
      event: tool_call     → {"id": ..., "name": ..., "arguments": {...}}
      event: done          → {"usage_tokens": int, "finish_reason": "..."}

    Otherwise it's a regular JSON response — see schema below.
    """
    if stream:
        return await _chat_stream(body, session, ctx)
    return await _chat_oneshot(body, session, ctx)


async def _chat_oneshot(
    body: dict,
    session: AsyncSession,
    ctx: RequestContext,
) -> dict:
    """Non-streaming chat with multi-turn tool execution via `AgentLoop`."""
    from orbiteus_core.ai.loop import apply_usage_budget, run_agent_loop
    from orbiteus_core.ai.keys import fetch_credential as _fetch_cred

    p, cred, messages, tools, provider_name = await _resolve_chat_inputs(body, session, ctx)

    embed_cred = await _fetch_cred(session, tenant_id=ctx.tenant_id, provider="openai")
    embed_key = embed_cred["secret"] if embed_cred else None

    try:
        loop_result = await run_agent_loop(
            session,
            ctx,
            provider=p,
            api_key=cred["secret"],
            messages=messages,
            tools=tools,
            model=body.get("model") or cred.get("model_default"),
            embed_api_key=embed_key,
            provider_name=provider_name,
        )
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if loop_result.usage_tokens:
        await apply_usage_budget(ctx.tenant_id, loop_result.usage_tokens)

    return {
        "text": loop_result.text,
        "tool_trace": loop_result.tool_trace,
        "usage_tokens": loop_result.usage_tokens,
        "turns": loop_result.turns,
        "finish_reason": "stop",
    }


async def _chat_stream(
    body: dict,
    session: AsyncSession,
    ctx: RequestContext,
):
    """Streaming chat with multi-turn tool execution via `run_agent_loop_stream`."""
    import json as _json

    from fastapi.responses import StreamingResponse

    from orbiteus_core.ai.keys import fetch_credential as _fetch_cred
    from orbiteus_core.ai.loop import apply_usage_budget, run_agent_loop_stream

    p, cred, messages, tools, provider_name = await _resolve_chat_inputs(body, session, ctx)
    embed_cred = await _fetch_cred(session, tenant_id=ctx.tenant_id, provider="openai")
    embed_key = embed_cred["secret"] if embed_cred else None

    async def _sse() -> Any:
        usage_tokens = 0
        tool_trace: list[dict[str, Any]] = []
        try:
            async for event in run_agent_loop_stream(
                session,
                ctx,
                provider=p,
                api_key=cred["secret"],
                messages=messages,
                tools=tools,
                model=body.get("model") or cred.get("model_default"),
                embed_api_key=embed_key,
                provider_name=provider_name,
            ):
                yield (
                    f"event: {event.kind}\n"
                    f"data: {_json.dumps(event.data)}\n\n"
                ).encode("utf-8")
                if event.kind == "done":
                    usage_tokens = int(event.data.get("usage_tokens", 0) or 0)
                    tool_trace = list(event.data.get("tool_trace") or [])
        except ProviderError as exc:
            yield (
                "event: error\n"
                f"data: {_json.dumps({'detail': str(exc)})}\n\n"
            ).encode("utf-8")
            return
        except Exception as exc:  # noqa: BLE001
            logger.exception("ai.chat_stream.failed")
            yield (
                "event: error\n"
                f"data: {_json.dumps({'detail': 'internal error', 'kind': type(exc).__name__})}\n\n"
            ).encode("utf-8")
            return

        if usage_tokens:
            try:
                await apply_usage_budget(ctx.tenant_id, usage_tokens)
            except Exception:  # noqa: BLE001
                logger.exception("ai.chat_stream.budget_increment_failed")

        tool_calls = [
            step for step in tool_trace
            if step.get("name")
        ]
        try:
            await _audit_tool_calls(
                session,
                ctx,
                [{"id": f"stream-{i}", "name": s.get("name"), "arguments": s.get("arguments", {})}
                 for i, s in enumerate(tool_calls)],
                provider_name=provider_name,
                body=body,
                cred=cred,
                usage_tokens=usage_tokens,
            )
        except Exception:  # noqa: BLE001
            logger.exception("ai.chat_stream.audit_failed")

    return StreamingResponse(_sse(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Agent runs (ADR-0018)
# ---------------------------------------------------------------------------

@router.post("/runs")
async def start_agent_run(
    body: dict = Body(...),
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Start an agent run.

    Body: `{ "agent_id": "<uuid>", "prompt": "...", "async": false }`

    When `async` is true the run is enqueued to Celery and returns
    immediately with `status=pending`.
    """
    from orbiteus_core.ai.executor import create_and_execute_run, load_agent
    from orbiteus_core.exceptions import ValidationError as DomainValidationError

    agent_id_raw = body.get("agent_id")
    prompt = (body.get("prompt") or "").strip()
    is_async = bool(body.get("async"))

    if not agent_id_raw:
        raise HTTPException(status_code=400, detail="agent_id is required")
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    try:
        agent_id = uuid.UUID(str(agent_id_raw))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid agent_id") from exc

    try:
        await load_agent(session, ctx, agent_id)
    except NotFound:
        raise HTTPException(status_code=404, detail="Agent not found")

    parent_run_id_raw = body.get("parent_run_id")
    parent_run_id = None
    if parent_run_id_raw:
        try:
            parent_run_id = uuid.UUID(str(parent_run_id_raw))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid parent_run_id") from exc

    if is_async:
        from modules.base.controller.repositories import AgentRunRepository

        run_repo = AgentRunRepository(session, ctx)
        run = await run_repo.create(
            {
                "agent_id": agent_id,
                "parent_run_id": parent_run_id,
                "depth": int(body.get("depth") or 0),
                "triggered_by_user_id": ctx.user_id,
                "input_prompt": prompt,
                "status": "pending",
            }
        )
        await session.commit()
        from tasks.ai_tasks import run_agent_run

        run_agent_run.delay(
            str(run.id),
            str(ctx.tenant_id),
            str(ctx.user_id) if ctx.user_id else "",
            list(ctx.roles),
            bool(ctx.is_superadmin),
        )
        return {
            "id": str(run.id),
            "agent_id": str(agent_id),
            "status": "pending",
            "async": True,
        }

    try:
        if parent_run_id:
            from orbiteus_core.ai.executor import create_and_execute_run

            result = await create_and_execute_run(
                session,
                ctx,
                agent_id=agent_id,
                prompt=prompt,
                parent_run_id=parent_run_id,
                depth=int(body.get("depth") or 0),
            )
        else:
            result = await create_and_execute_run(
                session, ctx, agent_id=agent_id, prompt=prompt,
            )
    except DomainValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "id": result.get("run_id"),
        "agent_id": result.get("agent_id"),
        "status": "completed",
        "text": result.get("text"),
        "tool_trace": result.get("tool_trace"),
        "usage_tokens": result.get("usage_tokens"),
        "turns": result.get("turns"),
    }


@router.get("/runs/{run_id}")
async def get_agent_run(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    from modules.base.controller.repositories import AgentRunRepository
    from modules.base.model.schemas import AgentRunRead

    repo = AgentRunRepository(session, ctx)
    try:
        run = await repo.get(run_id)
    except NotFound:
        raise HTTPException(status_code=404, detail="Run not found")

    payload = AgentRunRead.model_validate(run, from_attributes=True).model_dump(mode="json")
    return payload


# ---------------------------------------------------------------------------
# Dashboard generator (NL → aggregate spec)
# ---------------------------------------------------------------------------

_DASHBOARD_SYSTEM_PROMPT = """You are a data-aware assistant that turns
natural-language requests into a single JSON object describing an
aggregate query against the Orbiteus framework.

You MUST reply with ONE valid JSON object — no prose, no code fence,
no commentary — matching this schema exactly:

  {
    "model":    "<dotted_model_name from the allowed list>",
    "group_by": "<field name on that model>",
    "op":       "count" | "sum" | "avg" | "min" | "max",
    "measure":  "<field name>" | null,
    "title":    "<short, human-readable chart title>"
  }

Rules:
  * `op="count"` MUST set `measure` to null.
  * `op` ∈ {sum, avg, min, max} MUST set `measure` to a numeric field
    (typically *_revenue, *_amount, *_total, *_qty).
  * Pick the simplest possible aggregation that answers the request.
  * If the request is ambiguous, prefer `op="count"` grouped by the
    most discriminating categorical field (`stage_id`, `status`,
    `kind`, `team_id`, …).

Allowed models for this tenant:
{allowed_models}
"""


_DASHBOARD_RESPONSE_SHAPE = {
    "model", "group_by", "op", "measure", "title",
}


@router.post("/dashboard")
async def dashboard(
    body: dict = Body(...),
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Natural-language → aggregate spec → recharts payload.

    Flow:
      1. Resolve the tenant's AI provider + budget (same path as
         `/api/ai/chat`).
      2. Ask the model — with a tightly-shaped system prompt — to
         return a JSON aggregate spec.
      3. Hand the spec to `_run_aggregate(...)` which routes through
         the same `apply_record_rules` path as
         `GET /api/base/aggregate` (zero RBAC bypass).
      4. Return `{title, chart_type, x_axis, y_axis, data, spec}` —
         the exact shape `<AIDashboard>` consumes.

    Errors:
      * 412 — no AI credential / tenant context missing.
      * 422 — the model returned something we can't parse / cite.
      * 502 — provider call failed.
    """
    import json as _json

    if ctx.tenant_id is None:
        raise HTTPException(status_code=400, detail="tenant context required")

    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    p, cred, _msgs, _tools, _provider_name = await _resolve_chat_inputs(
        {"messages": [], "scope": body.get("scope") or "all"}, session, ctx,
    )

    accessible = ai_registry.accessible_models() or []
    if not accessible:
        raise HTTPException(
            status_code=412, detail="No AI module configured for this tenant",
        )

    system = _DASHBOARD_SYSTEM_PROMPT.format(
        allowed_models="\n".join(f"  - {m}" for m in accessible),
    )

    try:
        result = await p.chat(
            cred["secret"],
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            tools=None,
            model=body.get("model") or cred.get("model_default"),
            max_tokens=512,
            temperature=0.1,
        )
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    if result.usage_tokens:
        await increment(ctx.tenant_id, result.usage_tokens)

    spec = _parse_dashboard_spec(result.text or "")

    if spec["model"] not in accessible:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "ai.dashboard.model_not_allowed",
                "message": (
                    f"Model {spec['model']!r} is not in the AI scope for "
                    "this tenant; pick a model from the accessible list."
                ),
            },
        )

    if not await _check_can_read(ctx, spec["model"]):
        raise HTTPException(status_code=403, detail="Forbidden")

    data = await _run_aggregate(session, ctx, spec)

    return {
        "title": spec["title"] or prompt[:80] or "AI dashboard",
        "chart_type": "bar",
        # Two-key shape that matches the `<AIDashboard>` recharts
        # caller — `category` for the X axis label, `value` for the
        # bar height.
        "x_axis": "category",
        "y_axis": "value",
        "data": data,
        "spec": spec,
        "usage_tokens": result.usage_tokens,
    }


def _parse_dashboard_spec(raw: str) -> dict[str, Any]:
    """Coerce the model's reply to the dashboard JSON shape.

    Tolerates a stray code fence around the JSON. Anything we can't
    parse turns into a 422 — the contract is "valid JSON or nothing".
    """
    import json as _json
    import re

    text = raw.strip()
    # Strip a markdown ```json ...``` fence if the model insisted on
    # wrapping the payload.
    fence_match = re.search(r"```(?:json)?\s*(\{[\s\S]+?\})\s*```", text)
    if fence_match:
        text = fence_match.group(1)
    else:
        # Fallback: pick the first `{...}` block.
        brace_match = re.search(r"\{[\s\S]+\}", text)
        if brace_match:
            text = brace_match.group(0)

    try:
        parsed = _json.loads(text)
    except _json.JSONDecodeError:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "ai.dashboard.invalid_json",
                "raw": raw[:500],
            },
        )

    missing = _DASHBOARD_RESPONSE_SHAPE - set(parsed)
    if missing:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "ai.dashboard.missing_fields",
                "missing": sorted(missing),
                "got": parsed,
            },
        )

    op = parsed.get("op")
    if op not in {"count", "sum", "avg", "min", "max"}:
        raise HTTPException(
            status_code=422,
            detail={"code": "ai.dashboard.bad_op", "got": op},
        )
    if op != "count" and not parsed.get("measure"):
        raise HTTPException(
            status_code=422,
            detail={"code": "ai.dashboard.missing_measure", "op": op},
        )
    return parsed


async def _check_can_read(ctx: RequestContext, model: str) -> bool:
    from orbiteus_core.security.rbac import check_model_access

    return await check_model_access(ctx, model, "read")


async def _run_aggregate(
    session: AsyncSession,
    ctx: RequestContext,
    spec: dict[str, Any],
) -> list[dict[str, Any]]:
    """Run the aggregate query the model asked for. Reuses the exact
    same RBAC + tenant-filter path as `/api/base/aggregate`."""
    from sqlalchemy import func, select

    from orbiteus_core.auto_router import _model_registry
    from orbiteus_core.security.rbac import apply_record_rules

    entry = _model_registry.get(spec["model"])
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"Model {spec['model']!r} is not registered.",
        )

    table = entry["table"]
    group_col = table.c.get(spec["group_by"])
    if group_col is None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "ai.dashboard.bad_group_by",
                "model": spec["model"],
                "field": spec["group_by"],
            },
        )

    op = spec["op"]
    if op == "count":
        agg = func.count(table.c.id)
    else:
        measure_col = table.c.get(spec["measure"])
        if measure_col is None:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "ai.dashboard.bad_measure",
                    "model": spec["model"],
                    "field": spec["measure"],
                },
            )
        agg = getattr(func, op)(measure_col)

    stmt = select(group_col, agg).group_by(group_col)
    if (
        "tenant_id" in table.c
        and ctx.tenant_id is not None
        and not ctx.is_superadmin
    ):
        stmt = stmt.where(table.c.tenant_id == ctx.tenant_id)
    stmt = apply_record_rules(stmt, table, ctx, spec["model"])

    rows = (await session.execute(stmt)).all()

    def _coerce(v: Any) -> Any:
        if v is None:
            return None
        if hasattr(v, "as_tuple"):  # Decimal duck-typing
            return float(v)
        return v

    return [
        {"category": str(_coerce(g)) if g is not None else "—",
         "value": _coerce(v)}
        for g, v in rows
    ]
