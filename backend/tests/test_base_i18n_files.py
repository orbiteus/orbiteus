"""On-disk i18n JSON catalogs and CI check script."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

BASE_I18N = Path(__file__).resolve().parents[1] / "modules" / "base" / "i18n"
LOCALES_I18N = Path(__file__).resolve().parents[1] / "modules" / "locales" / "i18n"
_REPO_CANDIDATES = (
    Path(__file__).resolve().parents[2],
    Path(__file__).resolve().parents[1].parent,
)
CHECK_SCRIPT = next(
    (root / "scripts" / "check_i18n.py" for root in _REPO_CANDIDATES if (root / "scripts" / "check_i18n.py").is_file()),
    Path(__file__).resolve().parents[2] / "scripts" / "check_i18n.py",
)


def test_base_en_json_only_core_locale_file():
    json_files = sorted(p.name for p in BASE_I18N.glob("*.json"))
    assert json_files == ["en.json"], f"base/i18n must only ship en.json, found {json_files}"


def test_en_json_has_required_keys():
    data = json.loads((BASE_I18N / "en.json").read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert len(data) >= 100
    for key in ("common.save", "nav.dashboard", "auth.signIn", "portal.title"):
        assert key in data, key
        assert data[key].strip()


@pytest.mark.parametrize("locale", ["pl", "de", "fr"])
def test_locales_module_json_exists(locale: str):
    path = LOCALES_I18N / f"{locale}.json"
    assert path.is_file(), f"missing {path}"


def test_pl_covers_all_en_keys():
    en = json.loads((BASE_I18N / "en.json").read_text(encoding="utf-8"))
    pl = json.loads((LOCALES_I18N / "pl.json").read_text(encoding="utf-8"))
    missing = set(en) - set(pl)
    assert not missing, f"pl.json missing keys: {sorted(missing)[:10]}"


def test_check_i18n_script_passes():
    if not CHECK_SCRIPT.is_file():
        pytest.skip(f"check_i18n.py not available in this environment ({CHECK_SCRIPT})")
    repo_root = CHECK_SCRIPT.parent.parent
    proc = subprocess.run(
        [sys.executable, str(CHECK_SCRIPT)],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
