"""Test configuration for Orbiteus smoke tests.

Uses a real PostgreSQL database (orbiteus_test) — same dialect as production.

Strategy:
- Session-scoped engine + metadata.create_all once per test run.
- Session-scoped AsyncClient (app bootstraps once; registry is a singleton).
- Per-test isolation via unique UUIDs in emails/slugs — no rollbacks needed
  for smoke tests that check happy paths and auth/isolation behaviour.
"""
from __future__ import annotations

import os
import uuid

# ---------------------------------------------------------------------------
# Point to the test database BEFORE importing anything from orbiteus.
# orbiteus_core.db creates the engine at module import time via settings.
# ---------------------------------------------------------------------------
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://orbiteus:orbiteus@localhost:5432/orbiteus_test",
)

# ---------------------------------------------------------------------------
# After env is set, import the app (triggers registry bootstrap)
# ---------------------------------------------------------------------------
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from api import app  # noqa: E402


# ---------------------------------------------------------------------------
# Session-scoped client — tables created once, app bootstraps once.
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session")
async def client():
    """Shared HTTP test client for the whole test session."""
    from orbiteus_core.db import engine, metadata

    # Create all tables (idempotent — uses IF NOT EXISTS)
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    # Optional cleanup: drop all tables after the session
    async with engine.begin() as conn:
        await conn.run_sync(metadata.drop_all)


# ---------------------------------------------------------------------------
# Helpers — every test uses unique UUIDs to avoid inter-test conflicts.
# ---------------------------------------------------------------------------

def unique_email(prefix: str = "user") -> str:
    return f"{prefix}+{uuid.uuid4().hex[:8]}@test.example"


def unique_slug(prefix: str = "tenant") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


async def register_user(
    client: AsyncClient,
    email: str | None = None,
    password: str = "test1234",
    name: str = "Test User",
    tenant_name: str | None = None,
    tenant_slug: str | None = None,
) -> dict:
    """Register a new tenant+user. Returns the token response dict."""
    email = email or unique_email()
    tenant_name = tenant_name or f"Tenant {uuid.uuid4().hex[:6]}"
    tenant_slug = tenant_slug or unique_slug()
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": password,
            "name": name,
            "tenant_name": tenant_name,
            "tenant_slug": tenant_slug,
        },
    )
    assert resp.status_code == 201, f"register failed: {resp.text}"
    return resp.json()


async def login_user(client: AsyncClient, email: str, password: str = "test1234") -> str:
    """Login and return the access token string."""
    resp = await client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200, f"login failed: {resp.text}"
    return resp.json()["access_token"]
