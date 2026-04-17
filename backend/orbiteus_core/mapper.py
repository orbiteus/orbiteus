"""SQLAlchemy imperative mapping helpers.

Usage in a module's mapping.py:

    from orbiteus_core.mapper import make_base_columns, register_mapping
    from orbiteus_core.db import metadata

    customers_table = Table(
        "crm_customers",
        metadata,
        *make_base_columns(),           # adds id, tenant_id, company_id, …
        Column("name", String(255), nullable=False),
        Column("email", String(255)),
    )

    register_mapping(Customer, customers_table)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, Column, DateTime, String, Table, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import registry

# Central ORM registry (shared across all modules)
mapper_registry = registry()


def make_base_columns() -> list[Column]:
    """Return the standard base columns every business table must have."""
    return [
        Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        Column("tenant_id", UUID(as_uuid=True), nullable=True, index=True),
        Column("company_id", UUID(as_uuid=True), nullable=True, index=True),
        Column(
            "create_date",
            DateTime(timezone=True),
            nullable=False,
            default=lambda: datetime.now(timezone.utc),
        ),
        Column(
            "write_date",
            DateTime(timezone=True),
            nullable=False,
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
        ),
        Column("active", Boolean, nullable=False, server_default="true"),
        Column("custom_fields", JSON, nullable=False, server_default="{}"),
    ]


def make_system_columns() -> list[Column]:
    """Columns for system/ir_* objects (no tenant isolation)."""
    return [
        Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        Column(
            "create_date",
            DateTime(timezone=True),
            nullable=False,
            default=lambda: datetime.now(timezone.utc),
        ),
        Column(
            "write_date",
            DateTime(timezone=True),
            nullable=False,
            default=lambda: datetime.now(timezone.utc),
            onupdate=lambda: datetime.now(timezone.utc),
        ),
    ]


def register_mapping(
    domain_class: type,
    table: Table,
    properties: dict[str, Any] | None = None,
) -> None:
    """Imperatively map a domain dataclass to a SQLAlchemy Table."""
    mapper_registry.map_imperatively(
        domain_class,
        table,
        properties=properties or {},
    )


def setup_timestamp_listener(table: Table) -> None:
    """Ensure write_date is updated on every UPDATE even without ORM layer."""

    @event.listens_for(table, "before_update")
    def _set_write_date(mapper, connection, target):  # noqa: ARG001
        target.write_date = datetime.now(timezone.utc)
