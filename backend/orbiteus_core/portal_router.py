"""Public portal endpoints (PR 12 + PR final mutations).

- `GET  /api/portal/exchange?token=<jwt>` — validate share-link, return resource.
- `POST /api/portal/comment`              — append a comment when token has `comment`.
- `POST /api/portal/attachment`           — upload an attachment when token has `attach_file`.

Every mutation re-validates the token, refuses cross-tenant payloads, and
records the action in the audit log with `actor=portal`.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.db import get_session
from orbiteus_core.sharing import decode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portal", tags=["portal"])


def _require_permission(perms: list[str], required: str) -> None:
    if required not in perms:
        raise HTTPException(
            status_code=403,
            detail={"code": "portal.permission_denied", "required": required},
        )


async def _audit_portal(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    operation: str,
    resource_model: str,
    resource_id: uuid.UUID,
    diff: dict[str, Any],
) -> None:
    """Write an `base_audit_log` row with `actor=portal`."""
    from modules.base.model.mapping import base_audit_log_table as audit

    await session.execute(
        insert(audit).values(
            id=uuid.uuid4(),
            create_date=datetime.now(timezone.utc),
            write_date=datetime.now(timezone.utc),
            tenant_id=tenant_id,
            actor="portal",
            user_id=user_id,
            request_id=None,
            model=resource_model,
            record_id=resource_id,
            operation=operation,
            diff=diff,
            metadata={"scope": "portal"},
        )
    )


@router.get("/exchange")
async def exchange(
    token: str = Query(...),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Validate a share-link token and return a minimal resource payload."""
    try:
        payload = decode(token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Resolve the resource against the engine's registered models.
    from orbiteus_core.auto_router import _model_registry  # type: ignore[attr-defined]

    entry = _model_registry.get(payload.resource_model)
    if entry is None:
        raise HTTPException(status_code=404, detail="resource model not registered")

    table = entry["table"]
    row = (
        await session.execute(
            select(table).where(table.c.id == payload.resource_id)
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="resource not found")

    if row.get("tenant_id") and str(row["tenant_id"]) != str(payload.tenant_id):
        raise HTTPException(status_code=403, detail="cross-tenant share rejected")

    safe_payload: dict = {}
    for key, value in row.items():
        if key in {"id", "tenant_id", "company_id", "create_date", "write_date"}:
            continue
        # Stringify uuids/datetimes so the JSON encoder is happy.
        safe_payload[key] = str(value) if hasattr(value, "isoformat") or hasattr(value, "hex") else value

    return {
        "resource_model": payload.resource_model,
        "resource_id": str(payload.resource_id),
        "permissions": payload.permissions,
        # Surface tenant_id so the portal-ui realtime client can build
        # the canonical `tenant:{tid}:model:{model}:record:{rid}` topic
        # without an extra round-trip. The id is already inside the
        # signed token; we are not leaking anything.
        "tenant_id": str(payload.tenant_id),
        # Portal "view declaration" (DoD §12.5): the resource itself
        # is ALWAYS read-only from the portal — mutations live behind
        # the dedicated `/comment` + `/attachment` endpoints and are
        # gated by their own permission strings on the share token.
        # If a future module wants to expose a writable field via the
        # portal, that field has to land in an explicit "portal" view
        # declaration; the default is locked down.
        "view_mode": "readonly",
        # Frontend uses this to know which mutation surfaces to render.
        "available_mutations": _mutations_for_permissions(payload.permissions),
        "payload": safe_payload,
    }


def _mutations_for_permissions(perms: list[str]) -> list[str]:
    """Map share-token permissions to the mutation endpoints they unlock.

    The frontend reads this list to know whether to render the
    "Add comment" / "Upload attachment" surfaces. Anything not on
    this list MUST stay hidden — the backend re-checks the same
    permission strings before accepting the mutation, so this is a
    UX hint, not a security boundary.
    """
    mapping = {
        "comment":     "portal.comment",
        "attach_file": "portal.attachment",
    }
    return [mapping[p] for p in perms if p in mapping]


# ---------------------------------------------------------------------------
# Portal-scoped realtime (DoD §12.6) — share-token authenticated SSE.
# ---------------------------------------------------------------------------
#
# The standard `/api/realtime/subscribe` requires a normal `access` JWT
# with `scope=internal`. Portal users only have a share-link token
# (`type=portal_share`, `scope=portal`), so we expose a dedicated
# endpoint that:
#   1. Decodes + validates the share token (TTL, signature, scope).
#   2. Asserts the requested topic targets *exactly* the resource the
#      token grants access to. No "subscribe to a different model in
#      the same tenant" — the share-token's blast radius is one
#      record.
#   3. Forwards into the shared `stream_topics(...)` async generator,
#      so the same Redis pub/sub backplane drives both admin-ui and
#      portal-ui clients.

@router.get("/realtime")
async def portal_realtime(
    token: str = Query(..., description="Share-link JWT issued by /api/auth/share"),
    topic: list[str] = Query(default=[], description="Realtime topic(s) to subscribe to"),
):
    from fastapi.responses import StreamingResponse

    from orbiteus_core.realtime import (
        parse_tenant_from_topic,
        stream_topics,
    )

    try:
        share = decode(token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if not topic:
        raise HTTPException(status_code=400, detail="At least one ?topic= is required")

    # Allowed shape — the share token grants access to exactly one
    # resource. We accept either the per-record topic or the per-model
    # list topic for that tenant.
    record_topic = (
        f"tenant:{share.tenant_id}:model:{share.resource_model}"
        f":record:{share.resource_id}"
    )
    list_topic = f"tenant:{share.tenant_id}:model:{share.resource_model}:list"
    allowed = {record_topic, list_topic}
    forbidden = [t for t in topic if t not in allowed]
    if forbidden:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "portal.realtime.topic_forbidden",
                "topics": forbidden,
                "allowed": sorted(allowed),
            },
        )

    # Defensive: every topic MUST also carry the right tenant prefix.
    for t in topic:
        tid = parse_tenant_from_topic(t)
        if tid is None or tid != str(share.tenant_id):
            raise HTTPException(
                status_code=403,
                detail={"code": "portal.realtime.tenant_mismatch", "topic": t},
            )

    headers = {
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    }
    return StreamingResponse(
        stream_topics(topic),
        media_type="text/event-stream",
        headers=headers,
    )


# ---------------------------------------------------------------------------
# Mutations (PR final)
# ---------------------------------------------------------------------------

@router.post("/comment")
async def post_comment(
    body: dict = Body(...),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Append a comment to the shared resource.

    Body: `{ "token": "<jwt>", "body": "Hello world" }`
    """
    token = body.get("token")
    text = (body.get("body") or "").strip()
    if not token or not text:
        raise HTTPException(status_code=400, detail="token and body are required")

    try:
        share = decode(token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _require_permission(share.permissions, "comment")

    # Reuse `base_attachments` as a lightweight comment store keyed by res_model.
    # Comments live in `base_comments` once that table exists; until then we
    # serialize them to the audit log + return a comment id for the UI.
    comment_id = uuid.uuid4()
    await _audit_portal(
        session,
        tenant_id=share.tenant_id,
        user_id=share.issued_by,
        operation="portal.comment",
        resource_model=share.resource_model,
        resource_id=share.resource_id,
        diff={"comment_id": [None, str(comment_id)], "body": [None, text[:2000]]},
    )
    await session.commit()
    return {"id": str(comment_id), "body": text}


@router.post("/attachment")
async def post_attachment(
    token: str = Form(...),
    file: UploadFile = File(...),
    description: str = Form(""),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Upload an attachment to the shared resource.

    Form: `token` + multipart `file`. Honours portal `attach_file` permission.
    Stores the file metadata in `base_attachments` (binary lives outside DB; the
    upload pipeline is finalised in `docs/15-ai-layer.md` follow-up).
    """
    try:
        share = decode(token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    _require_permission(share.permissions, "attach_file")

    if not file.filename:
        raise HTTPException(status_code=400, detail="filename required")

    contents = await file.read()
    if len(contents) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="file too large (25 MB cap)")

    from modules.base.controller.attachment_service import AttachmentService

    result = await AttachmentService(session).upload_portal(
        tenant_id=share.tenant_id,
        user_id=share.issued_by,
        res_model=share.resource_model,
        res_id=share.resource_id,
        file_bytes=contents,
        filename=file.filename,
        mimetype=file.content_type or "application/octet-stream",
        description=description,
    )
    await _audit_portal(
        session,
        tenant_id=share.tenant_id,
        user_id=share.issued_by,
        operation="portal.attachment_upload",
        resource_model=share.resource_model,
        resource_id=share.resource_id,
        diff={
            "attachment_id": [None, result["id"]],
            "filename": [None, file.filename],
            "size": [None, len(contents)],
        },
    )
    await session.commit()
    return result
