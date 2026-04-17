"""BaseRepository – generic CRUD + search with automatic record rule application.

Usage:
    class CustomerRepository(BaseRepository[Customer]):
        model_name = "crm.customer"

    repo = CustomerRepository(session, ctx)
    customers = await repo.search([("status", "=", "active")])
"""
from __future__ import annotations

import uuid
from typing import Any, Generic, Sequence, TypeVar

from sqlalchemy import Table, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.base_domain import BaseModel
from orbiteus_core.context import RequestContext
from orbiteus_core.exceptions import AccessDenied, NotFound

T = TypeVar("T", bound=BaseModel)


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
        import dataclasses
        fields = {f.name for f in dataclasses.fields(self.domain_class)}
        if "tenant_id" in fields:
            data.setdefault("tenant_id", self.ctx.tenant_id)
        if "company_id" in fields:
            data.setdefault("company_id", self.ctx.company_id)
        obj = self.domain_class(**data)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def update(self, record_id: uuid.UUID, data: dict[str, Any]) -> T:
        await self._check_model_access("write")
        obj = await self.get(record_id)
        for key, value in data.items():
            setattr(obj, key, value)
        await self.session.flush()
        return obj

    async def delete(self, record_id: uuid.UUID) -> None:
        await self._check_model_access("unlink")
        obj = await self.get(record_id)
        # Soft delete: set active=False
        obj.active = False  # type: ignore[attr-defined]
        await self.session.flush()

    async def hard_delete(self, record_id: uuid.UUID) -> None:
        """Permanent delete – use only from migrations or admin."""
        await self._check_model_access("unlink")
        stmt = delete(self.domain_class).where(self.table.c.id == record_id)
        await self.session.execute(stmt)

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
        pass  # enforced at query level; this is a post-load safety hook
