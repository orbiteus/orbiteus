"""Add base_agents and base_agent_runs tables (ADR-0018).

Revision ID: b0c3d4e5f012
Revises: a9b0c1d2e010
Create Date: 2026-05-28
"""
from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON, UUID

from orbiteus_core.alembic_lock import migration_lock

revision: str = "b0c3d4e5f012"
down_revision: Union[str, None] = "a9b0c1d2e010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_BASE_COLS = [
    sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    sa.Column("tenant_id", UUID(as_uuid=True), nullable=True, index=True),
    sa.Column("company_id", UUID(as_uuid=True), nullable=True),
    sa.Column("create_date", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    sa.Column("write_date", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
    sa.Column("custom_fields", JSON, server_default="{}", nullable=False),
    sa.Column("created_by_id", UUID(as_uuid=True), nullable=True),
    sa.Column("modified_by_id", UUID(as_uuid=True), nullable=True),
]


def upgrade() -> None:
    with migration_lock():
        op.create_table(
            "base_agents",
            *_BASE_COLS,
            sa.Column("slug", sa.String(100), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("module_scope", sa.String(100), server_default="*", nullable=False),
            sa.Column("system_prompt", sa.Text(), server_default="", nullable=False),
            sa.Column("allowed_models", JSON, server_default="[]", nullable=False),
            sa.Column("allowed_actions", JSON, server_default="[]", nullable=False),
            sa.Column("provider", sa.String(50), nullable=True),
            sa.Column("model_default", sa.String(255), nullable=True),
            sa.Column("is_system", sa.Boolean(), server_default="false", nullable=False),
        )
        op.create_index(
            "uq_base_agents_tenant_slug",
            "base_agents",
            ["tenant_id", "slug"],
            unique=True,
        )

        op.create_table(
            "base_agent_runs",
            *_BASE_COLS,
            sa.Column(
                "agent_id",
                UUID(as_uuid=True),
                sa.ForeignKey("base_agents.id"),
                nullable=False,
            ),
            sa.Column("triggered_by_user_id", UUID(as_uuid=True), nullable=True),
            sa.Column("input_prompt", sa.Text(), server_default="", nullable=False),
            sa.Column("status", sa.String(32), server_default="pending", nullable=False),
            sa.Column("output_text", sa.Text(), nullable=True),
            sa.Column("tool_trace", JSON, server_default="[]", nullable=False),
            sa.Column("tokens_used", sa.Integer(), server_default="0", nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
        )
        op.create_index("ix_base_agent_runs_agent_id", "base_agent_runs", ["agent_id"])
        op.create_index(
            "ix_base_agent_runs_triggered_by",
            "base_agent_runs",
            ["triggered_by_user_id"],
        )


def downgrade() -> None:
    with migration_lock():
        op.drop_index("ix_base_agent_runs_triggered_by", table_name="base_agent_runs")
        op.drop_index("ix_base_agent_runs_agent_id", table_name="base_agent_runs")
        op.drop_table("base_agent_runs")
        op.drop_index("uq_base_agents_tenant_slug", table_name="base_agents")
        op.drop_table("base_agents")
