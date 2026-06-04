"""Postgres advisory lock helper for Alembic migrations.

Use at the top of every Alembic `upgrade()` to prevent concurrent runs from
multiple replicas (compose `migrate` service is single-shot, but this is
defense in depth and required for k8s migrations as a Job).

Usage in a migration:

    from orbiteus_core.alembic_lock import migration_lock

    def upgrade() -> None:
        with migration_lock():
            op.create_table(...)
            ...

The lock id is a stable hash unique to "Orbiteus migrations" — not shared
with any other component on the same Postgres server.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager

from alembic import op

logger = logging.getLogger(__name__)

# Stable lock id — picked once, never changed without coordination.
ORBITEUS_MIGRATION_LOCK_ID = 11534116837


@contextmanager
def migration_lock():
    """Acquire pg_advisory_lock for the migration; release on exit."""
    bind = op.get_bind()
    logger.info("migration_lock: acquiring advisory lock %s", ORBITEUS_MIGRATION_LOCK_ID)
    bind.exec_driver_sql(f"SELECT pg_advisory_lock({ORBITEUS_MIGRATION_LOCK_ID})")
    try:
        yield
    finally:
        bind.exec_driver_sql(f"SELECT pg_advisory_unlock({ORBITEUS_MIGRATION_LOCK_ID})")
        logger.info("migration_lock: released advisory lock %s", ORBITEUS_MIGRATION_LOCK_ID)
