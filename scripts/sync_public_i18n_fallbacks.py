#!/usr/bin/env python3
"""Generate packages/i18n public-page fallbacks from modules/base/i18n/en.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EN_PATH = ROOT / "backend" / "modules" / "base" / "i18n" / "en.json"
OUT_PATH = ROOT / "packages" / "i18n" / "src" / "public-page-fallbacks.ts"
PREFIXES = ("login.", "auth.", "welcome.", "portal.")


def main() -> int:
    if not EN_PATH.is_file():
        print(f"Missing {EN_PATH}", file=sys.stderr)
        return 1

    en: dict[str, str] = json.loads(EN_PATH.read_text(encoding="utf-8"))
    subset = {k: v for k, v in sorted(en.items()) if k.startswith(PREFIXES)}
    if "auth.signIn" not in subset:
        print("en.json missing auth.signIn", file=sys.stderr)
        return 1

    lines = [
        'import type { MessageCatalog } from "./core";',
        "",
        "/**",
        " * English copy for /login and /welcome — synced from modules/base/i18n/en.json.",
        " * Avoids fetching the full UI catalog (~590 keys) on public routes.",
        " * Regenerate: python3 scripts/sync_public_i18n_fallbacks.py",
        " */",
        "export const PUBLIC_PAGE_FALLBACK_EN: MessageCatalog = {",
    ]
    for key, value in subset.items():
        escaped = json.dumps(value, ensure_ascii=False)
        lines.append(f"  {json.dumps(key)}: {escaped},")
    lines.append("};")
    lines.append("")

    new_body = "\n".join(lines)
    if OUT_PATH.is_file() and OUT_PATH.read_text(encoding="utf-8") == new_body:
        print(f"OK: {OUT_PATH.name} unchanged ({len(subset)} keys)")
        return 0

    OUT_PATH.write_text(new_body, encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({len(subset)} keys)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
