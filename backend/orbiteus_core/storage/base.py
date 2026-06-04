"""Attachment storage backends (local filesystem; S3-compatible later)."""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    """Store attachment binaries outside PostgreSQL."""

    async def put(self, key: str, data: bytes) -> None:
        """Persist bytes at ``key`` (tenant-scoped path)."""

    async def get(self, key: str) -> bytes:
        """Load bytes; raise ``FileNotFoundError`` when missing."""

    async def delete(self, key: str) -> None:
        """Remove object if present (no error when already gone)."""

    async def exists(self, key: str) -> bool:
        """Return whether ``key`` is stored."""
