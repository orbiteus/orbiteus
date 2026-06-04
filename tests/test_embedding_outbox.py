"""Embedding dispatcher + outbox drain integration (Postgres required)."""
from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"


def _ensure_backend_path():
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))


def _postgres_alive() -> bool:
    try:
        import asyncpg  # noqa: F401
    except ImportError:
        return False

    async def _probe() -> bool:
        try:
            import asyncpg

            conn = await asyncio.wait_for(
                asyncpg.connect(
                    "postgresql://orbiteus:orbiteus@localhost:5433/orbiteus",  # pragma: allowlist secret
                ),
                timeout=2.0,
            )
            await conn.close()
            return True
        except Exception:  # noqa: BLE001
            return False

    return asyncio.run(_probe())


pytestmark = pytest.mark.skipif(
    not _postgres_alive(),
    reason="Postgres not reachable on localhost:5433",
)


@pytest.mark.asyncio
async def test_embedding_outbox_row_drains_to_done():
    _ensure_backend_path()
    from sqlalchemy import insert, select

    from modules.base.model.mapping import base_embeddings_table, base_outbox_table
    from orbiteus_core.db import AsyncSessionFactory
    from tasks.outbox_tasks import _drain_outbox_async

    tenant_id = uuid.uuid4()
    record_id = uuid.uuid4()
    outbox_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    payload = {
        "model": "crm.lead",
        "id": str(record_id),
        "tenant_id": str(tenant_id),
        "__event_name__": "record.updated",
    }

    mock_result = {"status": "indexed", "model": "crm.lead", "record_id": str(record_id)}

    with patch(
        "tasks.embedding_tasks.refresh_embedding_async",
        new=AsyncMock(return_value=mock_result),
    ):
        async with AsyncSessionFactory() as session:
            await session.execute(
                insert(base_outbox_table).values(
                    id=outbox_id,
                    create_date=now,
                    write_date=now,
                    tenant_id=tenant_id,
                    status="pending",
                    event="record.updated",
                    payload=payload,
                    target_kind="embedding",
                    target_ref=str(record_id),
                    retries=0,
                    next_run_at=now.isoformat(),
                )
            )
            await session.commit()

        stats = await _drain_outbox_async()
        assert stats["processed"] >= 1

        async with AsyncSessionFactory() as session:
            row = (
                await session.execute(
                    select(base_outbox_table.c.status).where(base_outbox_table.c.id == outbox_id)
                )
            ).first()
            assert row is not None
            assert row[0] == "done"

            emb = (
                await session.execute(
                    select(base_embeddings_table.c.id).where(
                        base_embeddings_table.c.record_id == record_id
                    )
                )
            ).first()
            assert emb is None
