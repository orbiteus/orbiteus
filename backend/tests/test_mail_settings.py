"""Mail settings persistence and API."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from orbiteus_core.config import settings
from tests.conftest import login_user, register_user, unique_email


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _superadmin_token(client: AsyncClient) -> str:
    return await login_user(
        client,
        settings.bootstrap_admin_email,
        settings.bootstrap_admin_password,
    )


def test_password_roundtrip_dev_encoding(monkeypatch):
    monkeypatch.setattr(settings, "environment", "development")

    import orbiteus_core.mail_settings as ms

    def _fail(*_args, **_kwargs):
        raise RuntimeError("no fernet")

    monkeypatch.setattr("orbiteus_core.ai.keys.encrypt", _fail)
    stored = ms._encrypt_password("secret")
    assert stored.startswith("dev:")
    assert ms._decrypt_password(stored) == "secret"


@pytest.mark.asyncio
async def test_mail_settings_api_roundtrip(client: AsyncClient):
    token = await _superadmin_token(client)

    get0 = await client.get("/api/base/mail/settings", headers=_h(token))
    assert get0.status_code == 200

    put = await client.put(
        "/api/base/mail/settings",
        headers=_h(token),
        json={
            "host": "smtp.test.example",
            "port": 587,
            "user": "mailer",
            "password": "s3cret",
            "use_tls": True,
            "from_address": "noreply@test.example",
        },
    )
    assert put.status_code == 200, put.text
    body = put.json()
    assert body["configured"] is True
    assert body["host"] == "smtp.test.example"
    assert body["has_password"] is True
    assert "password" not in body

    get1 = await client.get("/api/base/mail/settings", headers=_h(token))
    assert get1.json()["source"] == "database"


@pytest.mark.asyncio
async def test_mail_test_connection_requires_host(client: AsyncClient):
    token = await _superadmin_token(client)
    r = await client.post(
        "/api/base/mail/settings/test-connection",
        headers=_h(token),
        json={"host": ""},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_mail_settings_requires_superadmin(client: AsyncClient):
    email = unique_email("mail_user")
    await register_user(client, email=email)
    token = await login_user(client, email)
    r = await client.get("/api/base/mail/settings", headers=_h(token))
    assert r.status_code == 403
