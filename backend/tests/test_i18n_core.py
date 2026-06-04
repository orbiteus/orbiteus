"""Tests for UI language and timezone normalization."""
from __future__ import annotations

import pytest

from orbiteus_core.i18n import normalize_timezone, normalize_ui_language


def test_normalize_ui_language_supported():
    assert normalize_ui_language("en") == "en"
    extras = frozenset({"pl", "de"})
    assert normalize_ui_language("pl", extra_codes=extras) == "pl"
    assert normalize_ui_language("de-DE", extra_codes=extras) == "de"


def test_normalize_ui_language_fallback():
    assert normalize_ui_language("xx") == "en"


def test_normalize_timezone_valid():
    assert normalize_timezone("Europe/Warsaw") == "Europe/Warsaw"


def test_normalize_timezone_invalid():
    with pytest.raises(ValueError, match="Unknown timezone"):
        normalize_timezone("Not/AZone")
