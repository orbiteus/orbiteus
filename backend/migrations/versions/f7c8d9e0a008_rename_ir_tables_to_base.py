"""Rename Odoo-style ir_* tables to base_* engine tables.

Revision ID: f7c8d9e0a008
Revises: f6a1b2c3d007
Create Date: 2026-05-05

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect

from orbiteus_core.alembic_lock import migration_lock

revision: str = "f7c8d9e0a008"
down_revision: Union[str, None] = "f6a1b2c3d007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Old ir_* → new base_* (FK targets update automatically in PostgreSQL).
# base_ui_views was never created as ir_ui_views — it is created at runtime via create_all.
TABLE_RENAMES: list[tuple[str, str]] = [
    ("ir_action_servers", "base_action_servers"),
    ("ir_action_windows", "base_action_windows"),
    ("ir_attachments", "base_attachments"),
    ("ir_audit_log", "base_audit_log"),
    ("ir_ai_credentials", "base_ai_credentials"),
    ("ir_config_params", "base_config_params"),
    ("ir_crons", "base_crons"),
    ("ir_embeddings", "base_embeddings"),
    ("ir_mail_templates", "base_mail_templates"),
    ("ir_model_access", "base_model_access"),
    ("ir_models", "base_models"),
    ("ir_model_fields", "base_model_fields"),
    ("ir_outbox", "base_outbox"),
    ("ir_rules", "base_rules"),
    ("ir_sequences", "base_sequences"),
    ("ir_ui_menus", "base_ui_menus"),
    ("ir_webhooks", "base_webhooks"),
]


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(inspect(bind).get_table_names())
    with migration_lock():
        for old, new in TABLE_RENAMES:
            if old in existing and new not in existing:
                op.rename_table(old, new)


def downgrade() -> None:
    bind = op.get_bind()
    existing = set(inspect(bind).get_table_names())
    with migration_lock():
        for old, new in reversed(TABLE_RENAMES):
            if new in existing and old not in existing:
                op.rename_table(new, old)
