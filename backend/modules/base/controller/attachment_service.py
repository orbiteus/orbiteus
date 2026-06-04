"""Attachment upload/download orchestration (filestore + metadata + RBAC)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import desc, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.attachments import (
    assert_linked_record_access,
    can_browse_all_attachments,
    sanitize_filename,
)
from orbiteus_core.context import RequestContext
from orbiteus_core.exceptions import AccessDenied, NotFound
from orbiteus_core.storage import build_storage_key, get_storage
from modules.base.controller.repositories import AttachmentRepository
from modules.base.model.domain import Attachment
from modules.base.model.mapping import base_attachments_table


class AttachmentService:
    """Coordinates ``base_attachments`` rows with the configured filestore."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_attachments(
        self,
        ctx: RequestContext,
        *,
        q: str | None = None,
        res_model: str | None = None,
        res_id: uuid.UUID | None = None,
        mimetype: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        repo = AttachmentRepository(self.session, ctx)
        await repo._check_model_access("read")

        if res_model and res_id:
            await assert_linked_record_access(
                self.session,
                ctx,
                res_model=res_model,
                res_id=res_id,
                operation="read",
            )
        elif not can_browse_all_attachments(ctx):
            raise HTTPException(
                status_code=403,
                detail="Tenant-wide attachment search requires base.group_system",
            )

        stmt = select(base_attachments_table).where(base_attachments_table.c.active.is_(True))
        if not ctx.is_superadmin and ctx.tenant_id is not None:
            stmt = stmt.where(base_attachments_table.c.tenant_id == ctx.tenant_id)
        if res_model:
            stmt = stmt.where(base_attachments_table.c.res_model == res_model)
        if res_id:
            stmt = stmt.where(base_attachments_table.c.res_id == res_id)
        if mimetype:
            stmt = stmt.where(base_attachments_table.c.mimetype == mimetype)
        if q:
            stmt = stmt.where(base_attachments_table.c.name.ilike(f"%{q}%"))

        total = (
            await self.session.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar_one()

        rows = (
            await self.session.execute(
                stmt.order_by(desc(base_attachments_table.c.create_date))
                .offset(offset)
                .limit(limit)
            )
        ).mappings().all()

        items = [self._row_to_dict(r) for r in rows]
        await self._mark_linked_records_exist(ctx, items)

        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def _mark_linked_records_exist(
        self,
        ctx: RequestContext,
        items: list[dict[str, Any]],
    ) -> None:
        """Set ``res_record_exists`` so the UI can avoid dead links to deleted rows."""
        from orbiteus_core.auto_router import _model_registry

        by_model: dict[str, list[uuid.UUID]] = {}
        for row in items:
            model = row.get("res_model")
            raw_id = row.get("res_id")
            if not model or not raw_id:
                row["res_record_exists"] = False
                continue
            try:
                rid = uuid.UUID(str(raw_id))
            except ValueError:
                row["res_record_exists"] = False
                continue
            by_model.setdefault(model, []).append(rid)

        found_ids: dict[str, set[str]] = {}
        for model, ids in by_model.items():
            entry = _model_registry.get(model)
            if entry is None:
                found_ids[model] = set()
                continue
            repo = entry["repository_class"](self.session, ctx)
            try:
                records, _ = await repo.search(
                    domain=[("id", "in", [str(i) for i in ids])],
                    limit=len(ids),
                )
            except Exception:
                found_ids[model] = set()
                continue
            found_ids[model] = {str(r.id) for r in records}

        for row in items:
            model = row.get("res_model")
            raw_id = row.get("res_id")
            if not model or not raw_id:
                continue
            row["res_record_exists"] = str(raw_id) in found_ids.get(model, set())

    async def upload(
        self,
        ctx: RequestContext,
        *,
        file_bytes: bytes,
        filename: str,
        mimetype: str,
        res_model: str,
        res_id: uuid.UUID,
        description: str = "",
    ) -> dict[str, Any]:
        if not filename:
            raise HTTPException(status_code=400, detail="filename required")
        if len(file_bytes) == 0:
            raise HTTPException(status_code=400, detail="empty file")
        from orbiteus_core.config import settings

        if len(file_bytes) > settings.attachment_max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"file too large (max {settings.attachment_max_bytes} bytes)",
            )

        await assert_linked_record_access(
            self.session,
            ctx,
            res_model=res_model,
            res_id=res_id,
            operation="write",
        )

        if ctx.tenant_id is None:
            raise HTTPException(status_code=400, detail="tenant context required")

        attachment_id = uuid.uuid4()
        safe_name = sanitize_filename(filename)
        store_key = build_storage_key(str(ctx.tenant_id), str(attachment_id), safe_name)
        storage = get_storage()

        await storage.put(store_key, file_bytes)
        repo = AttachmentRepository(self.session, ctx)
        now = datetime.now(timezone.utc)
        try:
            obj = await repo.create(
                {
                    "id": attachment_id,
                    "name": safe_name,
                    "res_model": res_model,
                    "res_id": res_id,
                    "mimetype": mimetype or "application/octet-stream",
                    "file_size": len(file_bytes),
                    "store_fname": store_key,
                    "url": None,
                    "description": description[:500],
                    "create_date": now,
                    "write_date": now,
                }
            )
        except Exception:
            await storage.delete(store_key)
            raise

        return self._attachment_to_dict(obj)

    async def upload_portal(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID | None,
        res_model: str,
        res_id: uuid.UUID,
        file_bytes: bytes,
        filename: str,
        mimetype: str,
        description: str = "",
    ) -> dict[str, Any]:
        """Portal share-link upload — token gate is handled by the router."""
        from orbiteus_core.config import settings

        portal_cap = min(settings.attachment_max_bytes, 25 * 1024 * 1024)
        if len(file_bytes) > portal_cap:
            raise HTTPException(status_code=413, detail="file too large (25 MB cap)")
        if not filename:
            raise HTTPException(status_code=400, detail="filename required")

        attachment_id = uuid.uuid4()
        safe_name = sanitize_filename(filename)
        store_key = build_storage_key(str(tenant_id), str(attachment_id), safe_name)
        storage = get_storage()
        await storage.put(store_key, file_bytes)

        now = datetime.now(timezone.utc)
        try:
            await self.session.execute(
                insert(base_attachments_table).values(
                    id=attachment_id,
                    tenant_id=tenant_id,
                    company_id=None,
                    create_date=now,
                    write_date=now,
                    active=True,
                    custom_fields={},
                    created_by_id=user_id,
                    modified_by_id=user_id,
                    name=safe_name,
                    res_model=res_model,
                    res_id=res_id,
                    mimetype=mimetype or "application/octet-stream",
                    file_size=len(file_bytes),
                    store_fname=store_key,
                    url=None,
                    description=description[:500],
                )
            )
        except Exception:
            await storage.delete(store_key)
            raise

        return {
            "id": str(attachment_id),
            "name": safe_name,
            "filename": safe_name,
            "size": len(file_bytes),
            "store_fname": store_key,
            "res_model": res_model,
            "res_id": str(res_id),
        }

    async def get_metadata(
        self,
        ctx: RequestContext,
        attachment_id: uuid.UUID,
    ) -> dict[str, Any]:
        att = await self._get_attachment(ctx, attachment_id, operation="read")
        return self._attachment_to_dict(att)

    async def download(
        self,
        ctx: RequestContext,
        attachment_id: uuid.UUID,
    ) -> tuple[Attachment, bytes]:
        att = await self._get_attachment(ctx, attachment_id, operation="read")
        if not att.store_fname:
            raise HTTPException(status_code=404, detail="attachment binary missing")
        try:
            data = await get_storage().get(att.store_fname)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="attachment file not found in storage") from exc
        return att, data

    async def delete(
        self,
        ctx: RequestContext,
        attachment_id: uuid.UUID,
    ) -> None:
        att = await self._get_attachment(ctx, attachment_id, operation="write")
        await self._remove_attachment(ctx, attachment_id, att.store_fname)

    async def _remove_attachment(
        self,
        ctx: RequestContext,
        attachment_id: uuid.UUID,
        store_fname: str | None,
    ) -> None:
        """Drop metadata + binary without re-checking the linked business record."""
        repo = AttachmentRepository(self.session, ctx)
        await repo._check_model_access("unlink")
        try:
            await repo.hard_delete(attachment_id)
        except NotFound:
            return
        if store_fname:
            try:
                await get_storage().delete(store_fname)
            except FileNotFoundError:
                pass

    async def delete_for_linked_record(
        self,
        *,
        tenant_id: uuid.UUID | None,
        res_model: str,
        res_id: uuid.UUID,
    ) -> int:
        """Remove all active attachments for a deleted/unlinked business record."""
        ctx = RequestContext(is_superadmin=True, tenant_id=tenant_id)
        stmt = select(base_attachments_table).where(
            base_attachments_table.c.active.is_(True),
            base_attachments_table.c.res_model == res_model,
            base_attachments_table.c.res_id == res_id,
        )
        if tenant_id is not None:
            stmt = stmt.where(base_attachments_table.c.tenant_id == tenant_id)
        rows = (await self.session.execute(stmt)).mappings().all()
        for row in rows:
            await self._remove_attachment(ctx, row["id"], row.get("store_fname"))
        return len(rows)

    async def purge_orphan_attachments(self, ctx: RequestContext) -> int:
        """Delete attachment rows whose ``res_model`` / ``res_id`` no longer resolve."""
        if not can_browse_all_attachments(ctx):
            raise HTTPException(
                status_code=403,
                detail="Orphan cleanup requires base.group_system",
            )
        removed = 0
        page_size = 100
        while True:
            page = await self.list_attachments(ctx, limit=page_size, offset=0)
            orphans = [
                row for row in page["items"] if row.get("res_record_exists") is False
            ]
            if not orphans:
                break
            for row in orphans:
                att_id = uuid.UUID(str(row["id"]))
                store_key = await self._store_fname_for_id(att_id)
                await self._remove_attachment(ctx, att_id, store_key)
                removed += 1
        return removed

    async def _store_fname_for_id(self, attachment_id: uuid.UUID) -> str | None:
        row = (
            await self.session.execute(
                select(base_attachments_table.c.store_fname).where(
                    base_attachments_table.c.id == attachment_id
                )
            )
        ).first()
        return row[0] if row else None

    async def _get_attachment(
        self,
        ctx: RequestContext,
        attachment_id: uuid.UUID,
        *,
        operation: str,
    ) -> Attachment:
        repo = AttachmentRepository(self.session, ctx)
        try:
            att = await repo.get(attachment_id)
        except NotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except AccessDenied as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

        if att.res_model and att.res_id:
            await assert_linked_record_access(
                self.session,
                ctx,
                res_model=att.res_model,
                res_id=att.res_id,
                operation=operation,
            )
        return att

    @staticmethod
    def _attachment_to_dict(att: Attachment) -> dict[str, Any]:
        return {
            "id": str(att.id),
            "tenant_id": str(att.tenant_id) if att.tenant_id else None,
            "name": att.name,
            "res_model": att.res_model,
            "res_id": str(att.res_id) if att.res_id else None,
            "mimetype": att.mimetype,
            "file_size": att.file_size,
            "description": att.description,
            "create_date": att.create_date.isoformat() if att.create_date else None,
            "created_by_id": str(att.created_by_id) if att.created_by_id else None,
        }

    @staticmethod
    def _row_to_dict(row: Any) -> dict[str, Any]:
        return {
            "id": str(row["id"]),
            "tenant_id": str(row["tenant_id"]) if row["tenant_id"] else None,
            "name": row["name"],
            "res_model": row["res_model"],
            "res_id": str(row["res_id"]) if row["res_id"] else None,
            "mimetype": row["mimetype"],
            "file_size": row["file_size"],
            "description": row["description"] or "",
            "create_date": row["create_date"].isoformat() if row["create_date"] else None,
            "created_by_id": str(row["created_by_id"]) if row["created_by_id"] else None,
        }
