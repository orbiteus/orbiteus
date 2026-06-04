"""Unit tests for embedding refresh helpers."""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from orbiteus_core.embedding_refresh import build_embed_text  # noqa: E402


def test_build_embed_text_prioritizes_name_and_email():
    text = build_embed_text({
        "name": "Acme Corp",
        "email": "ops@acme.example",
        "notes": "Hot lead from trade show",
        "stage_id": "00000000-0000-0000-0000-000000000001",
    })
    assert "name: Acme Corp" in text
    assert "email: ops@acme.example" in text
    assert "notes: Hot lead" in text
    assert "stage_id" not in text


def test_build_embed_text_empty_record():
    assert build_embed_text({}) == ""
