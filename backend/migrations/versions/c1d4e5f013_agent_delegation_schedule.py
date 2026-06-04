"""Agent delegation, scheduling, and run hierarchy (ADR-0019).

Revision ID: c1d4e5f013
Revises: b0c3d4e5f012
Create Date: 2026-05-28
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON, UUID

from orbiteus_core.alembic_lock import migration_lock

revision: str = "c1d4e5f013"
down_revision: Union[str, None] = "b0c3d4e5f012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with migration_lock():
        op.add_column(
            "base_agents",
            sa.Column("can_delegate", sa.Boolean(), server_default="false", nullable=False),
        )
        op.add_column(
            "base_agents",
            sa.Column("allowed_delegate_slugs", JSON, server_default="[]", nullable=False),
        )
        op.add_column(
            "base_agents",
            sa.Column("schedule_interval_minutes", sa.Integer(), nullable=True),
        )
        op.add_column(
            "base_agents",
            sa.Column("schedule_prompt", sa.Text(), server_default="", nullable=False),
        )
        op.add_column(
            "base_agents",
            sa.Column("schedule_last_run_at", sa.DateTime(timezone=True), nullable=True),
        )

        op.add_column(
            "base_agent_runs",
            sa.Column("parent_run_id", UUID(as_uuid=True), nullable=True),
        )
        op.add_column(
            "base_agent_runs",
            sa.Column("depth", sa.Integer(), server_default="0", nullable=False),
        )
        op.create_foreign_key(
            "fk_base_agent_runs_parent",
            "base_agent_runs",
            "base_agent_runs",
            ["parent_run_id"],
            ["id"],
        )
        op.create_index("ix_base_agent_runs_parent_run_id", "base_agent_runs", ["parent_run_id"])


def downgrade() -> None:
    with migration_lock():
        op.drop_index("ix_base_agent_runs_parent_run_id", table_name="base_agent_runs")
        op.drop_constraint("fk_base_agent_runs_parent", "base_agent_runs", type_="foreignkey")
        op.drop_column("base_agent_runs", "depth")
        op.drop_column("base_agent_runs", "parent_run_id")
        op.drop_column("base_agents", "schedule_last_run_at")
        op.drop_column("base_agents", "schedule_prompt")
        op.drop_column("base_agents", "schedule_interval_minutes")
        op.drop_column("base_agents", "allowed_delegate_slugs")
        op.drop_column("base_agents", "can_delegate")
