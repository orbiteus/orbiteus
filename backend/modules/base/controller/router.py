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
    from modules.base.controller.repositories import IrConfigParamRepository
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
    from modules.base.controller.repositories import IrUiMenuRepository

    repo = IrUiMenuRepository(session, ctx)
    menus, total = await repo.search(limit=500)

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


@router.get("/view")
async def get_view(
    model: str,
    type: str = "form",
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_superadmin),
) -> dict:
    """Return resolved view arch for a given model and view type.

    Applies XPath inheritance chain and returns final XML arch as a string.
    Used by frontend to render views generically without hardcoded pages.

    Query params:
      - model: e.g. crm.customer
      - type: form / list / kanban / calendar / search  (default: form)
    """
    from modules.base.controller.repositories import IrUiViewRepository
    from orbiteus_core.view_loader import resolve_arch

    repo = IrUiViewRepository(session, ctx)

    # Load base view (no inherit_id, matching model+type)
    base_views, _ = await repo.search(
        domain=[("model", "=", model), ("type", "=", type), ("active", "=", True)],
        limit=50,
    )

    if not base_views:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"No view found for model={model} type={type}")

    # Split into base (inherit_id=None) and inherited
    base = next((v for v in base_views if v.inherit_id is None), None)
    if base is None:
        # All views are inherited — use the first as base
        base = base_views[0]

    inherited = [v for v in base_views if v.inherit_id is not None]
    inherited.sort(key=lambda v: v.priority)

    resolved = resolve_arch(base.arch, [v.arch for v in inherited])

    return {
        "model": model,
        "type": type,
        "name": base.name,
        "arch": resolved,
        "inherit_count": len(inherited),
    }


def _pydantic_to_ui_type(name: str, annotation: object) -> str:
    ann = str(annotation)
    if "bool" in ann:
        return "boolean"
    if "int" in ann or "float" in ann:
        return "number"
    if "UUID" in ann and name.endswith("_id"):
        return "select"
    if name == "email":
        return "email"
    if name in ("phone", "mobile"):
        return "tel"
    if name.endswith("_date") or name in ("date", "close_date"):
        return "date"
    if name in ("notes", "description") or name.endswith("_html"):
        return "textarea"
    return "text"


_SKIP_FIELDS = {"tenant_id", "company_id", "tags", "workflow_run_id"}


def _extract_schema_fields(write_schema: type) -> list[dict]:
    result = []
    for name, field_info in write_schema.model_fields.items():
        if name in _SKIP_FIELDS:
            continue
        result.append({
            "name": name,
            "type": _pydantic_to_ui_type(name, field_info.annotation),
            "required": field_info.is_required(),
            "label": name.replace("_", " ").title(),
        })
    return result


@router.get("/ui-config")
async def get_ui_config() -> dict:
    """Return full UI configuration for dynamic frontend rendering.

    Uses in-memory registry (XML views + Pydantic schema introspection) —
    no DB query needed, always consistent with the loaded modules.
    """
    from orbiteus_core.ui_config import build_ui_config
    return build_ui_config()


@router.post("/rbac/reload", dependencies=[Depends(require_superadmin)])
async def reload_rbac(
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_superadmin),
) -> dict:
    """Reload RBAC cache from YAML files and re-seed to DB.

    Use after changing security/access.yaml files without restarting the server.
    Requires superadmin role.
    """
    from orbiteus_core.security import rbac
    from orbiteus_core.registry import registry

    # Clear existing cache
    rbac._model_access.clear()
    rbac._record_rules.clear()

    # Re-apply all YAML security configs
    from orbiteus_core.security_loader import apply_security_to_cache, seed_security_to_db

    reloaded = []
    for name in registry.loaded_modules:
        desc = registry.get_module(name)
        config = getattr(desc, "_security_config", None)
        if config:
            apply_security_to_cache(config)
            await seed_security_to_db(config, session, ctx)
            reloaded.append(name)

    await session.commit()

    return {
        "status": "reloaded",
        "modules": reloaded,
        "access_entries": sum(len(v) for v in rbac._model_access.values()),
        "record_rules": sum(len(v) for v in rbac._record_rules.values()),
    }
