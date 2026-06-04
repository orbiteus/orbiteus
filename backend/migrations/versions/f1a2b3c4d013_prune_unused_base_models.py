"""Drop unused base models: partner, sequences, crons, Odoo action tables.

Revision ID: f1a2b3c4d013
Revises: f0a1b2c3d012
Create Date: 2026-05-29
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from orbiteus_core.alembic_lock import migration_lock

revision: str = "f1a2b3c4d013"
down_revision: Union[str, None] = "f0a1b2c3d012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_REMOVED_MODELS = (
    "base.partner",
    "base.sequence",
    "base.scheduled-job",
)


def upgrade() -> None:
    with migration_lock():
        conn = op.get_bind()

        for model in _REMOVED_MODELS:
            conn.execute(
                sa.text(
                    "DELETE FROM base_model_access WHERE model_name = :m"
                ),
                {"m": model},
            )
            conn.execute(
                sa.text("DELETE FROM base_rules WHERE model_name = :m"),
                {"m": model},
            )

        op.drop_constraint(
            op.f("fk_base_users_partner_id_base_partners"),
            "base_users",
            type_="foreignkey",
        )
        op.drop_column("base_users", "partner_id")
        op.drop_index(op.f("ix_base_partners_tenant_id"), table_name="base_partners")
        op.drop_index(op.f("ix_base_partners_company_id"), table_name="base_partners")
        op.drop_table("base_partners")
        op.drop_table("base_sequences")
        op.drop_table("base_crons")
        op.drop_table("base_action_windows")
        op.drop_table("base_action_servers")


def downgrade() -> None:
    with migration_lock():
        op.create_table(
            "base_action_servers",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("create_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("write_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("model_name", sa.String(length=255), nullable=False),
            sa.Column("code", sa.Text(), nullable=True),
            sa.Column("action_type", sa.String(length=50), server_default="code", nullable=True),
            sa.Column("workflow_name", sa.String(length=255), nullable=True),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_base_action_servers")),
        )
        op.create_table(
            "base_action_windows",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("create_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("write_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("model_name", sa.String(length=255), nullable=False),
            sa.Column("view_mode", sa.String(length=100), server_default="list,form", nullable=True),
            sa.Column("domain", sa.Text(), server_default="[]", nullable=True),
            sa.Column("context", sa.Text(), server_default="{}", nullable=True),
            sa.Column("target", sa.String(length=50), server_default="current", nullable=True),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_base_action_windows")),
        )
        op.create_table(
            "base_crons",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("create_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("write_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("model_name", sa.String(length=255), nullable=True),
            sa.Column("function_name", sa.String(length=255), nullable=True),
            sa.Column("args", sa.Text(), server_default="[]", nullable=True),
            sa.Column("kwargs", sa.Text(), server_default="{}", nullable=True),
            sa.Column("interval_number", sa.Integer(), server_default="1", nullable=True),
            sa.Column("interval_type", sa.String(length=20), server_default="hours", nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default="true", nullable=True),
            sa.Column("next_call", sa.String(length=50), nullable=True),
            sa.Column("temporal_schedule_id", sa.String(length=255), nullable=True),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_base_crons")),
        )
        op.create_table(
            "base_sequences",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("create_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("write_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("code", sa.String(length=100), nullable=False),
            sa.Column("prefix", sa.String(length=50), nullable=True),
            sa.Column("suffix", sa.String(length=50), nullable=True),
            sa.Column("padding", sa.Integer(), server_default="5", nullable=True),
            sa.Column("number_next", sa.Integer(), server_default="1", nullable=True),
            sa.Column("number_increment", sa.Integer(), server_default="1", nullable=True),
            sa.Column("use_date_range", sa.Boolean(), server_default="false", nullable=True),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_base_sequences")),
            sa.UniqueConstraint("code", name=op.f("uq_base_sequences_code")),
        )
        op.create_table(
            "base_partners",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("tenant_id", sa.UUID(), nullable=False),
            sa.Column("company_id", sa.UUID(), nullable=True),
            sa.Column("create_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("write_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by_id", sa.UUID(), nullable=True),
            sa.Column("modified_by_id", sa.UUID(), nullable=True),
            sa.Column("active", sa.Boolean(), server_default="true", nullable=True),
            sa.Column("custom_fields", sa.JSON(), server_default="{}", nullable=True),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("phone", sa.String(length=50), nullable=True),
            sa.Column("mobile", sa.String(length=50), nullable=True),
            sa.Column("street", sa.String(length=255), nullable=True),
            sa.Column("city", sa.String(length=100), nullable=True),
            sa.Column("zip_code", sa.String(length=20), nullable=True),
            sa.Column("country_code", sa.String(length=5), server_default="PL", nullable=True),
            sa.Column("is_company", sa.Boolean(), server_default="false", nullable=True),
            sa.Column("vat", sa.String(length=50), nullable=True),
            sa.Column("parent_partner_id", sa.UUID(), nullable=True),
            sa.Column("company_name", sa.String(length=255), nullable=True),
            sa.ForeignKeyConstraint(
                ["parent_partner_id"],
                ["base_partners.id"],
                name=op.f("fk_base_partners_parent_partner_id_base_partners"),
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_base_partners")),
        )
        op.create_index(
            op.f("ix_base_partners_company_id"),
            "base_partners",
            ["company_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_base_partners_tenant_id"),
            "base_partners",
            ["tenant_id"],
            unique=False,
        )
        op.add_column(
            "base_users",
            sa.Column("partner_id", sa.UUID(), nullable=True),
        )
        op.create_foreign_key(
            op.f("fk_base_users_partner_id_base_partners"),
            "base_users",
            "base_partners",
            ["partner_id"],
            ["id"],
        )
