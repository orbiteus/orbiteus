"""Base module custom endpoints (beyond auto-CRUD)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext
from orbiteus_core.db import get_session
from orbiteus_core.security.middleware import require_superadmin

router = APIRouter(tags=["base"])

_BRANDING_KEYS = ("app.name", "app.logo_url", "app.favicon_url")
_BRANDING_DEFAULTS = {
    "app.name": "Orbiteus",
    "app.logo_url": "/branding/logo.svg",
    "app.favicon_url": "/branding/logo.svg",
}


@router.get("/branding")
async def get_branding(session: AsyncSession = Depends(get_session)) -> dict:
    """Return public branding config (no auth required)."""
    from modules.base.repositories import IrConfigParamRepository
    ctx = RequestContext(is_superadmin=True)
    repo = IrConfigParamRepository(session, ctx)
    result = dict(_BRANDING_DEFAULTS)
    for key in _BRANDING_KEYS:
        try:
            items, _ = await repo.search(domain=[("key", "=", key)], limit=1)
            if items:
                result[key] = items[0].value or _BRANDING_DEFAULTS[key]
        except Exception:
            pass
    return {
        "name": result["app.name"],
        "logo_url": result["app.logo_url"],
        "favicon_url": result["app.favicon_url"],
    }


@router.get("/health", include_in_schema=True)
async def health() -> dict:
    """System health check."""
    return {"status": "ok", "service": "orbiteus-backend"}


@router.get("/ui-config")
async def get_ui_config() -> dict:
    """Return schema-driven UI configuration for all registered modules.

    Uses in-memory registry — no DB query, always consistent with loaded modules.
    """
    from orbiteus_core.ui_config import build_ui_config
    return build_ui_config()


@router.get("/modules", dependencies=[Depends(require_superadmin)])
async def list_modules() -> dict:
    """List all registered modules and their load order."""
    from orbiteus_core.registry import registry

    return {
        "modules": registry.loaded_modules,
        "total": len(registry.loaded_modules),
    }


@router.get("/menus")
async def get_menu_tree(
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_superadmin),
) -> dict:
    """Return the full ir_ui_menu tree for the Admin UI sidebar."""
    from modules.base.repositories import IrUiMenuRepository

    repo = IrUiMenuRepository(session, ctx)
    menus, total = await repo.search(limit=500)

    # Build tree structure
    menu_dict = {str(m.id): {"id": str(m.id), "name": m.name,
                               "parent_id": str(m.parent_id) if m.parent_id else None,
                               "sequence": m.sequence, "icon": m.icon,
                               "children": []} for m in menus}

    roots = []
    for menu in menu_dict.values():
        parent_id = menu["parent_id"]
        if parent_id and parent_id in menu_dict:
            menu_dict[parent_id]["children"].append(menu)
        else:
            roots.append(menu)

    return {"menus": sorted(roots, key=lambda x: x["sequence"])}
