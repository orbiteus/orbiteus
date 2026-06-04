"""JSON view loader tests (ADR-0022)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from orbiteus_core.json_views import JsonViewDefinition, load_json_view, view_to_ui_payload


def test_load_sample_list_view(tmp_path: Path):
    path = tmp_path / "demo.lead.list.view.json"
    path.write_text(
        json.dumps(
            {
                "model": "demo.lead",
                "type": "list",
                "columns": [{"key": "name", "label": "Lead"}],
            }
        ),
        encoding="utf-8",
    )
    view = load_json_view(path, "demo")
    assert view.model == "demo.lead"
    assert view.type == "list"
    payload = view_to_ui_payload(view)
    assert payload["columns"][0]["key"] == "name"


def test_invalid_json_view_rejected(tmp_path: Path):
    bad = tmp_path / "bad.view.json"
    bad.write_text('{"model": "x", "type": "list"}', encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid JSON view"):
        load_json_view(bad, "test")
