"""Module catalog — registry metadata + per-instance enable flags.

Enable state is stored in ``base_config_params`` as
``module.<name>.enabled`` (``"true"`` / ``"false"``). Missing key ⇒ enabled.

Core engine modules (``base``, ``auth``) are always on and not toggleable.
Disabling a product module hides it from ``ui-config`` and the admin sidebar;
API routes remain mounted until process restart (runtime unload is deferred).
"""
from __future__ import annotations

import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext
from orbiteus_core.registry import registry

CORE_MODULES = frozenset({"base", "auth"})
_ENABLED_MAP_TTL_SEC = 5.0
_enabled_map_cache: tuple[float, dict[str, bool]] | None = None


def clear_enabled_map_cache() -> None:
    """Invalidate after PATCH /modules/{name} or tests."""
    global _enabled_map_cache
    _enabled_map_cache = None
_ENABLED_PREFIX = "module."
_ENABLED_SUFFIX = ".enabled"


def config_key_for_module(module_name: str) -> str:
    return f"{_ENABLED_PREFIX}{module_name}{_ENABLED_SUFFIX}"


def parse_enabled_value(raw: str | None) -> bool:
    if raw is None:
        return True
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


async def load_enabled_map(
    session: AsyncSession,
    ctx: RequestContext | None = None,
) -> dict[str, bool]:
    """Return ``{module_name: enabled}`` for every registered module."""
    global _enabled_map_cache

    now = time.monotonic()
    if _enabled_map_cache is not None:
        cached_at, cached = _enabled_map_cache
        if now - cached_at < _ENABLED_MAP_TTL_SEC:
            return dict(cached)

    from modules.base.controller.repositories import ConfigParamRepository

    # Instance-wide admin toggles — not tenant-scoped business data.
    read_ctx = RequestContext(is_superadmin=True)
    repo = ConfigParamRepository(session, read_ctx)
    keys = [config_key_for_module(name) for name in registry.loaded_modules]
    enabled: dict[str, bool] = {name: True for name in registry.loaded_modules}

    if keys:
        rows, _ = await repo.search(domain=[("key", "in", keys)], limit=len(keys))
        for row in rows:
            key = row.key
            if key.startswith(_ENABLED_PREFIX) and key.endswith(_ENABLED_SUFFIX):
                mod = key[len(_ENABLED_PREFIX) : -len(_ENABLED_SUFFIX)]
                enabled[mod] = parse_enabled_value(row.value)

    for core in CORE_MODULES:
        if core in enabled:
            enabled[core] = True

    _enabled_map_cache = (now, dict(enabled))
    return enabled


def is_module_enabled(module_name: str, enabled_map: dict[str, bool] | None) -> bool:
    if module_name in CORE_MODULES:
        return True
    if not enabled_map:
        return True
    return enabled_map.get(module_name, True)


def build_module_catalog(enabled_map: dict[str, bool] | None = None) -> list[dict[str, Any]]:
    """Serialize registered modules for the admin catalog UI."""
    items: list[dict[str, Any]] = []
    for idx, name in enumerate(registry.loaded_modules):
        desc = registry.get_module(name)
        manifest = desc.manifest
        core = name in CORE_MODULES
        enabled = is_module_enabled(name, enabled_map)
        items.append({
            "name": name,
            "label": manifest.get("name", name.title()),
            "version": manifest.get("version", "?"),
            "category": manifest.get("category", ""),
            "depends_on": list(manifest.get("depends_on", [])),
            "auto_install": bool(manifest.get("auto_install", False)),
            "models": list(manifest.get("models", [])),
            "model_count": len(manifest.get("models", [])),
            "load_order": idx + 1,
            "core": core,
            "toggleable": not core,
            "enabled": enabled,
        })
    return items


async def set_module_enabled(
    session: AsyncSession,
    ctx: RequestContext,
    module_name: str,
    enabled: bool,
) -> dict[str, Any]:
    if module_name not in registry.loaded_modules:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Module '{module_name}' is not registered")
    if module_name in CORE_MODULES:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Core modules cannot be disabled")

    from modules.base.controller.repositories import ConfigParamRepository

    key = config_key_for_module(module_name)
    value = "true" if enabled else "false"
    repo = ConfigParamRepository(session, ctx)
    existing, _ = await repo.search(domain=[("key", "=", key)], limit=1)
    if existing:
        await repo.update(existing[0].id, {"value": value})
    else:
        await repo.create({
            "key": key,
            "value": value,
            "description": f"Admin toggle: enable/disable module '{module_name}'",
        })
    await session.commit()

    clear_enabled_map_cache()
    from orbiteus_core.i18n_registry import clear_ui_translation_cache

    clear_ui_translation_cache()
    enabled_map = await load_enabled_map(session, ctx)
    catalog = build_module_catalog(enabled_map)
    row = next(m for m in catalog if m["name"] == module_name)
    return row
