"""Add base_roles table for RBAC role CRUD.

Revision ID: a9b0c1d2e010
Revises: f7c8d9e0a008
Create Date: 2026-05-28
"""
from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

from orbiteus_core.alembic_lock import migration_lock

revision: str = "a9b0c1d2e010"
down_revision: Union[str, None] = "f7c8d9e0a008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_ROLES = [
    (
        "base.group_system",
        "System administrator",
        "Full access to engine configuration and security.",
    ),
    (
        "base.group_user",
        "Internal user",
        "Default employee role with read-only access to shared master data.",
    ),
    (
        "crm.group_crm_manager",
        "CRM manager",
        "Full access to canonical CRM models.",
    ),
    (
        "crm.group_crm_user",
        "CRM user",
        "Sales role — create and edit leads assigned to them.",
    ),
]


def upgrade() -> None:
    with migration_lock():
        op.create_table(
            "base_roles",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("create_date", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("write_date", sa.DateTime(timezone=True), server_default=sa.text("now()")),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("code", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_system", sa.Boolean(), server_default="false", nullable=False),
            sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        )
        op.create_index("ix_base_roles_code", "base_roles", ["code"], unique=True)

        rows = [
            {
                "id": str(uuid.uuid4()),
                "name": name,
                "code": code,
                "description": description,
                "is_system": True,
                "active": True,
            }
            for code, name, description in DEFAULT_ROLES
        ]
        op.bulk_insert(
            sa.table(
                "base_roles",
                sa.column("id", UUID(as_uuid=True)),
                sa.column("name", sa.String),
                sa.column("code", sa.String),
                sa.column("description", sa.Text),
                sa.column("is_system", sa.Boolean),
                sa.column("active", sa.Boolean),
            ),
            rows,
        )


def downgrade() -> None:
    with migration_lock():
        op.drop_index("ix_base_roles_code", table_name="base_roles")
        op.drop_table("base_roles")
