"""UI translation overrides table."""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "h4i5j6k7l017"
down_revision = "g2h3c4d5e016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "base_ui_translations" in insp.get_table_names():
        return

    op.create_table(
        "base_ui_translations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("create_date", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("write_date", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("lang", sa.String(16), nullable=False),
        sa.Column("module", sa.String(100), nullable=False, server_default=""),
        sa.Column("msg_key", sa.String(255), nullable=False),
        sa.Column("value", sa.Text(), nullable=False, server_default=""),
    )
    op.create_index("ix_base_ui_translations_lang", "base_ui_translations", ["lang"])
    op.create_index("ix_base_ui_translations_msg_key", "base_ui_translations", ["msg_key"])
    op.create_unique_constraint(
        "uq_base_ui_translations_lang_module_key",
        "base_ui_translations",
        ["lang", "module", "msg_key"],
    )


def downgrade() -> None:
    op.drop_table("base_ui_translations")
