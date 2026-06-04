"""User last_login timestamptz + last_login_device.

Revision ID: a2b3c4d5e014
Revises: f1a2b3c4d013
Create Date: 2026-05-29
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from orbiteus_core.alembic_lock import migration_lock

revision: str = "a2b3c4d5e014"
down_revision: Union[str, None] = "f1a2b3c4d013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with migration_lock():
        op.add_column(
            "base_users",
            sa.Column("last_login_device", sa.String(length=20), nullable=True),
        )
        op.execute(
            """
            ALTER TABLE base_users
            ALTER COLUMN last_login TYPE TIMESTAMPTZ
            USING NULL
            """
        )


def downgrade() -> None:
    with migration_lock():
        op.execute(
            """
            ALTER TABLE base_users
            ALTER COLUMN last_login TYPE VARCHAR(50)
            USING NULL
            """
        )
        op.drop_column("base_users", "last_login_device")
