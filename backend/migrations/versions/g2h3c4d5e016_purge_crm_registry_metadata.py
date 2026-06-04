"""Remove CRM rows from registry metadata tables (module removed from codebase).

Revision ID: g2h3c4d5e016
Revises: a2b3c4d5e014
Create Date: 2026-06-03
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from orbiteus_core.alembic_lock import migration_lock

revision: str = "g2h3c4d5e016"
down_revision: Union[str, None] = "a2b3c4d5e014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with migration_lock():
        conn = op.get_bind()
        conn.execute(
            sa.text("DELETE FROM base_model_fields WHERE model_name LIKE 'crm.%'")
        )
        conn.execute(sa.text("DELETE FROM base_models WHERE model_name LIKE 'crm.%'"))
        conn.execute(
            sa.text("DELETE FROM base_model_access WHERE model_name LIKE 'crm.%'")
        )
        conn.execute(sa.text("DELETE FROM base_rules WHERE model_name LIKE 'crm.%'"))


def downgrade() -> None:
    pass
