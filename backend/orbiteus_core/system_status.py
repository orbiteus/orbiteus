"""Aggregate health of Orbiteus framework components.

Used by Technical → System status in the admin UI. Probes runtime
dependencies (PostgreSQL, Redis, Celery, pgvector, outbox) and returns a
stable JSON contract for tile rendering.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import urlparse

from sqlalchemy import text

logger = logging.getLogger(__name__)

ComponentStatus = Literal["ok", "degraded", "skipped", "unknown"]


def _component(
    *,
    id: str,
    name: str,
    group: str,
    status: ComponentStatus,
    message: str,
    latency_ms: float | None = None,
    detail: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": id,
        "name": name,
        "group": group,
        "status": status,
        "message": message,
        "latency_ms": latency_ms,
        "detail": detail or {},
    }


async def _check_postgresql() -> dict[str, Any]:
    start = time.perf_counter()
    try:
        from orbiteus_core.db import engine

        async with engine.connect() as conn:
            row = (
                await conn.execute(text("SELECT version() AS version"))
            ).mappings().first()
            version = (row["version"] if row else "").split(",")[0]
        latency = round((time.perf_counter() - start) * 1000, 1)
        return _component(
            id="postgresql",
            name="PostgreSQL 16",
            group="data",
            status="ok",
            message=version or "Connected",
            latency_ms=latency,
        )
    except Exception as exc:
        logger.warning("system_status: postgresql failed", extra={"error": str(exc)})
        latency = round((time.perf_counter() - start) * 1000, 1)
        return _component(
            id="postgresql",
            name="PostgreSQL 16",
            group="data",
            status="degraded",
            message="Connection failed",
            latency_ms=latency,
            detail={"error": str(exc)[:200]},
        )


async def _check_pgvector() -> dict[str, Any]:
    start = time.perf_counter()
    try:
        from orbiteus_core.db import engine

        async with engine.connect() as conn:
            row = (
                await conn.execute(
                    text(
                        "SELECT EXISTS("
                        "  SELECT 1 FROM pg_extension WHERE extname = 'vector'"
                        ") AS installed"
                    )
                )
            ).mappings().first()
            installed = bool(row and row["installed"])
        latency = round((time.perf_counter() - start) * 1000, 1)
        if installed:
            return _component(
                id="pgvector",
                name="pgvector",
                group="data",
                status="ok",
                message="Extension installed",
                latency_ms=latency,
            )
        return _component(
            id="pgvector",
            name="pgvector",
            group="data",
            status="degraded",
            message="Extension not installed",
            latency_ms=latency,
        )
    except Exception as exc:
        logger.warning("system_status: pgvector check failed", extra={"error": str(exc)})
        return _component(
            id="pgvector",
            name="pgvector",
            group="data",
            status="degraded",
            message="Could not verify extension",
            detail={"error": str(exc)[:200]},
        )


def _check_pgbouncer() -> dict[str, Any]:
    url = os.environ.get("DATABASE_URL", "")
    parsed = urlparse(url.replace("+asyncpg", ""))
    host = (parsed.hostname or "").lower()
    port = parsed.port
    if host == "pgbouncer" or port == 6432:
        return _component(
            id="pgbouncer",
            name="PgBouncer",
            group="data",
            status="ok",
            message="Transaction pool in use",
            detail={"host": host, "port": port},
        )
    return _component(
        id="pgbouncer",
        name="PgBouncer",
        group="data",
        status="skipped",
        message="Direct DB connection (dev / single-host)",
        detail={"host": host or "localhost", "port": port or 5432},
    )


async def _check_redis() -> dict[str, Any]:
    redis_url = os.environ.get("REDIS_URL", "").strip()
    if not redis_url:
        return _component(
            id="redis",
            name="Redis 7",
            group="data",
            status="skipped",
            message="REDIS_URL not configured",
        )

    start = time.perf_counter()
    try:
        import redis.asyncio as redis_async

        client = redis_async.from_url(redis_url, encoding="utf-8", decode_responses=True)
        try:
            pong = await client.ping()
            info = await client.info(section="server")
        finally:
            await client.aclose()
        latency = round((time.perf_counter() - start) * 1000, 1)
        version = info.get("redis_version", "unknown") if isinstance(info, dict) else "unknown"
        return _component(
            id="redis",
            name="Redis 7",
            group="data",
            status="ok" if pong else "degraded",
            message=f"redis {version}" if pong else "Ping failed",
            latency_ms=latency,
        )
    except Exception as exc:
        logger.warning("system_status: redis failed", extra={"error": str(exc)})
        latency = round((time.perf_counter() - start) * 1000, 1)
        return _component(
            id="redis",
            name="Redis 7",
            group="data",
            status="degraded",
            message="Connection failed",
            latency_ms=latency,
            detail={"error": str(exc)[:200]},
        )


def _inspect_celery_workers() -> dict[str, Any]:
    start = time.perf_counter()
    try:
        from celery_app import app

        insp = app.control.inspect(timeout=0.8)
        ping = insp.ping() or {}
        latency = round((time.perf_counter() - start) * 1000, 1)
        if ping:
            workers = sorted(ping.keys())
            return _component(
                id="celery_worker",
                name="Celery Worker",
                group="async",
                status="ok",
                message=f"{len(workers)} worker(s) online",
                latency_ms=latency,
                detail={"workers": workers},
            )
        return _component(
            id="celery_worker",
            name="Celery Worker",
            group="async",
            status="unknown",
            message="No workers running (optional in dev — start worker service)",
            latency_ms=latency,
        )
    except Exception as exc:
        logger.warning("system_status: celery worker inspect failed", extra={"error": str(exc)})
        return _component(
            id="celery_worker",
            name="Celery Worker",
            group="async",
            status="degraded",
            message="Inspect failed",
            detail={"error": str(exc)[:200]},
        )


def _inspect_celery_beat() -> dict[str, Any]:
    redis_url = os.environ.get("REDIS_URL", "").strip()
    if not redis_url:
        return _component(
            id="celery_beat",
            name="Celery Beat",
            group="async",
            status="skipped",
            message="Requires Redis broker",
        )
    try:
        from celery_app import app

        jobs = sorted(app.conf.beat_schedule.keys()) if app.conf.beat_schedule else []
        if not jobs:
            return _component(
                id="celery_beat",
                name="Celery Beat",
                group="async",
                status="degraded",
                message="No beat schedule configured",
            )
        insp = app.control.inspect(timeout=0.8)
        scheduled = insp.scheduled() or {}
        queued = sum(len(v) for v in scheduled.values())
        if queued > 0:
            return _component(
                id="celery_beat",
                name="Celery Beat",
                group="async",
                status="ok",
                message=f"{len(jobs)} periodic jobs · {queued} queued",
                detail={"jobs": jobs},
            )
        return _component(
            id="celery_beat",
            name="Celery Beat",
            group="async",
            status="unknown",
            message=f"{len(jobs)} jobs configured — verify beat container",
            detail={"jobs": jobs},
        )
    except Exception as exc:
        logger.warning("system_status: celery beat inspect failed", extra={"error": str(exc)})
        return _component(
            id="celery_beat",
            name="Celery Beat",
            group="async",
            status="degraded",
            message="Inspect failed",
            detail={"error": str(exc)[:200]},
        )


async def _check_outbox() -> dict[str, Any]:
    start = time.perf_counter()
    try:
        from orbiteus_core.db import engine

        async with engine.connect() as conn:
            rows = (
                await conn.execute(
                    text(
                        "SELECT status, COUNT(*) AS count "
                        "FROM base_outbox GROUP BY status"
                    )
                )
            ).mappings().all()
        counts = {str(r["status"]): int(r["count"]) for r in rows}
        pending = counts.get("pending", 0)
        dead = counts.get("dead", 0)
        latency = round((time.perf_counter() - start) * 1000, 1)
        if dead > 0:
            status: ComponentStatus = "degraded"
            message = f"{pending} pending · {dead} dead"
        else:
            status = "ok"
            message = f"{pending} pending"
        return _component(
            id="outbox",
            name="Event Outbox",
            group="async",
            status=status,
            message=message,
            latency_ms=latency,
            detail={"counts": counts},
        )
    except Exception as exc:
        logger.warning("system_status: outbox check failed", extra={"error": str(exc)})
        return _component(
            id="outbox",
            name="Event Outbox",
            group="async",
            status="degraded",
            message="Could not read queue",
            detail={"error": str(exc)[:200]},
        )


async def _check_realtime(redis_status: ComponentStatus) -> dict[str, Any]:
    if redis_status == "skipped":
        return _component(
            id="realtime",
            name="Realtime (SSE)",
            group="engine",
            status="skipped",
            message="Requires Redis pub/sub",
        )
    if redis_status != "ok":
        return _component(
            id="realtime",
            name="Realtime (SSE)",
            group="engine",
            status="degraded",
            message="Redis backplane unavailable",
        )
    return _component(
        id="realtime",
        name="Realtime (SSE)",
        group="engine",
        status="ok",
        message="Redis pub/sub · tenant-scoped topics",
    )


async def collect_system_status() -> dict[str, Any]:
    """Probe framework components and return a tile-friendly payload."""
    from orbiteus_core.system_status_ai import collect_ai_status_components
    from orbiteus_core.system_status_catalog import COMPONENT_ORDER
    from orbiteus_core.system_status_probes import (
        check_asyncpg,
        check_audit,
        check_auth_jwt,
        check_cache,
        check_celery_lib,
        check_docker,
        check_event_bus,
        check_fastapi,
        check_http_server,
        check_module_registry,
        check_nginx,
        check_pydantic,
        check_prometheus,
        check_python,
        check_rbac,
        check_sqlalchemy,
        check_alembic,
    )

    pg, pgvector, redis, outbox, alembic, rbac, audit = await asyncio.gather(
        _check_postgresql(),
        _check_pgvector(),
        _check_redis(),
        _check_outbox(),
        check_alembic(),
        check_rbac(),
        check_audit(),
    )

    ai_components = await collect_ai_status_components(pgvector["status"])

    pg_ok = pg["status"] == "ok"
    pgbouncer = _check_pgbouncer()
    try:
        worker, beat = await asyncio.gather(
            asyncio.wait_for(asyncio.to_thread(_inspect_celery_workers), timeout=2.5),
            asyncio.wait_for(asyncio.to_thread(_inspect_celery_beat), timeout=2.5),
        )
    except TimeoutError:
        worker = _component(
            id="celery_worker",
            name="Celery Worker",
            group="async",
            status="unknown",
            message="Worker probe timed out",
        )
        beat = _component(
            id="celery_beat",
            name="Celery Beat",
            group="async",
            status="unknown",
            message="Beat probe timed out",
        )

    components_map: dict[str, dict[str, Any]] = {
        c["id"]: c
        for c in (
            check_python(),
            check_fastapi(),
            check_http_server(),
            check_sqlalchemy(pg_ok),
            check_asyncpg(),
            alembic,
            pg,
            pgvector,
            pgbouncer,
            check_pydantic(),
            redis,
            check_cache(redis["status"]),
            check_module_registry(),
            rbac,
            audit,
            check_event_bus(),
            await _check_realtime(redis["status"]),
            check_auth_jwt(),
            check_prometheus(),
            check_celery_lib(),
            worker,
            beat,
            outbox,
            check_nginx(),
            check_docker(),
        )
    }

    for comp in ai_components:
        components_map[comp["id"]] = comp

    order_index = {cid: idx for idx, cid in enumerate(COMPONENT_ORDER)}
    components = sorted(
        components_map.values(),
        key=lambda c: (order_index.get(c["id"], 999), c["id"]),
    )

    critical = {"postgresql", "fastapi", "sqlalchemy", "alembic"}
    redis_required = os.environ.get("REDIS_URL", "").strip()
    if redis_required:
        critical.add("redis")

    overall: ComponentStatus = "ok"
    for comp in components:
        if comp["id"] in critical and comp["status"] == "degraded":
            overall = "degraded"
            break

    return {
        "status": overall,
        "checked_at": datetime.now(UTC).isoformat(),
        "components": components,
    }
