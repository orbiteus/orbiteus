"""Static checks on the ir_* → base_* table rename migration."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MIG = REPO_ROOT / "backend" / "migrations" / "versions" / "f7c8d9e0a008_rename_ir_tables_to_base.py"


def test_rename_migration_exists():
    assert MIG.exists()


def test_rename_migration_revises_webhook_filters():
    assert 'down_revision: Union[str, None] = "f6a1b2c3d007"' in MIG.read_text()


def test_rename_migration_renames_all_engine_tables():
    text = MIG.read_text()
    for old, new in (
        ("base_models", "base_models"),
        ("base_model_fields", "base_model_fields"),
        ("base_audit_log", "base_audit_log"),
        ("base_outbox", "base_outbox"),
        ("base_webhooks", "base_webhooks"),
        ("base_ai_credentials", "base_ai_credentials"),
        ("base_embeddings", "base_embeddings"),
    ):
        assert f'("{old}", "{new}")' in text, f"missing rename pair {old} → {new}"


def test_rename_migration_has_downgrade():
    text = MIG.read_text()
    assert "def downgrade()" in text
    assert 'op.rename_table(new, old)' in text or "reversed(TABLE_RENAMES)" in text
