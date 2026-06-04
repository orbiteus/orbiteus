"""RBAC engine — Level 1 (model access) + Level 2 (record rules).

Storage layout
--------------
The authoritative store stays in Postgres (`base_model_access`, `base_rules`).
Cache lives in **Redis** with a process-local L1 mirror so the hot path
on every request stays in-memory:

    L1  (in-process dict)   ← read by `check_model_access` / `apply_record_rules`
     ↑ refreshed by pub/sub listener
    L2  (Redis hashes)      ← `rbac:access`, `rbac:rules`, `rbac:version`
     ↑ written by `reload_access_cache`
    DB  (base_model_access, base_rules)

Cross-replica invalidation
--------------------------
Every replica subscribes to the `rbac.invalidate` channel at startup
(`start_invalidator()`). When any replica calls `reload_access_cache`
(after a YAML/seed reload or an `base_model_access` mutation) it bumps
`rbac:version` and publishes the new value on `rbac.invalidate`. Other
replicas refresh their L1 from Redis on receipt — typically <50ms.

Open-fail policy
----------------
Redis outage MUST NOT lock everyone out. If the listener crashes the
last successfully-loaded L1 keeps serving requests; if Redis was never
reachable and the cache is empty, requests are denied (closed-fail) so
we never accidentally bypass RBAC. This matches the behaviour the
existing tests assert.

Backward compatibility
----------------------
`_model_access` and `_record_rules` are aliases of the L1 dictionaries
so existing direct readers (`ai/resolver.py`, `security_loader.py`,
`modules/crm/security.py`) continue to work without changes — they
are mutated in place via `.clear()` / `.update()` / `.setdefault()`.

See ADR-0003 (Redis as cross-cutting backplane) and DoD §2.4 / §7.1.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from sqlalchemy import Select

from orbiteus_core.context import RequestContext

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# L1 cache (in-process)
# ---------------------------------------------------------------------------
_l1_access: dict[str, dict[str, dict[str, bool]]] = {}
_l1_rules: dict[str, list[dict[str, Any]]] = {}
_l1_version: int = 0

# Backwards-compat aliases. THESE MUST point at the same dict objects so
# external readers (resolver.py, crm/security.py) see the same data.
_model_access = _l1_access
_record_rules = _l1_rules


# ---------------------------------------------------------------------------
# Redis keys / channel
# ---------------------------------------------------------------------------
_KEY_ACCESS = "rbac:access"
_KEY_RULES = "rbac:rules"
_KEY_VERSION = "rbac:version"
_CHANNEL_INVALIDATE = "rbac.invalidate"


def _serialize_rule(rule: dict[str, Any]) -> dict[str, Any]:
    """Strip non-JSON-safe values (UUIDs, datetimes) before persisting."""
    out = {}
    for k, v in rule.items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            out[k] = v
        elif isinstance(v, (list, tuple)):
            out[k] = list(v)
        elif isinstance(v, dict):
            out[k] = v
        else:
            out[k] = str(v)
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_rbac_version() -> int:
    """Return the in-process RBAC cache version (mirrors Redis `rbac:version`)."""
    return _l1_version


async def reload_access_cache(
    access_entries: list[dict[str, Any]],
    rule_entries: list[dict[str, Any]],
) -> None:
    """Persist the access matrix to Redis, refresh L1 locally, and notify
    every other replica via `rbac.invalidate`.

    Called by:
      * application lifespan startup (after `seed_security_to_db`)
      * EventBus subscriber when `base_model_access` / `base_rules` mutates
    """
    global _l1_version

    # 1) Build in-memory representation (L1) — shared with `_model_access`
    #    and `_record_rules` aliases.
    _l1_access.clear()
    for entry in access_entries:
        role = entry["role_name"]
        model = entry["model_name"]
        _l1_access.setdefault(role, {})[model] = {
            "read": bool(entry.get("perm_read", False)),
            "write": bool(entry.get("perm_write", False)),
            "create": bool(entry.get("perm_create", False)),
            "unlink": bool(entry.get("perm_unlink", False)),
        }

    _l1_rules.clear()
    for rule in rule_entries:
        model = rule["model_name"]
        _l1_rules.setdefault(model, []).append(_serialize_rule(rule))

    # 2) Persist to Redis + bump version + publish invalidate.
    try:
        from orbiteus_core.cache import get_redis

        client = get_redis()
        access_blob = json.dumps(_l1_access)
        rules_blob = json.dumps(_l1_rules, default=str)
        await client.set(_KEY_ACCESS, access_blob)
        await client.set(_KEY_RULES, rules_blob)
        new_version = await client.incr(_KEY_VERSION)
        _l1_version = int(new_version)
        await client.publish(_CHANNEL_INVALIDATE, str(new_version))
    except Exception:  # noqa: BLE001
        # Redis outage must not block startup — the L1 is still populated
        # in this replica and will be re-pushed on the next reload.
        logger.exception("rbac.cache.redis_write_failed")

    logger.info(
        "rbac.cache.reloaded access=%d rules=%d version=%d",
        len(access_entries),
        sum(len(v) for v in _l1_rules.values()),
        _l1_version,
    )


async def _refresh_from_redis() -> bool:
    """Pull the latest access matrix from Redis into L1.

    Returns True when something was loaded, False otherwise (e.g. Redis
    is down and L1 is preserved).
    """
    global _l1_version
    try:
        from orbiteus_core.cache import get_redis

        client = get_redis()
        access_raw = await client.get(_KEY_ACCESS)
        rules_raw = await client.get(_KEY_RULES)
        ver_raw = await client.get(_KEY_VERSION)
    except Exception:  # noqa: BLE001
        logger.warning("rbac.cache.redis_refresh_failed", exc_info=True)
        return False

    if access_raw is None and rules_raw is None:
        return False

    if access_raw is not None:
        _l1_access.clear()
        try:
            _l1_access.update(json.loads(access_raw))
        except json.JSONDecodeError:
            logger.warning("rbac.cache.access_decode_failed")
    if rules_raw is not None:
        _l1_rules.clear()
        try:
            _l1_rules.update(json.loads(rules_raw))
        except json.JSONDecodeError:
            logger.warning("rbac.cache.rules_decode_failed")
    if ver_raw is not None:
        try:
            _l1_version = int(ver_raw)
        except (TypeError, ValueError):
            pass
    return True


async def check_model_access(ctx: RequestContext, model_name: str, operation: str) -> bool:
    """Return True if the current user has the given permission on the model."""
    if ctx.is_superadmin:
        return True

    # Lazy first-load — protects unit tests that import this module
    # before lifespan has had a chance to run.
    if not _l1_access:
        await _refresh_from_redis()

    if not _l1_access:
        # Closed-fail: better to lock down than to leak data when nobody
        # has populated the cache yet.
        logger.warning("rbac.cache.empty model=%s op=%s", model_name, operation)
        return False

    for role in ctx.roles:
        perms = _l1_access.get(role, {}).get(model_name, {})
        if perms.get(operation, False):
            return True
    return False


def apply_record_rules(
    stmt: Select,
    table: Any,
    ctx: RequestContext,
    model_name: str,
) -> Select:
    """Apply record rules as SQLAlchemy WHERE conditions."""
    if ctx.is_superadmin:
        return stmt

    rules = _l1_rules.get(model_name, [])
    for rule in rules:
        if not rule.get("global", False):
            rule_roles = rule.get("roles", [])
            if rule_roles and not any(r in ctx.roles for r in rule_roles):
                continue

        domain = rule.get("domain", [])
        for triple in domain:
            if isinstance(triple, dict):
                field_name = triple.get("field")
                operator = triple.get("op", "=")
                value = triple.get("value")
            elif isinstance(triple, (list, tuple)) and len(triple) == 3:
                field_name, operator, value = triple
            else:
                continue
            if not field_name:
                continue
            col = table.c.get(field_name)
            if col is None:
                continue
            if value == "current_user":
                value = ctx.user_id
            elif value == "current_company":
                value = ctx.company_id

            if operator == "=":
                stmt = stmt.where(col == value)
            elif operator == "!=":
                stmt = stmt.where(col != value)
            elif operator == "in":
                stmt = stmt.where(col.in_(value))

    return stmt


# ---------------------------------------------------------------------------
# Cross-replica invalidator (background task)
# ---------------------------------------------------------------------------

_INVALIDATOR_TASK: asyncio.Task | None = None


async def start_invalidator() -> None:
    """Start the background Redis pub/sub listener.

    Idempotent — calling twice is a no-op. Designed to run for the
    lifetime of the FastAPI application.
    """
    global _INVALIDATOR_TASK
    if _INVALIDATOR_TASK is not None and not _INVALIDATOR_TASK.done():
        return
    _INVALIDATOR_TASK = asyncio.create_task(
        _invalidator_loop(),
        name="rbac-invalidator",
    )


async def stop_invalidator() -> None:
    global _INVALIDATOR_TASK
    if _INVALIDATOR_TASK is None:
        return
    _INVALIDATOR_TASK.cancel()
    try:
        await _INVALIDATOR_TASK
    except (asyncio.CancelledError, Exception):  # noqa: BLE001
        pass
    _INVALIDATOR_TASK = None


async def _invalidator_loop() -> None:
    """Subscribe to `rbac.invalidate` and refresh L1 on every notification.

    Reconnects with exponential back-off on transient Redis errors.
    """
    backoff = 1.0
    while True:
        pubsub = None
        try:
            from orbiteus_core.cache import get_redis

            client = get_redis()
            pubsub = client.pubsub()
            await pubsub.subscribe(_CHANNEL_INVALIDATE)
            backoff = 1.0
            logger.info("rbac.invalidator.subscribed channel=%s", _CHANNEL_INVALIDATE)

            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=30.0,
                )
                if message is None:
                    continue
                if message.get("type") == "message":
                    new_version = message.get("data")
                    refreshed = await _refresh_from_redis()
                    logger.info(
                        "rbac.cache.invalidated version=%s refreshed=%s",
                        new_version, refreshed,
                    )
        except asyncio.CancelledError:
            if pubsub is not None:
                try:
                    await pubsub.unsubscribe()
                    # `aclose()` since redis-py 5.0.1 (`close()` deprecated).
                    if hasattr(pubsub, "aclose"):
                        await pubsub.aclose()
                    else:
                        await pubsub.close()
                except Exception:  # noqa: BLE001
                    pass
            raise
        except Exception:  # noqa: BLE001
            logger.warning("rbac.invalidator.disconnected", exc_info=True)
            await asyncio.sleep(min(backoff, 30))
            backoff *= 2


# ---------------------------------------------------------------------------
# EventBus → reload bridge
# ---------------------------------------------------------------------------

_REGISTERED = False


def register_rbac_invalidator() -> None:
    """Wire the EventBus so any mutation of `base_model_access` / `base_rules`
    triggers a fresh reload of the cache (with cross-replica fan-out via
    pub/sub).

    Idempotent.
    """
    global _REGISTERED
    if _REGISTERED:
        return
    from orbiteus_core.events import event_bus

    async def _on_record(payload: dict[str, Any]) -> None:
        model = payload.get("model")
        if model not in ("base.model-access", "base.record-rule"):
            return
        try:
            await _reload_from_db()
        except Exception:  # noqa: BLE001
            logger.exception("rbac.cache.reload_from_db_failed")

    for event_name in ("record.created", "record.updated", "record.deleted"):
        event_bus.subscribe(event_name, _on_record)
    _REGISTERED = True
    logger.info("rbac.invalidator.registered_on_eventbus")


async def _reload_from_db() -> None:
    """Pull `base_model_access` + `base_rules` from Postgres and refresh both
    Redis and L1 (which also publishes invalidation)."""
    from sqlalchemy import select

    from modules.base.model.mapping import base_model_access_table, base_rules_table
    from orbiteus_core.db import AsyncSessionFactory

    async with AsyncSessionFactory() as session:
        access_rows = (
            await session.execute(select(base_model_access_table))
        ).mappings().all()
        rule_rows = (
            await session.execute(select(base_rules_table))
        ).mappings().all()

    access_dicts = [
        {
            "role_name": r.get("role_name", ""),
            "model_name": r.get("model_name", ""),
            "perm_read": bool(r.get("perm_read", False)),
            "perm_write": bool(r.get("perm_write", False)),
            "perm_create": bool(r.get("perm_create", False)),
            "perm_unlink": bool(r.get("perm_unlink", False)),
        }
        for r in access_rows
    ]

    def _normalize_list(val: Any) -> list[Any]:
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            from orbiteus_core.security_loader import normalize_domain

            return normalize_domain(val)
        return []

    rule_dicts = [
        {
            "model_name": r.get("model_name", ""),
            "roles": _normalize_list(r.get("roles", [])),
            "domain": _normalize_list(r.get("domain_force", [])),
            "global": bool(r.get("is_global", False)),
        }
        for r in rule_rows
    ]
    await reload_access_cache(access_dicts, rule_dicts)
