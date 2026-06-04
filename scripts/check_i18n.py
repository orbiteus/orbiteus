#!/usr/bin/env python3
"""CI check: en.json is canonical; locale modules stay aligned with en."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_I18N = ROOT / "backend" / "modules" / "base" / "i18n"
LOCALES_I18N = ROOT / "backend" / "modules" / "locales" / "i18n"
PUBLIC_FALLBACK_TS = ROOT / "packages" / "i18n" / "src" / "public-page-fallbacks.ts"
SYNC_PUBLIC_SCRIPT = ROOT / "scripts" / "sync_public_i18n_fallbacks.py"
OPTIONAL_LOCALE_MODULES = (("locales", LOCALES_I18N, ("pl", "de", "fr")),)
PUBLIC_PREFIXES = ("login.", "auth.", "welcome.", "portal.")


def main() -> int:
    en_path = BASE_I18N / "en.json"
    if not en_path.is_file():
        print(f"Missing {en_path}", file=sys.stderr)
        return 1

    en_keys = set(json.loads(en_path.read_text(encoding="utf-8")).keys())
    if "common.save" not in en_keys:
        print("en.json missing common.save", file=sys.stderr)
        return 1

    exit_code = 0
    for _mod_name, i18n_dir, locales in OPTIONAL_LOCALE_MODULES:
        if not i18n_dir.is_dir():
            print(f"Missing locale module dir {i18n_dir}", file=sys.stderr)
            exit_code = 1
            continue
        for locale in locales:
            path = i18n_dir / f"{locale}.json"
            if not path.is_file():
                print(f"Missing {path}", file=sys.stderr)
                exit_code = 1
                continue
            loc_keys = set(json.loads(path.read_text(encoding="utf-8")).keys())
            missing = sorted(en_keys - loc_keys)
            if missing:
                print(
                    f"{path.name} missing {len(missing)} keys vs en (first 5): {missing[:5]}",
                    file=sys.stderr,
                )
                exit_code = 1
            extra = sorted(loc_keys - en_keys)
            if extra:
                print(f"note: {path.name} has {len(extra)} keys not in en")

    if exit_code == 0:
        locale_list = ", ".join(loc for _, _, locs in OPTIONAL_LOCALE_MODULES for loc in locs)
        print(f"OK: en={len(en_keys)} keys; {locale_list} aligned in modules/locales")

    if exit_code == 0 and SYNC_PUBLIC_SCRIPT.is_file():
        import subprocess

        before = PUBLIC_FALLBACK_TS.read_text(encoding="utf-8") if PUBLIC_FALLBACK_TS.is_file() else ""
        proc = subprocess.run(
            [sys.executable, str(SYNC_PUBLIC_SCRIPT)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            print(proc.stderr or proc.stdout, file=sys.stderr)
            return 1
        after = PUBLIC_FALLBACK_TS.read_text(encoding="utf-8")
        if before != after:
            print(
                "public-page-fallbacks.ts is out of sync — run: python3 scripts/sync_public_i18n_fallbacks.py",
                file=sys.stderr,
            )
            return 1
        expected = {k for k in en_keys if k.startswith(PUBLIC_PREFIXES)}
        if '"auth.signIn"' not in after:
            print("public-page-fallbacks.ts missing auth.signIn", file=sys.stderr)
            return 1
        print(f"OK: public-page fallbacks synced ({len(expected)} keys from en)")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
