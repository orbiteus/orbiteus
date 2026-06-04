"""Unit tests for attachment storage helpers."""
from __future__ import annotations

import uuid

import pytest

from orbiteus_core.attachments import sanitize_filename
from orbiteus_core.storage import build_storage_key
from orbiteus_core.storage.local import LocalStorage


def test_sanitize_filename_strips_path():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("folder/doc.pdf") == "doc.pdf"


def test_build_storage_key():
    tid = str(uuid.uuid4())
    aid = str(uuid.uuid4())
    key = build_storage_key(tid, aid, "report (1).pdf")
    assert key.startswith(f"{tid}/{aid}/")
    assert "report" in key


@pytest.mark.asyncio
async def test_local_storage_roundtrip(tmp_path):
    storage = LocalStorage(tmp_path)
    key = "tenant/abc/file.txt"
    await storage.put(key, b"payload")
    assert await storage.exists(key)
    assert await storage.get(key) == b"payload"
    await storage.delete(key)
    assert not await storage.exists(key)
