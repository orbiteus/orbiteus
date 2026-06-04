"""Unit tests for UI i18n registry merge and English fallback."""
from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

from orbiteus_core.i18n_loader import discover_module_i18n, parse_locale_meta
from orbiteus_core.i18n_registry import (
    _MERGED_CACHE_MAX_LANGS,
    _merged_messages_cache,
    catalog_with_en_fallback,
    clear_ui_translation_cache,
    file_catalog_for,
    register_locale_meta,
    register_module_messages,
    reset_i18n_registry_for_tests,
)
from tests.conftest import login_user

_BASE_PATH = Path(__file__).resolve().parents[1] / "modules" / "base"
_LOCALES_PATH = Path(__file__).resolve().parents[1] / "modules" / "locales"


def _reload_base_i18n_from_disk() -> None:
    from modules.base.manifest import MANIFEST as BASE_MANIFEST
    from modules.locales.manifest import MANIFEST as LOCALES_MANIFEST

    for _mod, lang, messages in discover_module_i18n(_BASE_PATH, BASE_MANIFEST):
        register_module_messages("base", lang, messages)
    register_locale_meta(parse_locale_meta(BASE_MANIFEST), module="base")
    for _mod, lang, messages in discover_module_i18n(_LOCALES_PATH, LOCALES_MANIFEST):
        register_module_messages("locales", lang, messages)
    register_locale_meta(parse_locale_meta(LOCALES_MANIFEST), module="locales")


@pytest.fixture
def isolated_i18n_registry():
    reset_i18n_registry_for_tests()
    register_module_messages("base", "en", {"common.save": "Save", "common.cancel": "Cancel"})
    register_module_messages("base", "pl", {"common.save": "Zapisz"})
    yield
    reset_i18n_registry_for_tests()
    _reload_base_i18n_from_disk()


def test_catalog_with_en_fallback_inherits_en_keys(isolated_i18n_registry):
    pl = catalog_with_en_fallback("pl")
    assert pl["common.save"] == "Zapisz"
    assert pl["common.cancel"] == "Cancel"


def test_catalog_with_en_fallback_en_only(isolated_i18n_registry):
    en = catalog_with_en_fallback("en")
    assert en["common.save"] == "Save"
    assert "common.cancel" in en


def test_later_module_overrides_same_locale(isolated_i18n_registry):
    register_module_messages("inventory", "pl", {"common.save": "Zapisz magazyn"})
    assert file_catalog_for("pl")["common.save"] == "Zapisz magazyn"


@pytest.mark.asyncio
async def test_merged_messages_cache_evicts_when_full(isolated_i18n_registry):
    from orbiteus_core.i18n_registry import merged_messages_for

    clear_ui_translation_cache()
    for i in range(_MERGED_CACHE_MAX_LANGS):
        _merged_messages_cache[f"lang{i}"] = (f"sig{i}", {"k": "v"})
    await merged_messages_for(None, "en", enabled_map={"crm": True})
    assert len(_merged_messages_cache) == 1
    assert "en" in _merged_messages_cache

