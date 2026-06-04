#!/usr/bin/env python3
"""Export FastAPI OpenAPI schema without a running server.

Used by admin-ui `npm run codegen` when the API is down locally, and by CI
drift checks after the stack is healthy.

Usage:
  PYTHONPATH=backend python scripts/export_openapi.py -o /tmp/openapi.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://orbiteus:orbiteus@localhost:5432/orbiteus_test",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "export-openapi-dev")
os.environ.setdefault("JWT_SECRET", "export-openapi-dev")
os.environ.setdefault("AI_SECRET_KEY", "export-openapi-dev")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Orbiteus OpenAPI JSON")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=ROOT / "admin-ui" / "src" / "lib" / "openapi" / "openapi.json",
        help="Output path (default: admin-ui/src/lib/openapi/openapi.json)",
    )
    args = parser.parse_args()

    from api import app  # noqa: WPS433 — import after env

    schema = app.openapi()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output} ({len(json.dumps(schema))} bytes)")


if __name__ == "__main__":
    main()
