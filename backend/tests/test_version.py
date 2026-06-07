"""Tests for Orbiteus release version helper."""
from __future__ import annotations

import orbiteus_core.version as version_mod
from orbiteus_core.version import _read_pyproject_version, get_orbiteus_version


def test_read_pyproject_version_matches_repo():
    ver = _read_pyproject_version()
    assert ver
    assert ver != "dev"


def test_get_orbiteus_version_prefers_pyproject_over_stale_metadata(monkeypatch):
    monkeypatch.delenv("ORBITEUS_VERSION", raising=False)
    version_mod.get_orbiteus_version.cache_clear()
    ver = get_orbiteus_version()
    assert ver == _read_pyproject_version()


def test_get_orbiteus_version_env_override(monkeypatch):
    monkeypatch.setenv("ORBITEUS_VERSION", "9.9.9-test")
    version_mod.get_orbiteus_version.cache_clear()
    assert get_orbiteus_version() == "9.9.9-test"
