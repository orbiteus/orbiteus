"""Load or reset the Orbiteus demo dataset.

Examples:
  # Idempotent demo seed (skip if already applied):
  python -m scripts.seed_demo

  # Wipe junk + re-apply demo (recommended after old bulk seed):
  python -m scripts.seed_demo --reset

Docker:
  docker compose exec backend python -m scripts.seed_demo --reset
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys

from orbiteus_core.demo_seed import DEMO_PASSWORD, DEMO_USERS, run_demo_seed_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo data for the default tenant")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Remove junk tenants/users/bulk seed rows before seeding",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-apply demo seed even when demo.seed_version matches",
    )
    args = parser.parse_args()

    result = asyncio.run(
        run_demo_seed_pipeline(reset=args.reset, force=args.force)
    )
    print(json.dumps(result, indent=2))
    print()
    print("Demo logins (password for all demo.* users):")
    print(f"  {DEMO_PASSWORD}")
    for u in DEMO_USERS:
        print(f"  - {u.email} ({u.name})")


if __name__ == "__main__":
    main()
