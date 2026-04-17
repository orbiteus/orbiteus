#!/usr/bin/env python3
"""Copy admin-ui/public/branding/symbol.svg to docs/assets/symbol-readme.svg (transparent; GitHub README)."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "admin-ui/public/branding/symbol.svg"
OUT = ROOT / "docs/assets/symbol-readme.svg"


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit(f"Missing source: {SOURCE}")
    data = SOURCE.read_bytes()
    OUT.write_bytes(data)
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(data)} bytes)")


if __name__ == "__main__":
    main()
