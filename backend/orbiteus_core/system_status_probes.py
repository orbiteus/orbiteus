"""Version and subsystem probes for the Orbiteus stack catalogue."""
from __future__ import annotations

import importlib
import logging
import os
import sys
from typing import Any

from sqlalchemy import text

from orbiteus_core.system_status import ComponentStatus, _component

logger = logging.getLogger(__name__)


def pkg_version(distribution: str, *, module_fallback: str | None = None) -> str:
    try:
        from importlib.metadata import version

        return version(distribution)
    except Exception:
        mod_name = module_fallback or distribution.replace("-", "_")
        try:
            mod = importlib.import_module(mod_name)
            ver = getattr(mod, "__version__", None)
            return str(ver) if ver else "unknown"
        except Exception:
            return "unknown"


def check_python() -> dict[str, Any]:
    major, minor, micro = sys.version_info[:3]
    return _component(
        id="python",
        name="Python",
        group="runtime",
        status="ok",
        message=f"{major}.{minor}.{micro}",
        detail={"implementation": sys.implementation.name},
    )


def check_fastapi() -> dict[str, Any]:
    ver = pkg_version("fastapi")
    return _component(
        id="fastapi",
        name="FastAPI",
        group="runtime",
        status="ok",
        message=f"v{ver}",
    )


def check_http_server() -> dict[str, Any]:
    use_gunicorn = os.environ.get("USE_GUNICORN", "0") == "1"
    if use_gunicorn:
        ver = pkg_version("gunicorn")
        workers = os.environ.get("GUNICORN_WORKERS", "4")
        return _component(
            id="http_server",
            name="Gunicorn + UvicornWorker",
            group="runtime",
            status="ok",
            message=f"v{ver} · {workers} workers",
        )
    ver = pkg_version("uvicorn")
    reload = os.environ.get("UVICORN_RELOAD", "")
    return _component(
        id="http_server",
        name="Uvicorn",
        group="runtime",
        status="ok",
        message=f"v{ver}" + (" · reload" if reload else " · dev server"),
    )


def check_sqlalchemy(pg_ok: bool) -> dict[str, Any]:
    import sqlalchemy

    try:
        from orbiteus_core.db import engine

        pool = engine.pool
        checked_in = getattr(pool, "checkedin", lambda: None)()
        message = f"v{sqlalchemy.__version__} · async engine"
        if checked_in is not None:
            message += f" · pool in {checked_in}"
        status: ComponentStatus = "ok" if pg_ok else "unknown"
        return _component(
            id="sqlalchemy",
            name="SQLAlchemy 2",
            group="persistence",
            status=status,
            message=message,
            detail={"dialect": engine.dialect.name},
        )
    except Exception as exc:
        return _component(
            id="sqlalchemy",
            name="SQLAlchemy 2",
            group="persistence",
            status="degraded",
            message=f"v{sqlalchemy.__version__}",
            detail={"error": str(exc)[:200]},
        )


def check_asyncpg() -> dict[str, Any]:
    ver = pkg_version("asyncpg")
    return _component(
        id="asyncpg",
        name="asyncpg",
        group="persistence",
        status="ok",
        message=f"v{ver} · PostgreSQL driver",
    )


async def check_alembic() -> dict[str, Any]:
    ver = pkg_version("alembic")
    try:
        from alembic.config import Config
        from alembic.runtime.migration import MigrationContext
        from alembic.script import ScriptDirectory

        from orbiteus_core.db import engine

        cfg = Config("alembic.ini")
        script = ScriptDirectory.from_config(cfg)
        head = script.get_current_head()

        async with engine.connect() as conn:
            current = await conn.run_sync(
                lambda sync_conn: MigrationContext.configure(sync_conn).get_current_revision()
            )

        if current == head:
            return _component(
                id="alembic",
                name="Alembic",
                group="persistence",
                status="ok",
                message=f"v{ver} · at head ({str(head)[:12]})",
                detail={"revision": current, "head": head},
            )
        if not current:
            return _component(
                id="alembic",
                name="Alembic",
                group="persistence",
                status="degraded",
                message=f"v{ver} · database not migrated",
                detail={"head": head},
            )
        return _component(
            id="alembic",
            name="Alembic",
            group="persistence",
            status="degraded",
            message=f"v{ver} · revision {str(current)[:12]} ≠ head",
            detail={"revision": current, "head": head},
        )
    except Exception as exc:
        logger.warning("system_status: alembic check failed", extra={"error": str(exc)})
        return _component(
            id="alembic",
            name="Alembic",
            group="persistence",
            status="degraded",
            message=f"v{ver} · could not verify migrations",
            detail={"error": str(exc)[:200]},
        )


def check_pydantic() -> dict[str, Any]:
    ver = pkg_version("pydantic")
    return _component(
        id="pydantic",
        name="Pydantic v2",
        group="persistence",
        status="ok",
        message=f"v{ver} · schemas & settings",
    )


def check_module_registry() -> dict[str, Any]:
    try:
        from orbiteus_core.auto_router import _model_registry
        from orbiteus_core.registry import registry

        modules = sorted(getattr(registry, "_modules", {}).keys())
        model_count = len(_model_registry)
        bootstrapped = getattr(registry, "_bootstrapped", False)
        return _component(
            id="module_registry",
            name="Module Registry",
            group="engine",
            status="ok" if bootstrapped else "unknown",
            message=f"{len(modules)} modules · {model_count} models",
            detail={"modules": modules, "bootstrapped": bootstrapped},
        )
    except Exception as exc:
        return _component(
            id="module_registry",
            name="Module Registry",
            group="engine",
            status="degraded",
            message="Registry unavailable",
            detail={"error": str(exc)[:200]},
        )


async def check_rbac() -> dict[str, Any]:
    try:
        from orbiteus_core.db import engine

        async with engine.connect() as conn:
            access = (
                await conn.execute(text("SELECT COUNT(*) AS n FROM base_model_access"))
            ).scalar_one()
            rules = (
                await conn.execute(text("SELECT COUNT(*) AS n FROM base_rules"))
            ).scalar_one()
        return _component(
            id="rbac",
            name="RBAC",
            group="engine",
            status="ok",
            message=f"{int(access)} access rows · {int(rules)} record rules",
        )
    except Exception as exc:
        return _component(
            id="rbac",
            name="RBAC",
            group="engine",
            status="degraded",
            message="Could not read RBAC tables",
            detail={"error": str(exc)[:200]},
        )


async def check_audit() -> dict[str, Any]:
    try:
        from orbiteus_core.db import engine

        async with engine.connect() as conn:
            total = (
                await conn.execute(text("SELECT COUNT(*) AS n FROM base_audit_log"))
            ).scalar_one()
        return _component(
            id="audit",
            name="Audit log",
            group="engine",
            status="ok",
            message=f"{int(total)} entries · mandatory CRUD trail",
        )
    except Exception as exc:
        return _component(
            id="audit",
            name="Audit log",
            group="engine",
            status="degraded",
            message="Could not read audit table",
            detail={"error": str(exc)[:200]},
        )


def check_event_bus() -> dict[str, Any]:
    try:
        from orbiteus_core.events import event_bus

        event_count = len(event_bus._subs)
        handler_count = sum(len(h) for h in event_bus._subs.values())
        return _component(
            id="event_bus",
            name="EventBus",
            group="engine",
            status="ok",
            message=f"in-process · {event_count} topics · {handler_count} handlers",
        )
    except Exception as exc:
        return _component(
            id="event_bus",
            name="EventBus",
            group="engine",
            status="degraded",
            message="Unavailable",
            detail={"error": str(exc)[:200]},
        )


def check_cache(redis_status: ComponentStatus) -> dict[str, Any]:
    if redis_status == "skipped":
        return _component(
            id="cache",
            name="Cache",
            group="data",
            status="skipped",
            message="Requires Redis",
        )
    if redis_status != "ok":
        return _component(
            id="cache",
            name="Cache",
            group="data",
            status="degraded",
            message="Redis backplane unavailable",
        )
    return _component(
        id="cache",
        name="Cache",
        group="data",
        status="ok",
        message="Redis read-through · RBAC ≤60s · rate limits",
    )


def check_auth_jwt() -> dict[str, Any]:
    jose = pkg_version("python-jose", module_fallback="jose")
    bcrypt = pkg_version("bcrypt")
    return _component(
        id="auth_jwt",
        name="Auth (JWT + 2FA)",
        group="engine",
        status="ok",
        message=f"jose v{jose} · bcrypt v{bcrypt}",
        detail={"totp": pkg_version("pyotp", module_fallback="pyotp")},
    )


def check_prometheus() -> dict[str, Any]:
    ver = pkg_version("prometheus_client", module_fallback="prometheus_client")
    return _component(
        id="prometheus",
        name="Prometheus metrics",
        group="engine",
        status="ok",
        message=f"v{ver} · GET /metrics",
    )


def check_celery_lib() -> dict[str, Any]:
    ver = pkg_version("celery")
    return _component(
        id="celery_lib",
        name="Celery 5",
        group="async",
        status="ok",
        message=f"v{ver} · task library",
    )


def check_nginx() -> dict[str, Any]:
    if os.environ.get("NGINX_ENABLED", "").lower() in ("1", "true", "yes"):
        return _component(
            id="nginx",
            name="nginx",
            group="infra",
            status="ok",
            message="Reverse proxy · TLS · SSE buffering off",
        )
    return _component(
        id="nginx",
        name="nginx",
        group="infra",
        status="skipped",
        message="Prod compose only (docker-compose.prod.yml)",
    )


def check_docker() -> dict[str, Any]:
    in_container = os.path.exists("/.dockerenv") or os.environ.get("ENVIRONMENT") == "development"
    return _component(
        id="docker",
        name="Docker Compose",
        group="infra",
        status="ok" if in_container else "unknown",
        message="Dev/prod compose stack" if in_container else "Host process (outside container)",
    )
