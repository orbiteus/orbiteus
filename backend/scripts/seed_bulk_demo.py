"""DEPRECATED — use ``python -m scripts.seed_demo`` instead.

The old bulk script created 100 junk tenants/users and orphan attachment
metadata. It is kept only to print a clear migration message.
"""
from __future__ import annotations

import sys


def main() -> None:
    print(
        "seed_bulk_demo.py is deprecated.\n\n"
        "Use the curated demo seed instead:\n"
        "  python -m scripts.seed_demo --reset\n\n"
        "Or enable in Docker:\n"
        "  SEED_DEMO_DATA=1 RESET_DEMO_DATA=1 docker compose up --build\n",
        file=sys.stderr,
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
