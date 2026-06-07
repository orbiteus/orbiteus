"""Unit tests for system status version helpers."""
from __future__ import annotations

from orbiteus_core.system_status_probes import version_label, with_version


def test_version_label_normalizes():
    assert version_label("1.2.3") == "v1.2.3"
    assert version_label("v1.2.3") == "v1.2.3"
    assert version_label("unknown") == ""
    assert version_label("") == ""


def test_with_version_joins_parts():
    assert with_version("1.0.0", "async engine") == "v1.0.0 · async engine"
    assert with_version(None, "no version") == "no version"
    assert with_version("2.1", "ready", "3 modules") == "v2.1 · ready · 3 modules"
