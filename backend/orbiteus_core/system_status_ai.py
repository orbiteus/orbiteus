"""AI layer component probes for Technical → System status."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from sqlalchemy import text

from orbiteus_core.system_status import ComponentStatus, _component

logger = logging.getLogger(__name__)

_AI_GROUP = "ai"


def _check_ai_module_config() -> dict[str, Any]:
    from orbiteus_core.ai.config import ai_registry

    configs = ai_registry.all()
    enabled = [name for name, cfg in configs.items() if cfg.enabled]
    models = sorted(ai_registry.accessible_models())
    if not enabled:
        return _component(
            id="ai_module_config",
            name="Module AI config",
            group=_AI_GROUP,
            status="unknown",
            message="No enabled module AI declarations",
            detail={"modules": [], "accessible_models": models},
        )
    return _component(
        id="ai_module_config",
        name="Module AI config",
        group=_AI_GROUP,
        status="ok",
        message=f"{len(enabled)} module(s) · {len(models)} accessible model(s)",
        detail={"modules": enabled, "accessible_models": models},
    )


def _check_ai_action_palette() -> dict[str, Any]:
    from orbiteus_core.ai.registry import action_registry

    actions = action_registry.get_all()
    modules = sorted({a.module for a in actions if a.module})
    if not actions:
        return _component(
            id="ai_action_palette",
            name="Command palette",
            group=_AI_GROUP,
            status="unknown",
            message="No actions registered",
        )
    return _component(
        id="ai_action_palette",
        name="Command palette",
        group=_AI_GROUP,
        status="ok",
        message=f"{len(actions)} action(s) across {len(modules)} module(s)",
        detail={"action_count": len(actions), "modules": modules},
    )


async def _check_ai_agents() -> dict[str, Any]:
    start = time.perf_counter()
    try:
        from orbiteus_core.db import engine

        async with engine.connect() as conn:
            row = (
                await conn.execute(
                    text(
                        "SELECT COUNT(*) AS total, "
                        "COUNT(*) FILTER (WHERE is_system) AS system "
                        "FROM base_agents WHERE active = true"
                    )
                )
            ).mappings().first()
        total = int(row["total"]) if row else 0
        system = int(row["system"]) if row else 0
        latency = round((time.perf_counter() - start) * 1000, 1)
        if total == 0:
            return _component(
                id="ai_agents",
                name="Agent definitions",
                group=_AI_GROUP,
                status="unknown",
                message="No active agents in base_agents",
                latency_ms=latency,
            )
        return _component(
            id="ai_agents",
            name="Agent definitions",
            group=_AI_GROUP,
            status="ok",
            message=f"{total} active agent(s) ({system} system)",
            latency_ms=latency,
            detail={"total": total, "system": system},
        )
    except Exception as exc:
        logger.warning("system_status: ai agents check failed", extra={"error": str(exc)})
        return _component(
            id="ai_agents",
            name="Agent definitions",
            group=_AI_GROUP,
            status="degraded",
            message="Could not read base_agents",
            detail={"error": str(exc)[:200]},
        )


async def _check_ai_credentials() -> dict[str, Any]:
    start = time.perf_counter()
    try:
        from orbiteus_core.db import engine

        async with engine.connect() as conn:
            rows = (
                await conn.execute(
                    text(
                        "SELECT provider, COUNT(*) AS n "
                        "FROM base_ai_credentials "
                        "WHERE is_active = true "
                        "GROUP BY provider ORDER BY provider"
                    )
                )
            ).mappings().all()
        latency = round((time.perf_counter() - start) * 1000, 1)
        providers = {str(r["provider"]): int(r["n"]) for r in rows}
        total = sum(providers.values())
        if total == 0:
            return _component(
                id="ai_credentials",
                name="BYOK credentials",
                group=_AI_GROUP,
                status="unknown",
                message="No active provider credentials",
                latency_ms=latency,
            )
        return _component(
            id="ai_credentials",
            name="BYOK credentials",
            group=_AI_GROUP,
            status="ok",
            message=f"{total} credential(s) · {', '.join(providers)}",
            latency_ms=latency,
            detail={"providers": providers},
        )
    except Exception as exc:
        logger.warning("system_status: ai credentials check failed", extra={"error": str(exc)})
        return _component(
            id="ai_credentials",
            name="BYOK credentials",
            group=_AI_GROUP,
            status="degraded",
            message="Could not read base_ai_credentials",
            detail={"error": str(exc)[:200]},
        )


def _check_ai_secret_key() -> dict[str, Any]:
    from orbiteus_core.config import settings

    raw = (settings.ai_secret_key or "").strip()
    if not raw or raw == "change-me-with-fernet-key":
        return _component(
            id="ai_secret_key",
            name="Credential encryption",
            group=_AI_GROUP,
            status="unknown",
            message="AI_SECRET_KEY not configured (BYOK storage disabled)",
        )
    try:
        from orbiteus_core.ai.keys import _fernet

        _fernet()
        return _component(
            id="ai_secret_key",
            name="Credential encryption",
            group=_AI_GROUP,
            status="ok",
            message="Fernet key valid · credentials can be stored",
        )
    except Exception as exc:
        return _component(
            id="ai_secret_key",
            name="Credential encryption",
            group=_AI_GROUP,
            status="degraded",
            message="AI_SECRET_KEY invalid",
            detail={"error": str(exc)[:200]},
        )


async def _check_ai_embeddings(pgvector_status: ComponentStatus) -> dict[str, Any]:
    from orbiteus_core.ai.config import ai_registry
    from orbiteus_core import embedding_dispatcher

    embed_models = sorted(ai_registry.embed_models())
    if pgvector_status != "ok":
        return _component(
            id="ai_embeddings",
            name="Embeddings pipeline",
            group=_AI_GROUP,
            status="degraded" if pgvector_status == "degraded" else "unknown",
            message="pgvector extension unavailable",
            detail={"embed_models": embed_models},
        )
    start = time.perf_counter()
    try:
        from orbiteus_core.db import engine

        async with engine.connect() as conn:
            row = (
                await conn.execute(text("SELECT COUNT(*) AS total FROM base_embeddings"))
            ).mappings().first()
        total = int(row["total"]) if row else 0
        latency = round((time.perf_counter() - start) * 1000, 1)
        dispatcher = "registered" if embedding_dispatcher._REGISTERED else "pending"
        if not embed_models:
            return _component(
                id="ai_embeddings",
                name="Embeddings pipeline",
                group=_AI_GROUP,
                status="unknown",
                message=f"Dispatcher {dispatcher} · no embed_models declared",
                latency_ms=latency,
                detail={"rows": total, "embed_models": embed_models},
            )
        return _component(
            id="ai_embeddings",
            name="Embeddings pipeline",
            group=_AI_GROUP,
            status="ok",
            message=(
                f"{len(embed_models)} embed model(s) · {total} vector row(s) · "
                f"dispatcher {dispatcher}"
            ),
            latency_ms=latency,
            detail={"rows": total, "embed_models": embed_models},
        )
    except Exception as exc:
        logger.warning("system_status: ai embeddings check failed", extra={"error": str(exc)})
        return _component(
            id="ai_embeddings",
            name="Embeddings pipeline",
            group=_AI_GROUP,
            status="degraded",
            message="Could not read base_embeddings",
            detail={"error": str(exc)[:200]},
        )


async def _check_ai_agent_runs() -> dict[str, Any]:
    start = time.perf_counter()
    try:
        from orbiteus_core.db import engine

        async with engine.connect() as conn:
            rows = (
                await conn.execute(
                    text(
                        "SELECT status, COUNT(*) AS n "
                        "FROM base_agent_runs "
                        "GROUP BY status ORDER BY status"
                    )
                )
            ).mappings().all()
        latency = round((time.perf_counter() - start) * 1000, 1)
        by_status = {str(r["status"]): int(r["n"]) for r in rows}
        total = sum(by_status.values())
        if total == 0:
            return _component(
                id="ai_agent_runs",
                name="Agent run ledger",
                group=_AI_GROUP,
                status="unknown",
                message="No agent runs recorded yet",
                latency_ms=latency,
            )
        failed = by_status.get("failed", 0)
        status: ComponentStatus = "degraded" if failed else "ok"
        return _component(
            id="ai_agent_runs",
            name="Agent run ledger",
            group=_AI_GROUP,
            status=status,
            message=f"{total} run(s)" + (f" · {failed} failed" if failed else ""),
            latency_ms=latency,
            detail={"by_status": by_status},
        )
    except Exception as exc:
        logger.warning("system_status: ai agent runs check failed", extra={"error": str(exc)})
        return _component(
            id="ai_agent_runs",
            name="Agent run ledger",
            group=_AI_GROUP,
            status="degraded",
            message="Could not read base_agent_runs",
            detail={"error": str(exc)[:200]},
        )


def _check_ai_providers() -> dict[str, Any]:
    from orbiteus_core.ai.providers import get_provider

    names = ("anthropic", "openai", "ollama", "gemini")
    loaded: list[str] = []
    errors: dict[str, str] = {}
    for name in names:
        try:
            get_provider(name)
            loaded.append(name)
        except Exception as exc:  # noqa: BLE001
            errors[name] = str(exc)[:120]
    if not loaded:
        return _component(
            id="ai_providers",
            name="Provider adapters",
            group=_AI_GROUP,
            status="degraded",
            message="No provider adapters available",
            detail={"errors": errors},
        )
    return _component(
        id="ai_providers",
        name="Provider adapters",
        group=_AI_GROUP,
        status="ok",
        message=f"Ready: {', '.join(loaded)}",
        detail={"providers": loaded, "errors": errors or None},
    )


def _check_ai_tooling() -> dict[str, Any]:
    try:
        from orbiteus_core.ai.loop import run_agent_loop  # noqa: F401
        from orbiteus_core.ai.tools import build_tools
        from orbiteus_core.context import RequestContext

        ctx = RequestContext(is_superadmin=True)
        tools = build_tools(ctx)
        read_tools = [t["name"] for t in tools if t["name"].startswith("read_")]
        return _component(
            id="ai_tooling",
            name="Agent tooling",
            group=_AI_GROUP,
            status="ok",
            message=f"{len(tools)} tool(s) · {len(read_tools)} read tool(s)",
            detail={"tool_count": len(tools), "read_tools": read_tools[:12]},
        )
    except Exception as exc:
        logger.warning("system_status: ai tooling check failed", extra={"error": str(exc)})
        return _component(
            id="ai_tooling",
            name="Agent tooling",
            group=_AI_GROUP,
            status="degraded",
            message="Tool surface could not be built",
            detail={"error": str(exc)[:200]},
        )


async def collect_ai_status_components(
    pgvector_status: ComponentStatus,
) -> list[dict[str, Any]]:
    """Probe AI-layer subsystems; returns tiles with group ``ai``."""
    sync_checks = (
        _check_ai_module_config,
        _check_ai_action_palette,
        _check_ai_secret_key,
        _check_ai_providers,
        _check_ai_tooling,
    )
    sync_results = [fn() for fn in sync_checks]
    async_results = await asyncio.gather(
        _check_ai_agents(),
        _check_ai_credentials(),
        _check_ai_embeddings(pgvector_status),
        _check_ai_agent_runs(),
    )
    return [*sync_results, *async_results]
