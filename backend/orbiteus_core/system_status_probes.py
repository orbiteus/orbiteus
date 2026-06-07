"""Version and subsystem probes for the Orbiteus stack catalogue."""
from __future__ import annotations

import importlib
import logging
import os
import sys
from typing import Any

from sqlalchemy import text

from orbiteus_core.system_status import ComponentStatus, _component
from orbiteus_core.version import get_orbiteus_version

logger = logging.getLogger(__name__)


def version_label(ver: str | None) -> str:
    """Normalize a semver string to ``vX.Y.Z`` (empty when unknown)."""
    clean = (ver or "").strip().removeprefix("v")
    if not clean or clean == "unknown":
        return ""
    return f"v{clean}"


def with_version(ver: str | None, *parts: str) -> str:
    """Join a version label with human-readable status fragments."""
    bits: list[str] = []
    label = version_label(ver)
    if label:
        bits.append(label)
    bits.extend(p for p in parts if p)
    return " · ".join(bits)


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


def check_orbiteus() -> dict[str, Any]:
    ver = get_orbiteus_version()
    return _component(
        id="orbiteus",
        name="Orbiteus",
        group="runtime",
        status="ok",
        message=f"v{ver}",
        detail={"version": ver},
    )


def check_python() -> dict[str, Any]:
    major, minor, micro = sys.version_info[:3]
    impl = sys.implementation.name
    return _component(
        id="python",
        name="Python",
        group="runtime",
        status="ok",
        message=with_version(f"{major}.{minor}.{micro}", impl),
        detail={"implementation": impl},
    )


def check_fastapi() -> dict[str, Any]:
    ver = pkg_version("fastapi")
    starlette = pkg_version("starlette")
    return _component(
        id="fastapi",
        name="FastAPI",
        group="runtime",
        status="ok",
        message=with_version(ver, f"Starlette {version_label(starlette)}"),
        detail={"starlette": starlette},
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
            message=with_version(ver, f"{workers} workers"),
        )
    ver = pkg_version("uvicorn")
    reload = os.environ.get("UVICORN_RELOAD", "")
    return _component(
        id="http_server",
        name="Uvicorn",
        group="runtime",
        status="ok",
        message=with_version(ver, "reload" if reload else "dev server"),
    )


def check_sqlalchemy(pg_ok: bool) -> dict[str, Any]:
    import sqlalchemy

    try:
        from orbiteus_core.db import engine

        pool = engine.pool
        checked_in = getattr(pool, "checkedin", lambda: None)()
        message = with_version(sqlalchemy.__version__, "async engine")
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
            message=with_version(sqlalchemy.__version__),
            detail={"error": str(exc)[:200]},
        )


def check_asyncpg() -> dict[str, Any]:
    ver = pkg_version("asyncpg")
    return _component(
        id="asyncpg",
        name="asyncpg",
        group="persistence",
        status="ok",
        message=with_version(ver, "PostgreSQL driver"),
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
                message=with_version(ver, f"at head ({str(head)[:12]})"),
                detail={"revision": current, "head": head},
            )
        if not current:
            return _component(
                id="alembic",
                name="Alembic",
                group="persistence",
                status="degraded",
                message=with_version(ver, "database not migrated"),
                detail={"head": head},
            )
        return _component(
            id="alembic",
            name="Alembic",
            group="persistence",
            status="degraded",
            message=with_version(ver, f"revision {str(current)[:12]} ≠ head"),
            detail={"revision": current, "head": head},
        )
    except Exception as exc:
        logger.warning("system_status: alembic check failed", extra={"error": str(exc)})
        return _component(
            id="alembic",
            name="Alembic",
            group="persistence",
            status="degraded",
            message=with_version(ver, "could not verify migrations"),
            detail={"error": str(exc)[:200]},
        )


def check_pydantic() -> dict[str, Any]:
    ver = pkg_version("pydantic")
    return _component(
        id="pydantic",
        name="Pydantic v2",
        group="persistence",
        status="ok",
        message=with_version(ver, "schemas & settings"),
    )


def check_module_registry() -> dict[str, Any]:
    try:
        from orbiteus_core.auto_router import _model_registry
        from orbiteus_core.registry import registry

        modules = sorted(getattr(registry, "_modules", {}).keys())
        model_count = len(_model_registry)
        bootstrapped = getattr(registry, "_bootstrapped", False)
        module_versions = {
            name: desc.manifest.get("version", "?")
            for name, desc in getattr(registry, "_modules", {}).items()
        }
        version_summary = ", ".join(
            f"{name} v{module_versions[name]}" for name in modules
        )
        return _component(
            id="module_registry",
            name="Module Registry",
            group="engine",
            status="ok" if bootstrapped else "unknown",
            message=f"{len(modules)} modules · {model_count} models · {version_summary}",
            detail={
                "modules": modules,
                "module_versions": module_versions,
                "bootstrapped": bootstrapped,
            },
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
    redis_py = pkg_version("redis")
    if redis_status == "skipped":
        return _component(
            id="cache",
            name="Cache",
            group="data",
            status="skipped",
            message=with_version(redis_py, "requires Redis"),
        )
    if redis_status != "ok":
        return _component(
            id="cache",
            name="Cache",
            group="data",
            status="degraded",
            message=with_version(redis_py, "Redis backplane unavailable"),
        )
    return _component(
        id="cache",
        name="Cache",
        group="data",
        status="ok",
        message=with_version(redis_py, "read-through · RBAC ≤60s · rate limits"),
    )


def check_auth_jwt() -> dict[str, Any]:
    jose = pkg_version("python-jose", module_fallback="jose")
    bcrypt = pkg_version("bcrypt")
    pyotp = pkg_version("pyotp", module_fallback="pyotp")
    return _component(
        id="auth_jwt",
        name="Auth (JWT + 2FA)",
        group="engine",
        status="ok",
        message=with_version(
            jose,
            f"bcrypt {version_label(bcrypt)}",
            f"pyotp {version_label(pyotp)}",
        ),
        detail={"bcrypt": bcrypt, "pyotp": pyotp},
    )


def check_prometheus() -> dict[str, Any]:
    ver = pkg_version("prometheus_client", module_fallback="prometheus_client")
    return _component(
        id="prometheus",
        name="Prometheus metrics",
        group="engine",
        status="ok",
        message=with_version(ver, "GET /metrics"),
    )


def check_celery_lib() -> dict[str, Any]:
    ver = pkg_version("celery")
    return _component(
        id="celery_lib",
        name="Celery 5",
        group="async",
        status="ok",
        message=with_version(ver, "task library"),
    )


def check_nginx() -> dict[str, Any]:
    if os.environ.get("NGINX_ENABLED", "").lower() in ("1", "true", "yes"):
        nginx_ver = _probe_nginx_version()
        return _component(
            id="nginx",
            name="nginx",
            group="infra",
            status="ok",
            message=with_version(nginx_ver, "reverse proxy · TLS · SSE buffering off"),
            detail={"version": nginx_ver or None},
        )
    return _component(
        id="nginx",
        name="nginx",
        group="infra",
        status="skipped",
        message="Prod compose only (docker-compose.prod.yml)",
    )


def _probe_nginx_version() -> str:
    import shutil
    import subprocess

    binary = shutil.which("nginx")
    if not binary:
        return "unknown"
    try:
        proc = subprocess.run(
            [binary, "-v"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        raw = (proc.stderr or proc.stdout or "").strip()
        if "/" in raw:
            return raw.split("/", 1)[1].strip()
        return raw or "unknown"
    except Exception:
        return "unknown"


def check_docker() -> dict[str, Any]:
    import platform

    in_container = os.path.exists("/.dockerenv") or os.environ.get("ENVIRONMENT") == "development"
    py = platform.python_version()
    if in_container:
        return _component(
            id="docker",
            name="Docker Compose",
            group="infra",
            status="ok",
            message=with_version(py, "Python container · compose stack"),
            detail={"python": py, "platform": platform.platform()},
        )
    return _component(
        id="docker",
        name="Docker Compose",
        group="infra",
        status="unknown",
        message=with_version(py, "host process (outside container)"),
        detail={"python": py, "platform": platform.platform()},
    )
