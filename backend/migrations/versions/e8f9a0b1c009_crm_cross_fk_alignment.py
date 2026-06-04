"""Align CRM cross-table FK constraints with ORM metadata.

Adds missing FK on ``crm_persons.assigned_team_id`` and optional user refs
on persons, teams, and leads → ``base_users``.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "e8f9a0b1c009"
down_revision: Union[str, None] = "c1d4e5f013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _advisory_lock() -> None:
    op.get_bind().exec_driver_sql("SELECT pg_advisory_lock(11534116838)")


def _advisory_unlock() -> None:
    op.get_bind().exec_driver_sql("SELECT pg_advisory_unlock(11534116838)")


def upgrade() -> None:
    _advisory_lock()
    try:
        op.create_foreign_key(
            op.f("fk_crm_persons_assigned_team_id_crm_teams"),
            "crm_persons",
            "crm_teams",
            ["assigned_team_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_foreign_key(
            op.f("fk_crm_persons_assigned_user_id_base_users"),
            "crm_persons",
            "base_users",
            ["assigned_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_foreign_key(
            op.f("fk_crm_teams_leader_user_id_base_users"),
            "crm_teams",
            "base_users",
            ["leader_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_foreign_key(
            op.f("fk_crm_leads_assigned_user_id_base_users"),
            "crm_leads",
            "base_users",
            ["assigned_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
    finally:
        _advisory_unlock()


def downgrade() -> None:
    _advisory_lock()
    try:
        op.drop_constraint(
            op.f("fk_crm_leads_assigned_user_id_base_users"),
            "crm_leads",
            type_="foreignkey",
        )
        op.drop_constraint(
            op.f("fk_crm_teams_leader_user_id_base_users"),
            "crm_teams",
            type_="foreignkey",
        )
        op.drop_constraint(
            op.f("fk_crm_persons_assigned_user_id_base_users"),
            "crm_persons",
            type_="foreignkey",
        )
        op.drop_constraint(
            op.f("fk_crm_persons_assigned_team_id_crm_teams"),
            "crm_persons",
            type_="foreignkey",
        )
    finally:
        _advisory_unlock()
