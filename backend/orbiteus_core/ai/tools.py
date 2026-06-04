"""Build the tool list for an AI chat session.

Three sources (docs/15-ai-layer.md):
  1. `Action` registry — callable navigations / mutations.
  2. `QueryTool` per accessible model — read via BaseRepository.
  3. `semantic_search` — pgvector similarity (when embeddings exist).

Tools returned here are provider-agnostic: a list of `{name, description,
parameters}` dicts. Each provider adapter (anthropic / openai / gemini / ollama)
shapes them to its own function-calling format.
"""
from __future__ import annotations

import json
from typing import Any

from orbiteus_core.ai.config import ai_registry
from orbiteus_core.ai.registry import action_registry
from orbiteus_core.context import RequestContext


def _query_tool_for(model: str) -> dict[str, Any]:
    safe_name = model.replace(".", "_")
    return {
        "name": f"read_{safe_name}",
        "description": (
            f"Read records from the {model} model. Returns a paginated list. "
            "RBAC and tenant isolation are enforced server-side."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "filter": {"type": "object", "description": "Optional Odoo-style domain dict"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 25},
            },
            "required": [],
        },
    }


def _action_tool_for(action) -> dict[str, Any]:
    """Build a provider-agnostic tool schema for one Action.

    Honours the action's `parameters_schema` when present (canonical
    way for an action to advertise the args its dispatcher handler
    expects). Falls back to an open `id` field so legacy actions
    keep a working — if minimal — tool surface.
    """
    schema = action.parameters_schema or {
        "type": "object",
        "properties": {
            "id": {"type": "string", "description": "Optional record id"},
        },
        "required": [],
    }
    return {
        "name": action.id.replace(".", "_"),
        "description": action.description or action.label,
        "parameters": schema,
    }


def build_tools(ctx: RequestContext, scope: str = "all") -> list[dict[str, Any]]:
    """Build tool list scoped to the user's RBAC and the registered AI configs.

    `scope` filters by module when set to `module:<name>`.
    """
    tools: list[dict[str, Any]] = []
    module_filter: str | None = None
    if scope.startswith("module:"):
        module_filter = scope.split(":", 1)[1]

    accessible = ai_registry.accessible_models()
    callable_actions = ai_registry.callable_actions()

    if module_filter:
        prefix = f"{module_filter}."
        accessible = {m for m in accessible if m.startswith(prefix)}
        callable_actions = {a for a in callable_actions if a.startswith(prefix)}

    # 1) Per-model read tools.
    for model in sorted(accessible):
        tools.append(_query_tool_for(model))

    # 2) Action tools (filtered by RBAC).
    actions = action_registry.get_all()
    for action in actions:
        if action.id not in callable_actions:
            continue
        tools.append(_action_tool_for(action))

    # 3) Semantic search if any module declares embeddings.
    embed_models = ai_registry.embed_models()
    if module_filter:
        prefix = f"{module_filter}."
        embed_models = {m for m in embed_models if m.startswith(prefix)}

    if embed_models:
        tools.append(
            {
                "name": "semantic_search",
                "description": (
                    "Semantic search across embedded records the caller can read."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "model": {"type": "string"},
                        "query": {"type": "string"},
                        "top_k": {"type": "integer", "minimum": 1, "maximum": 50, "default": 8},
                    },
                    "required": ["model", "query"],
                },
            }
        )

    return tools


def build_tools_for_agent(
    ctx: RequestContext,
    *,
    module_scope: str,
    allowed_models: list[str],
    allowed_actions: list[str],
    can_delegate: bool = False,
) -> list[dict[str, Any]]:
    """Intersect module AIModuleConfig with agent allow-lists."""
    from orbiteus_core.ai.delegation import delegate_tool_schema

    scope = "all" if module_scope in ("", "*") else f"module:{module_scope}"
    module_filter = None if module_scope in ("", "*") else module_scope
    all_tools = build_tools(ctx, scope=scope)
    allowed_model_set = set(allowed_models or [])
    allowed_action_set = set(allowed_actions or [])

    if not allowed_model_set and not allowed_action_set:
        filtered = list(all_tools)
    else:
        filtered: list[dict[str, Any]] = []
        for tool in all_tools:
            name = tool["name"]
            if name == "semantic_search":
                embed = ai_registry.embed_models()
                if module_filter:
                    embed = {m for m in embed if m.startswith(f"{module_filter}.")}
                if allowed_model_set:
                    embed = embed & allowed_model_set
                if embed:
                    filtered.append(tool)
                continue
            if name.startswith("read_"):
                from orbiteus_core.ai.query_executor import resolve_model_from_read_tool
                model = resolve_model_from_read_tool(name)
                if allowed_model_set and model not in allowed_model_set:
                    continue
                filtered.append(tool)
                continue
            action_id = name.replace("_", ".")
            if allowed_action_set and action_id not in allowed_action_set:
                continue
            filtered.append(tool)

    if can_delegate:
        filtered.append(delegate_tool_schema())
    return filtered
