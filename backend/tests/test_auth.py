"""Smoke tests: auth endpoints (register, login, refresh, /me)."""
from __future__ import annotations

import pytest

from tests.conftest import login_user, register_user, unique_email, unique_slug


@pytest.mark.asyncio
async def test_register_creates_user(client):
    tokens = await register_user(client)
    assert tokens["access_token"]
    assert tokens["refresh_token"]


@pytest.mark.asyncio
async def test_login_returns_tokens(client):
    email = unique_email("login")
    await register_user(client, email=email)
    resp = await client.post(
        "/api/auth/login",
        json={"email": email, "password": "test1234"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"]
    assert data["refresh_token"]


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    email = unique_email("wrongpw")
    await register_user(client, email=email)
    resp = await client.post(
        "/api/auth/login",
        json={"email": email, "password": "wrong-password"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(client):
    resp = await client.post(
        "/api/auth/login",
        json={"email": "nobody@does-not-exist.example", "password": "test1234"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_profile(client):
    email = unique_email("me")
    await register_user(client, email=email, name="Dave")
    token = await login_user(client, email)

    resp = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == email


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_issues_new_token(client):
    tokens = await register_user(client)
    resp = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert resp.status_code == 200
    new_tokens = resp.json()
    assert new_tokens["access_token"]


@pytest.mark.asyncio
async def test_refresh_invalid_token(client):
    resp = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": "not.a.valid.token"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_duplicate_email_rejected(client):
    """Two registrations with the same email must not both succeed."""
    email = unique_email("dup")
    await register_user(client, email=email, tenant_slug=unique_slug("dup1"))
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "test1234",
            "name": "Duplicate",
            "tenant_name": "Dup Tenant 2",
            "tenant_slug": unique_slug("dup2"),
        },
    )
    assert resp.status_code != 201


@pytest.mark.asyncio
async def test_register_user_is_not_superadmin(client):
    email = unique_email("rbac_role")
    await register_user(client, email=email)
    token = await login_user(client, email)
    resp = await client.get(
        "/api/base/modules",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
