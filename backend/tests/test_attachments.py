"""Tests for attachment filestore + API."""
from __future__ import annotations

import io

import pytest
from httpx import AsyncClient

from orbiteus_core.config import settings
from orbiteus_core.security.tokens import decode_access_token
from tests.conftest import login_user, register_user, unique_email


def _patch_storage(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "attachment_storage_path", str(tmp_path))
    from orbiteus_core.storage import get_storage

    get_storage.cache_clear()


async def _registered_session(client: AsyncClient) -> tuple[dict[str, str], str]:
    email = unique_email("attach")
    reg = await register_user(client, email=email)
    token = reg["access_token"]
    company_id = decode_access_token(token)["company_id"]
    assert company_id is not None
    return {"Authorization": f"Bearer {token}"}, company_id


async def _bootstrap_headers(client: AsyncClient) -> dict[str, str]:
    token = await login_user(
        client,
        settings.bootstrap_admin_email,
        settings.bootstrap_admin_password,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_attachment_upload_download_roundtrip(client: AsyncClient, tmp_path, monkeypatch):
    _patch_storage(tmp_path, monkeypatch)

    headers, company_id = await _registered_session(client)

    payload = b"hello attachment bytes"
    resp = await client.post(
        "/api/base/attachments",
        headers=headers,
        data={
            "res_model": "base.company",
            "res_id": company_id,
            "description": "test doc",
        },
        files={"file": ("notes.txt", io.BytesIO(payload), "text/plain")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    attachment_id = body["id"]
    assert body["name"] == "notes.txt"
    assert body["file_size"] == len(payload)

    dl = await client.get(
        f"/api/base/attachments/{attachment_id}/download",
        headers=headers,
    )
    assert dl.status_code == 200
    assert dl.content == payload

    listing = await client.get(
        "/api/base/attachments",
        headers=headers,
        params={"res_model": "base.company", "res_id": company_id},
    )
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1
    assert any(i["id"] == attachment_id for i in listing.json()["items"])


@pytest.mark.asyncio
async def test_attachment_tenant_isolation(client: AsyncClient, tmp_path, monkeypatch):
    _patch_storage(tmp_path, monkeypatch)

    headers_a, company_id = await _registered_session(client)

    upload_a = await client.post(
        "/api/base/attachments",
        headers=headers_a,
        data={"res_model": "base.company", "res_id": company_id},
        files={"file": ("secret.txt", io.BytesIO(b"tenant-a"), "text/plain")},
    )
    assert upload_a.status_code == 200
    att_id = upload_a.json()["id"]

    headers_b, _ = await _registered_session(client)

    dl = await client.get(
        f"/api/base/attachments/{att_id}/download",
        headers=headers_b,
    )
    assert dl.status_code in {403, 404}


@pytest.mark.asyncio
async def test_attachment_tenant_wide_search_requires_system(client: AsyncClient):
    headers, _ = await _registered_session(client)
    resp = await client.get("/api/base/attachments", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_attachment_tenant_wide_search_for_system(client: AsyncClient, tmp_path, monkeypatch):
    _patch_storage(tmp_path, monkeypatch)
    headers = await _bootstrap_headers(client)
    resp = await client.get("/api/base/attachments", headers=headers, params={"q": "notes"})
    assert resp.status_code == 200
    assert "items" in resp.json()


@pytest.mark.asyncio
async def test_attachment_delete_removes_binary(client: AsyncClient, tmp_path, monkeypatch):
    _patch_storage(tmp_path, monkeypatch)

    headers, company_id = await _registered_session(client)

    upload = await client.post(
        "/api/base/attachments",
        headers=headers,
        data={"res_model": "base.company", "res_id": company_id},
        files={"file": ("gone.txt", io.BytesIO(b"bye"), "text/plain")},
    )
    assert upload.status_code == 200
    att_id = upload.json()["id"]

    deleted = await client.delete(f"/api/base/attachments/{att_id}", headers=headers)
    assert deleted.status_code == 200

    dl = await client.get(
        f"/api/base/attachments/{att_id}/download",
        headers=headers,
    )
    assert dl.status_code == 404


@pytest.mark.asyncio
async def test_delete_company_cascades_attachments(
    client: AsyncClient,
    tmp_path,
    monkeypatch,
):
    """Unlinking a business record removes its attachment rows from the catalog."""
    _patch_storage(tmp_path, monkeypatch)
    headers = await _bootstrap_headers(client)

    created = await client.post(
        "/api/base/company",
        headers=headers,
        json={
            "name": "Attachment orphan test Co",
            "currency_code": "USD",
            "country_code": "US",
            "email": "orphan-test@example.com",
            "city": "Test",
            "vat": "US-ORPHAN-1",
        },
    )
    assert created.status_code in {200, 201}, created.text
    company_id = created.json()["id"]

    upload = await client.post(
        "/api/base/attachments",
        headers=headers,
        data={"res_model": "base.company", "res_id": company_id},
        files={"file": ("orphan-test.txt", io.BytesIO(b"x"), "text/plain")},
    )
    assert upload.status_code == 200
    att_id = upload.json()["id"]

    deleted = await client.delete(f"/api/base/company/{company_id}", headers=headers)
    assert deleted.status_code in {200, 204}

    listing = await client.get("/api/base/attachments", headers=headers, params={"q": "orphan-test"})
    assert listing.status_code == 200
    assert not any(i["id"] == att_id for i in listing.json()["items"])


@pytest.mark.asyncio
async def test_purge_orphan_attachments(client: AsyncClient, tmp_path, monkeypatch):
    """Legacy rows without a parent record are removed by purge-orphans."""
    from sqlalchemy import delete

    from orbiteus_core.db import AsyncSessionFactory
    from modules.base.model.mapping import companies_table

    _patch_storage(tmp_path, monkeypatch)
    headers = await _bootstrap_headers(client)

    created = await client.post(
        "/api/base/company",
        headers=headers,
        json={
            "name": "Purge orphan test",
            "currency_code": "USD",
            "country_code": "US",
            "email": "purge@example.com",
            "city": "Test",
            "vat": "US-PURGE-1",
        },
    )
    assert created.status_code in {200, 201}
    company_id = created.json()["id"]

    upload = await client.post(
        "/api/base/attachments",
        headers=headers,
        data={"res_model": "base.company", "res_id": company_id},
        files={"file": ("purge-me.txt", io.BytesIO(b"x"), "text/plain")},
    )
    assert upload.status_code == 200
    att_id = upload.json()["id"]

    import uuid

    async with AsyncSessionFactory() as session:
        await session.execute(
            delete(companies_table).where(
                companies_table.c.id == uuid.UUID(company_id)
            )
        )
        await session.commit()

    listing = await client.get(
        "/api/base/attachments",
        headers=headers,
        params={"q": "purge-me"},
    )
    assert any(i["id"] == att_id for i in listing.json()["items"])

    purged = await client.post("/api/base/attachments/purge-orphans", headers=headers)
    assert purged.status_code == 200
    assert purged.json()["removed"] >= 1

    listing2 = await client.get(
        "/api/base/attachments",
        headers=headers,
        params={"q": "purge-me"},
    )
    assert not any(i["id"] == att_id for i in listing2.json()["items"])
