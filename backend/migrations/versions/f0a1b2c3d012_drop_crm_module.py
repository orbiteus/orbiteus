"""Remove legacy CRM module tables and RBAC artifacts.

Revision ID: f0a1b2c3d012
Revises: f9a0b1c2d011
Create Date: 2026-05-29
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from orbiteus_core.alembic_lock import migration_lock

revision: str = "f0a1b2c3d012"
down_revision: Union[str, None] = "f9a0b1c2d011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with migration_lock():
        conn = op.get_bind()

        # RBAC + agents (module removed; tables kept in history only).
        conn.execute(
            sa.text(
                "DELETE FROM base_user_roles WHERE role_id IN "
                "(SELECT id FROM base_roles WHERE code LIKE 'crm.%')"
            )
        )
        conn.execute(sa.text("DELETE FROM base_model_access WHERE model_name LIKE 'crm.%'"))
        conn.execute(sa.text("DELETE FROM base_rules WHERE model_name LIKE 'crm.%'"))
        conn.execute(sa.text("DELETE FROM base_roles WHERE code LIKE 'crm.%'"))
        conn.execute(
            sa.text(
                "DELETE FROM base_agent_runs WHERE agent_id IN "
                "(SELECT id FROM base_agents WHERE module_scope = 'crm' OR slug LIKE 'crm-%')"
            )
        )
        conn.execute(
            sa.text(
                "DELETE FROM base_agents WHERE module_scope = 'crm' OR slug LIKE 'crm-%'"
            )
        )
        conn.execute(
            sa.text(
                "DELETE FROM base_ui_views WHERE model LIKE 'crm.%' OR module = 'crm'"
            )
        )

        op.execute("DROP TABLE IF EXISTS crm_leads CASCADE")
        op.execute("DROP TABLE IF EXISTS crm_teams CASCADE")
        op.execute("DROP TABLE IF EXISTS crm_persons CASCADE")
        op.execute("DROP TABLE IF EXISTS crm_stages CASCADE")


def downgrade() -> None:
    # CRM module removed from codebase — no downgrade path.
    pass
