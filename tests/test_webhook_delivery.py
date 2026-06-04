"""Webhook delivery + dead-letter contract — DoD §5.5 / §5.6.

Two contracts, both exercised against the real Postgres `base_outbox` and
`base_webhooks` tables (the dev compose stack the rest of the suite already
relies on):

  1.  Happy path.
      A `pending` outbox row pointing at a webhook subscriber is drained
      by `_drain_outbox_async`, the HTTP POST is observed (with the
      canonical `X-Orbiteus-Signature` HMAC header), and the row's
      status flips to ``done``.

  2.  Retry → dead-letter.
      With the same setup but the outbound POST returning HTTP 500, the
      drainer increments `retries` and reschedules `next_run_at`. When
      `MAX_RETRIES` is reached the row's status becomes ``dead``.

The status string ``dead`` (not ``dead_letter``) matches the existing
implementation in `tasks/outbox_tasks.py:_mark_dead`. Tests assert on
the actual contract, not the documentation's name for it.

Skipped when Postgres on the dev port (5433) isn't reachable so the
suite stays green on a bare laptop.
"""
from __future__ import annotations

import asyncio
import importlib
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"


def _ensure_backend_path():
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))


def _postgres_alive() -> bool:
    """Try to connect to the dev postgres on host port 5433."""
    try:
        import asyncpg  # noqa: F401
    except ImportError:
        return False

    async def _probe() -> bool:
        try:
            import asyncpg

            conn = await asyncio.wait_for(
                asyncpg.connect(
                    "postgresql://orbiteus:orbiteus@localhost:5433/orbiteus",
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


def _import_outbox_tasks():
    _ensure_backend_path()
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+asyncpg://orbiteus:orbiteus@localhost:5433/orbiteus",
    )
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("SECRET_KEY", "change-me-in-development")

    sys.modules.pop("tasks.outbox_tasks", None)
    sys.modules.pop("tasks.webhook_tasks", None)
    return (
        importlib.import_module("tasks.outbox_tasks"),
        importlib.import_module("tasks.webhook_tasks"),
    )


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

async def _seed_webhook_and_outbox(*, status_code: int) -> tuple[uuid.UUID, uuid.UUID]:
    """Insert one `base_webhook` + one matching `pending` `base_outbox` row.

    Returns ``(webhook_id, outbox_id)``. The caller cleans up by id.
    """
    _ensure_backend_path()
    from sqlalchemy import insert

    from modules.base.model.mapping import (
        base_outbox_table,
        base_webhooks_table,
    )
    from orbiteus_core.db import AsyncSessionFactory

    webhook_id = uuid.uuid4()
    outbox_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    async with AsyncSessionFactory() as session:
        await session.execute(
            insert(base_webhooks_table).values(
                id=webhook_id,
                create_date=now,
                write_date=now,
                tenant_id=None,
                name=f"test-{status_code}",
                url=f"https://test.local/hook/{webhook_id}",
                secret="s3cret-shhh",
                event_mask=["record.updated"],
                model_filter="crm.lead",
                field_filter=[],
                is_active=True,
                active=True,
            )
        )
        await session.execute(
            insert(base_outbox_table).values(
                id=outbox_id,
                create_date=now,
                write_date=now,
                tenant_id=None,
                event="record.updated",
                payload={"id": str(uuid.uuid4()), "model": "crm.lead"},
                target_kind="webhook",
                target_ref=str(webhook_id),
                status="pending",
                next_run_at=(now - timedelta(seconds=1)).isoformat(),
                retries=0,
            )
        )
        await session.commit()
    return webhook_id, outbox_id


async def _read_outbox_status(outbox_id: uuid.UUID) -> tuple[str, int]:
    _ensure_backend_path()
    from sqlalchemy import select

    from modules.base.model.mapping import base_outbox_table
    from orbiteus_core.db import AsyncSessionFactory

    async with AsyncSessionFactory() as session:
        row = (
            await session.execute(
                select(
                    base_outbox_table.c.status,
                    base_outbox_table.c.retries,
                ).where(base_outbox_table.c.id == outbox_id)
            )
        ).first()
    assert row is not None
    return row[0], row[1]


async def _cleanup(webhook_id: uuid.UUID, outbox_id: uuid.UUID) -> None:
    _ensure_backend_path()
    from sqlalchemy import delete

    from modules.base.model.mapping import base_outbox_table, base_webhooks_table
    from orbiteus_core.db import AsyncSessionFactory, engine

    async with AsyncSessionFactory() as session:
        await session.execute(
            delete(base_outbox_table).where(base_outbox_table.c.id == outbox_id)
        )
        await session.execute(
            delete(base_webhooks_table).where(base_webhooks_table.c.id == webhook_id)
        )
        await session.commit()
    # The engine binds asyncpg connections to the current event loop; if a
    # later test in the same suite runs in a fresh loop, asyncpg will trip on
    # `Event loop is closed`. Dispose the engine so the next test gets a
    # clean pool.
    await engine.dispose()


def _patch_httpx(monkeypatch, *, status_code: int) -> list[dict]:
    """Replace `httpx.AsyncClient` with a stub that records calls.

    Returns a list which the test can inspect after the drain runs:

        [{"url": ..., "headers": {...}, "body": b"..."}, ...]
    """
    captured: list[dict] = []

    class _StubResponse:
        def __init__(self, code: int) -> None:
            self.status_code = code

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                import httpx

                raise httpx.HTTPStatusError(
                    f"server returned {self.status_code}",
                    request=MagicMock(),
                    response=self,
                )

    class _StubAsyncClient:
        def __init__(self, *_, **__):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def post(self, url, *, content=None, headers=None, **__):
            captured.append({
                "url": url,
                "headers": dict(headers or {}),
                "body": content,
            })
            return _StubResponse(status_code)

    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", _StubAsyncClient)
    return captured


# ---------------------------------------------------------------------------
# 1) Happy path — pending → done, signed HMAC posted
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_outbox_drains_webhook_and_marks_done(monkeypatch):
    outbox_tasks, webhook_tasks = _import_outbox_tasks()

    captured = _patch_httpx(monkeypatch, status_code=200)

    webhook_id, outbox_id = await _seed_webhook_and_outbox(status_code=200)
    try:
        result = await outbox_tasks._drain_outbox_async()

        assert result["processed"] >= 1
        assert result["dead"] == 0

        status, retries = await _read_outbox_status(outbox_id)
        assert status == "done", f"expected done, got {status} (retries={retries})"

        # Verify the HMAC contract: exactly one POST, with the canonical
        # signature header.
        target_calls = [c for c in captured if str(webhook_id) in c["url"]]
        assert len(target_calls) == 1, (
            f"expected one POST, got {len(target_calls)}: {captured}"
        )
        sent = target_calls[0]
        assert "X-Orbiteus-Signature" in sent["headers"]
        assert sent["headers"]["X-Orbiteus-Event"] == "record.updated"
        assert isinstance(sent["body"], bytes) and len(sent["body"]) > 0
    finally:
        await _cleanup(webhook_id, outbox_id)


# ---------------------------------------------------------------------------
# 2) Retry → dead-letter
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_outbox_retries_then_dead_letters_on_5xx(monkeypatch):
    """With a low MAX_RETRIES and a 500-returning webhook, the drainer
    must transition the outbox row through `pending` (with growing
    `retries`) and finally `dead`."""
    outbox_tasks, webhook_tasks = _import_outbox_tasks()

    # Tighten the retry budget for the test — the production default is 10.
    monkeypatch.setattr(outbox_tasks, "MAX_RETRIES", 3)
    # Backoff is normally 60s+; force the drainer to consider the row
    # ready immediately so we don't have to wait minutes between drains.
    monkeypatch.setattr(outbox_tasks, "_backoff_seconds", lambda _retries: 0)

    _patch_httpx(monkeypatch, status_code=500)

    webhook_id, outbox_id = await _seed_webhook_and_outbox(status_code=500)
    try:
        seen_statuses: list[tuple[str, int]] = []
        for _ in range(5):
            await outbox_tasks._drain_outbox_async()
            status, retries = await _read_outbox_status(outbox_id)
            seen_statuses.append((status, retries))
            if status == "dead":
                break

        # We MUST have observed at least one `pending` retry before the
        # final transition, plus a final `dead`.
        assert seen_statuses[-1][0] == "dead", (
            f"row never transitioned to dead: {seen_statuses}"
        )
        retries_progression = [r for s, r in seen_statuses if s == "pending"]
        assert retries_progression, (
            "row went straight to dead without a pending retry: "
            f"{seen_statuses}"
        )
        assert max(retries_progression) >= 1, (
            f"`retries` never incremented: {seen_statuses}"
        )
    finally:
        await _cleanup(webhook_id, outbox_id)
