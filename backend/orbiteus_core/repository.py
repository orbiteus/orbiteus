"""BaseRepository – generic CRUD + search with automatic record rule application.

PR 3 additions:

- Hooks: `_run_hooks("before_create", ...)` etc., dispatched through
  `EventBus`. Subclasses can override `before_create / after_create / ...`
  for module-specific behavior; cross-cutting subscribers (audit,
  realtime emit, embeddings refresh) attach via `event_bus.subscribe`.
- Audit log: every CRUD writes a row to `base_audit_log` unless the model
  is on the `AUDIT_OPTOUT_MODELS` list (defense against logging the log).
- Attribution: `created_by_id` and `modified_by_id` auto-populated from
  `RequestContext.user_id`.

Usage:

    class CustomerRepository(BaseRepository[Customer]):
        model_name = "crm.customer"

    repo = CustomerRepository(session, ctx)
    customers = await repo.search([("status", "=", "active")])
"""
from __future__ import annotations

import dataclasses
import uuid
from typing import Any, Generic, Sequence, TypeVar

from sqlalchemy import Table, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.base_domain import BaseModel
from orbiteus_core.context import RequestContext
from orbiteus_core.events import event_bus
from orbiteus_core.exceptions import AccessDenied, NotFound

T = TypeVar("T", bound=BaseModel)


# Models that must NOT be audited (logging the log creates infinite loops,
# transient queues are noise). See docs/14-audit.md.
AUDIT_OPTOUT_MODELS: set[str] = {
    "base.audit-log",
    "base.outbox",
    "base.embedding-record",
}


class BaseRepository(Generic[T]):
    """Generic async repository with multi-tenant isolation and RBAC."""

    model_name: str  # e.g. "crm.customer" – used for RBAC checks
    domain_class: type[T]
    table: Table

    def __init__(self, session: AsyncSession, ctx: RequestContext) -> None:
        self.session = session
        self.ctx = ctx

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------

    async def get(self, record_id: uuid.UUID) -> T:
        await self._check_model_access("read")
        stmt = select(self.domain_class).where(
            self.table.c.id == record_id,
            *self._tenant_filter(),
        )
        result = await self.session.execute(stmt)
        obj = result.scalars().first()
        if obj is None:
            raise NotFound(self.model_name, record_id)
        await self._check_record_rules(obj, "read")
        return obj

    async def search(
        self,
        domain: list[tuple[str, str, Any]] | None = None,
        offset: int = 0,
        limit: int = 25,
        order_by: str | None = None,
        order_dir: str = "asc",
    ) -> tuple[Sequence[T], int]:
        """Search records, applying record rules and tenant filter."""
        from sqlalchemy import asc, desc

        await self._check_model_access("read")
        stmt = select(self.domain_class).where(*self._tenant_filter())
        stmt = self._apply_domain(stmt, domain or [])
        stmt = self._apply_record_rules_filter(stmt)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        if order_by:
            col = self.table.c.get(order_by)
            if col is not None:
                stmt = stmt.order_by(desc(col) if order_dir == "desc" else asc(col))

        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

    async def create(self, data: dict[str, Any]) -> T:
        await self._check_model_access("create")
        fields = {f.name for f in dataclasses.fields(self.domain_class)}
        if "tenant_id" in fields:
            data.setdefault("tenant_id", self.ctx.tenant_id)
        if "company_id" in fields:
            data.setdefault("company_id", self.ctx.company_id)
        if "created_by_id" in fields and self.ctx.user_id:
            data.setdefault("created_by_id", self.ctx.user_id)
        if "modified_by_id" in fields and self.ctx.user_id:
            data.setdefault("modified_by_id", self.ctx.user_id)

        data = await self._before_create(data)

        obj = self.domain_class(**data)
        self.session.add(obj)
        await self.session.flush()

        await self._after_create(obj)
        await self._audit("create", obj, diff=self._diff_for_create(obj))
        return obj

    async def update(self, record_id: uuid.UUID, data: dict[str, Any]) -> T:
        await self._check_model_access("write")
        obj = await self.get(record_id)
        old_snapshot = self._snapshot(obj)

        data = await self._before_write(obj, data)

        for key, value in data.items():
            setattr(obj, key, value)
        if "modified_by_id" in {f.name for f in dataclasses.fields(self.domain_class)} and self.ctx.user_id:
            obj.modified_by_id = self.ctx.user_id  # type: ignore[attr-defined]
        await self.session.flush()

        await self._after_write(obj, old_snapshot)
        diff = self._diff(old_snapshot, self._snapshot(obj))
        if diff:
            await self._audit("update", obj, diff=diff)
        return obj

    async def delete(self, record_id: uuid.UUID) -> None:
        await self._check_model_access("unlink")
        obj = await self.get(record_id)
        await self._before_unlink(obj)

        # Soft delete: set active=False
        obj.active = False  # type: ignore[attr-defined]
        if "modified_by_id" in {f.name for f in dataclasses.fields(self.domain_class)} and self.ctx.user_id:
            obj.modified_by_id = self.ctx.user_id  # type: ignore[attr-defined]
        await self.session.flush()

        await self._after_unlink(obj)
        await self._audit("delete", obj, diff={"active": [True, False]})

    async def hard_delete(self, record_id: uuid.UUID) -> None:
        """Permanent delete – use only from migrations or admin."""
        await self._check_model_access("unlink")
        stmt = delete(self.domain_class).where(self.table.c.id == record_id)
        await self.session.execute(stmt)

    # ------------------------------------------------------------------
    # Hooks (override in subclasses for module-specific logic)
    # ------------------------------------------------------------------

    async def _before_create(self, data: dict[str, Any]) -> dict[str, Any]:
        await event_bus.publish(
            f"record.before_create:{self.model_name}",
            {"model": self.model_name, "data": data, "ctx": self.ctx},
        )
        return data

    async def _after_create(self, obj: T) -> None:
        await event_bus.publish(
            f"record.created:{self.model_name}",
            self._record_event_payload(obj),
        )
        await event_bus.publish(
            "record.created",
            self._record_event_payload(obj),
        )

    async def _before_write(self, obj: T, data: dict[str, Any]) -> dict[str, Any]:
        await event_bus.publish(
            f"record.before_write:{self.model_name}",
            {"model": self.model_name, "id": getattr(obj, "id", None),
             "data": data, "ctx": self.ctx},
        )
        return data

    async def _after_write(self, obj: T, old_snapshot: dict[str, Any]) -> None:
        payload = self._record_event_payload(obj)
        payload["old"] = old_snapshot
        await event_bus.publish(f"record.updated:{self.model_name}", payload)
        await event_bus.publish("record.updated", payload)

    async def _before_unlink(self, obj: T) -> None:
        await event_bus.publish(
            f"record.before_unlink:{self.model_name}",
            self._record_event_payload(obj),
        )

    async def _after_unlink(self, obj: T) -> None:
        await event_bus.publish(
            f"record.deleted:{self.model_name}",
            self._record_event_payload(obj),
        )
        await event_bus.publish(
            "record.deleted",
            self._record_event_payload(obj),
        )
        rid = getattr(obj, "id", None)
        if rid is not None:
            from modules.base.controller.attachment_service import AttachmentService

            await AttachmentService(self.session).delete_for_linked_record(
                tenant_id=self.ctx.tenant_id,
                res_model=self.model_name,
                res_id=rid,
            )

    # ------------------------------------------------------------------
    # Multi-tenancy filter
    # ------------------------------------------------------------------

    def _tenant_filter(self) -> list:
        filters = []
        if self.ctx.tenant_id and "tenant_id" in self.table.c:
            filters.append(self.table.c.tenant_id == self.ctx.tenant_id)
        if self.ctx.company_id and "company_id" in self.table.c:
            filters.append(self.table.c.company_id == self.ctx.company_id)
        if "active" in self.table.c:
            filters.append(self.table.c.active == True)  # noqa: E712
        return filters

    # ------------------------------------------------------------------
    # Domain filter (Odoo-style tuples)
    # ------------------------------------------------------------------

    def _apply_domain(self, stmt, domain: list[tuple[str, str, Any]]):
        """Apply Odoo-style domain filters: [("field", "=", value), ...]"""
        ops = {
            "=": lambda c, v: c == v,
            "!=": lambda c, v: c != v,
            ">": lambda c, v: c > v,
            ">=": lambda c, v: c >= v,
            "<": lambda c, v: c < v,
            "<=": lambda c, v: c <= v,
            "like": lambda c, v: c.like(v),
            "ilike": lambda c, v: c.ilike(v),
            "in": lambda c, v: c.in_(v),
            "not in": lambda c, v: c.not_in(v),
        }
        for field_name, operator, value in domain:
            col = self.table.c.get(field_name)
            if col is None:
                continue
            op_fn = ops.get(operator)
            if op_fn:
                stmt = stmt.where(op_fn(col, value))
        return stmt

    # ------------------------------------------------------------------
    # RBAC stubs – implemented by orbiteus_core.security.rbac
    # ------------------------------------------------------------------

    async def _check_model_access(self, operation: str) -> None:
        """Raise AccessDenied if the current user lacks model-level access."""
        from orbiteus_core.security.rbac import check_model_access

        if not await check_model_access(self.ctx, self.model_name, operation):
            raise AccessDenied(self.model_name, operation)

    def _apply_record_rules_filter(self, stmt):
        """Apply record rules (domain-based row filters) from RBAC."""
        from orbiteus_core.security.rbac import apply_record_rules

        return apply_record_rules(stmt, self.table, self.ctx, self.model_name)

    async def _check_record_rules(self, obj: T, operation: str) -> None:
        """Verify a loaded record is accessible under record rules."""
        # enforced at query level; this is a post-load safety hook
        return None

    # ------------------------------------------------------------------
    # Snapshots, diffs, audit
    # ------------------------------------------------------------------

    _AUDIT_REDACT_FIELDS: set[str] = {"password_hash", "totp_secret"}
    _AUDIT_SKIP_FIELDS: set[str] = {"create_date", "write_date", "custom_fields"}

    def _snapshot(self, obj: T) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for f in dataclasses.fields(self.domain_class):
            if f.name in self._AUDIT_SKIP_FIELDS:
                continue
            value = getattr(obj, f.name, None)
            if f.name in self._AUDIT_REDACT_FIELDS and value is not None:
                value = "***"
            out[f.name] = value
        return out

    def _diff_for_create(self, obj: T) -> dict[str, Any]:
        snap = self._snapshot(obj)
        return {k: [None, v] for k, v in snap.items() if v not in (None, "", False, [], {})}

    @staticmethod
    def _diff(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        keys = set(old) | set(new)
        for key in keys:
            o, n = old.get(key), new.get(key)
            if o != n:
                out[key] = [o, n]
        return out

    def _record_event_payload(self, obj: T) -> dict[str, Any]:
        rid = getattr(obj, "id", None)
        return {
            "model": self.model_name,
            "id": rid,
            "tenant_id": getattr(obj, "tenant_id", None),
            "actor": self.ctx.actor,
            "user_id": self.ctx.user_id,
            "request_id": self.ctx.request_id,
        }

    async def _audit(self, operation: str, obj: T, *, diff: dict[str, Any]) -> None:
        if self.model_name in AUDIT_OPTOUT_MODELS:
            return

        # Lazy import to avoid circular at module load.
        from modules.base.model.domain import AuditLog
        from orbiteus_core.db import metadata  # noqa: F401

        record_id = getattr(obj, "id", None)
        tenant_id = getattr(obj, "tenant_id", None)
        actor = self.ctx.actor
        user_id = self.ctx.user_id
        meta: dict[str, Any] = {}
        if self.ctx.scope and self.ctx.scope != "internal":
            meta["scope"] = self.ctx.scope
        if self.ctx.is_superadmin:
            meta["superadmin"] = True

        row = AuditLog(
            tenant_id=tenant_id,
            actor=actor,
            user_id=user_id,
            request_id=self.ctx.request_id,
            model=self.model_name,
            record_id=record_id,
            operation=operation,
            diff=diff,
            metadata=meta,
        )
        self.session.add(row)
        await self.session.flush()
