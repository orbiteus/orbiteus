"""Shared helpers for the attachment primitive."""
from __future__ import annotations

import re
import uuid
from pathlib import PurePosixPath

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext
from orbiteus_core.exceptions import AccessDenied, NotFound
from orbiteus_core.security.rbac import check_model_access

_UNSAFE_NAME = re.compile(r"[^\w.\- ()]+", re.UNICODE)


def sanitize_filename(name: str) -> str:
    """Strip path components and unsafe characters from an upload filename."""
    base = PurePosixPath(name.replace("\\", "/")).name.strip()
    if not base or base in {".", ".."}:
        base = "upload.bin"
    cleaned = _UNSAFE_NAME.sub("_", base)
    return cleaned[:200] or "upload.bin"


async def assert_linked_record_access(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    res_model: str,
    res_id: uuid.UUID,
    operation: str,
) -> None:
    """Ensure ``ctx`` may ``read`` or ``write`` the linked business record."""
    if not res_model or not res_id:
        raise HTTPException(status_code=400, detail="res_model and res_id are required")

    from orbiteus_core.auto_router import _model_registry

    entry = _model_registry.get(res_model)
    if entry is None:
        raise HTTPException(status_code=400, detail=f"Unknown model: {res_model}")

    rbac_op = "read" if operation == "read" else "write"
    if not ctx.is_superadmin and not await check_model_access(ctx, res_model, rbac_op):
        raise HTTPException(
            status_code=403,
            detail=f"Access denied: {rbac_op} on {res_model}",
        )

    repo = entry["repository_class"](session, ctx)
    try:
        await repo.get(res_id)
    except NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AccessDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def can_browse_all_attachments(ctx: RequestContext) -> bool:
    """Technical browser — tenant-wide search (system admins only)."""
    return ctx.is_superadmin or ctx.has_role("base.group_system")
