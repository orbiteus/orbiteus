"""Add base_user_roles junction and migrate role_ids JSON.

Revision ID: f9a0b1c2d011
Revises: e8f9a0b1c009
Create Date: 2026-05-29
"""
from __future__ import annotations

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

from orbiteus_core.alembic_lock import migration_lock

revision: str = "f9a0b1c2d011"
down_revision: Union[str, None] = "e8f9a0b1c009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with migration_lock():
        op.create_table(
            "base_user_roles",
            sa.Column(
                "user_id",
                UUID(as_uuid=True),
                sa.ForeignKey("base_users.id", ondelete="CASCADE"),
                primary_key=True,
                nullable=False,
            ),
            sa.Column(
                "role_id",
                UUID(as_uuid=True),
                sa.ForeignKey("base_roles.id", ondelete="CASCADE"),
                primary_key=True,
                nullable=False,
            ),
        )
        op.create_index("ix_base_user_roles_user_id", "base_user_roles", ["user_id"])
        op.create_index("ix_base_user_roles_role_id", "base_user_roles", ["role_id"])

        conn = op.get_bind()
        users = conn.execute(
            sa.text("SELECT id, role_ids FROM base_users")
        ).fetchall()
        roles = conn.execute(
            sa.text("SELECT id, code FROM base_roles WHERE active = true")
        ).fetchall()
        code_to_id = {r.code: r.id for r in roles}

        for user in users:
            raw = user.role_ids
            if isinstance(raw, str):
                try:
                    raw = json.loads(raw)
                except json.JSONDecodeError:
                    raw = []
            if not isinstance(raw, list):
                raw = []
            codes = [str(c).strip() for c in raw if str(c).strip()]
            if not codes:
                codes = ["base.group_user"]
            for code in codes:
                role_id = code_to_id.get(code)
                if role_id is None:
                    continue
                conn.execute(
                    sa.text(
                        "INSERT INTO base_user_roles (user_id, role_id) "
                        "VALUES (:uid, :rid) ON CONFLICT DO NOTHING"
                    ),
                    {"uid": user.id, "rid": role_id},
                )


def downgrade() -> None:
    with migration_lock():
        op.drop_index("ix_base_user_roles_role_id", table_name="base_user_roles")
        op.drop_index("ix_base_user_roles_user_id", table_name="base_user_roles")
        op.drop_table("base_user_roles")
