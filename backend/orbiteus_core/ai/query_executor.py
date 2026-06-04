"""Execute read_* AI tools via BaseRepository (DoD §8.10)."""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.ai.config import ai_registry
from orbiteus_core.auto_router import _model_registry
from orbiteus_core.context import RequestContext
from orbiteus_core.exceptions import AccessDenied, NotFound

logger = logging.getLogger(__name__)


def resolve_model_from_read_tool(tool_name: str) -> str | None:
    """Map `read_crm_lead` → `crm.lead` using registered accessible models."""
    if not tool_name.startswith("read_"):
        return None
    suffix = tool_name[len("read_") :]
    candidates = sorted(ai_registry.accessible_models(), key=len, reverse=True)
    for model in candidates:
        if model.replace(".", "_") == suffix:
            return model
    return None


def normalize_domain(raw: Any) -> list[tuple[str, str, Any]]:
    """Coerce filter argument to Odoo-style domain tuples."""
    if raw is None:
        return []
    if isinstance(raw, list):
        out: list[tuple[str, str, Any]] = []
        for item in raw:
            if isinstance(item, (list, tuple)) and len(item) == 3:
                out.append((str(item[0]), str(item[1]), item[2]))
        return out
    if isinstance(raw, dict):
        return [(str(k), "=", v) for k, v in raw.items()]
    return []


async def execute_read_tool(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    tool_name: str,
    arguments: dict[str, Any] | None,
) -> dict[str, Any]:
    """Run a read_* tool against the model registry."""
    model = resolve_model_from_read_tool(tool_name)
    if model is None:
        return {
            "status": "error",
            "code": "ai.read.unknown_model",
            "message": f"Cannot resolve model for tool {tool_name!r}",
        }

    if model not in ai_registry.accessible_models():
        return {
            "status": "error",
            "code": "ai.read.model_not_declared",
            "message": f"Model {model!r} is not exposed by any module ai.py",
        }

    entry = _model_registry.get(model)
    if entry is None:
        return {
            "status": "error",
            "code": "ai.read.model_not_registered",
            "message": f"Model {model!r} is not registered for auto-CRUD",
        }

    args = arguments or {}
    limit = min(max(int(args.get("limit", 25)), 1), 200)
    domain = normalize_domain(args.get("filter"))

    repo_class = entry["repository_class"]
    read_schema = entry["read_schema"]
    repo = repo_class(session, ctx)

    try:
        items, total = await repo.search(domain=domain, limit=limit)
    except AccessDenied as exc:
        return {"status": "error", "code": "ai.read.forbidden", "message": str(exc)}
    except Exception as exc:  # noqa: BLE001
        logger.exception("ai.read_tool.failed model=%s", model)
        return {
            "status": "error",
            "code": "ai.read.failed",
            "message": str(exc)[:500],
        }

    serialized = [
        read_schema.model_validate(obj, from_attributes=True).model_dump(mode="json")
        for obj in items
    ]
    return {
        "status": "ok",
        "model": model,
        "total": total,
        "count": len(serialized),
        "items": serialized,
    }


async def execute_semantic_search(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    arguments: dict[str, Any] | None,
    embed_api_key: str | None = None,
    embed_provider_name: str = "openai",
) -> dict[str, Any]:
    """Best-effort semantic search over `base_embeddings`.

    Returns an empty item list when no embeddings are indexed or when
    embedding the query fails (e.g. no OpenAI key for Anthropic-only tenants).
    """
    args = arguments or {}
    model = str(args.get("model") or "")
    query = str(args.get("query") or "").strip()
    top_k = min(max(int(args.get("top_k", 8)), 1), 50)

    if not model or not query:
        return {
            "status": "error",
            "code": "ai.semantic.bad_args",
            "message": "model and query are required",
        }

    if model not in ai_registry.embed_models():
        return {
            "status": "error",
            "code": "ai.semantic.model_not_embedded",
            "message": f"Model {model!r} is not listed in embed_models",
        }

    if ctx.tenant_id is None:
        return {"status": "error", "code": "ai.semantic.no_tenant", "message": "tenant required"}

    if not embed_api_key:
        return {
            "status": "ok",
            "model": model,
            "items": [],
            "message": "no embedding provider credential; index empty",
        }

    try:
        from orbiteus_core.ai.providers import get_provider

        provider = get_provider(embed_provider_name)
        vectors = await provider.embed(embed_api_key, texts=[query])
        if not vectors:
            return {"status": "ok", "model": model, "items": []}
        query_vec = vectors[0]
    except Exception as exc:  # noqa: BLE001
        logger.warning("ai.semantic.embed_failed", extra={"error": str(exc)[:200]})
        return {"status": "ok", "model": model, "items": [], "message": "embed failed"}

    # pgvector similarity query — raw SQL for cosine distance.
    from sqlalchemy import text

    vec_literal = "[" + ",".join(str(float(x)) for x in query_vec) + "]"
    sql = text(
        """
        SELECT record_id, model,
               (vector <=> CAST(:qvec AS vector)) AS distance
        FROM base_embeddings
        WHERE tenant_id = CAST(:tenant_id AS uuid)
          AND model = :model
          AND vector IS NOT NULL
        ORDER BY vector <=> CAST(:qvec AS vector)
        LIMIT :top_k
        """
    )
    try:
        rows = (
            await session.execute(
                sql,
                {
                    "qvec": vec_literal,
                    "tenant_id": str(ctx.tenant_id),
                    "model": model,
                    "top_k": top_k,
                },
            )
        ).all()
    except Exception as exc:  # noqa: BLE001
        logger.warning("ai.semantic.query_failed", extra={"error": str(exc)[:200]})
        return {"status": "ok", "model": model, "items": [], "message": "vector query failed"}

    entry = _model_registry.get(model)
    if entry is None:
        return {"status": "ok", "model": model, "items": []}

    repo_class = entry["repository_class"]
    read_schema = entry["read_schema"]
    repo = repo_class(session, ctx)
    items: list[dict[str, Any]] = []

    for record_id, row_model, distance in rows:
        try:
            obj = await repo.get(record_id)
        except (NotFound, AccessDenied):
            continue
        payload = read_schema.model_validate(obj, from_attributes=True).model_dump(mode="json")
        payload["_semantic_distance"] = float(distance)
        items.append(payload)

    return {"status": "ok", "model": model, "count": len(items), "items": items}
