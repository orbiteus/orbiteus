"""Unit tests for module catalog helpers."""
from __future__ import annotations

import pytest

from orbiteus_core.module_catalog import (
    CORE_MODULES,
    build_module_catalog,
    config_key_for_module,
    is_module_enabled,
    parse_enabled_value,
)
from orbiteus_core.registry import registry


@pytest.fixture(autouse=True)
def _ensure_modules_registered():
    for name in ("base", "auth"):
        if name not in registry.loaded_modules:
            registry.register(name)
    if not registry._bootstrapped:
        from fastapi import FastAPI
        registry.bootstrap(FastAPI())


def test_config_key_format():
    assert config_key_for_module("sales") == "module.sales.enabled"


def test_parse_enabled_value_defaults_true():
    assert parse_enabled_value(None) is True
    assert parse_enabled_value("true") is True
    assert parse_enabled_value("false") is False


def test_clear_enabled_map_cache():
    import orbiteus_core.module_catalog as mc

    mc._enabled_map_cache = (0.0, {"base": True})  # noqa: SLF001
    mc.clear_enabled_map_cache()
    assert mc._enabled_map_cache is None


def test_core_modules_always_enabled():
    enabled_map = {"base": False, "auth": False}
    assert is_module_enabled("base", enabled_map) is True
    assert is_module_enabled("auth", enabled_map) is True


def test_build_module_catalog_marks_core():
    catalog = build_module_catalog()
    base = next(m for m in catalog if m["name"] == "base")
    assert base["core"] is True
    assert base["toggleable"] is False
    assert base["name"] in CORE_MODULES
