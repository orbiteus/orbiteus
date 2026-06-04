#!/usr/bin/env python3
"""One-off: export packages/i18n catalogs to modules/base/i18n/*.json via Node."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
I18N_PKG = ROOT / "packages" / "i18n"
OUT_DIR = ROOT / "backend" / "modules" / "base" / "i18n"

EXPORT_JS = """
import { writeFileSync, mkdirSync } from "fs";
import { MESSAGE_CATALOGS } from "./src/messages.ts";

const out = process.argv[2];
mkdirSync(out, { recursive: true });
for (const [lang, catalog] of Object.entries(MESSAGE_CATALOGS)) {
  const path = `${out}/${lang}.json`;
  writeFileSync(path, JSON.stringify(catalog, null, 2) + "\\n", "utf8");
  console.log("wrote", path, Object.keys(catalog).length, "keys");
}
"""


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    script_path = I18N_PKG / "_export_catalogs.mjs"
    script_path.write_text(
        'import { writeFileSync, mkdirSync } from "fs";\n'
        'import { MESSAGE_CATALOGS } from "./src/messages.ts";\n'
        f'const out = {json.dumps(str(OUT_DIR))};\n'
        "mkdirSync(out, { recursive: true });\n"
        "for (const [lang, catalog] of Object.entries(MESSAGE_CATALOGS)) {\n"
        '  const path = `${out}/${lang}.json`;\n'
        "  writeFileSync(path, JSON.stringify(catalog, null, 2) + '\\n', 'utf8');\n"
        '  console.log("wrote", path, Object.keys(catalog).length, "keys");\n'
        "}\n",
        encoding="utf-8",
    )
    try:
        subprocess.run(
            ["npx", "tsx", str(script_path)],
            cwd=str(I18N_PKG),
            check=True,
        )
    finally:
        script_path.unlink(missing_ok=True)
    en = OUT_DIR / "en.json"
    if not en.is_file():
        print("export failed: en.json missing", file=sys.stderr)
        return 1
    print("OK:", en, "bytes", en.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
