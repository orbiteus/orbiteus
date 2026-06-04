"""Local filesystem attachment storage (development and single-node prod)."""
from __future__ import annotations

import asyncio
from pathlib import Path


class LocalStorage:
    """Writes files under a configurable root directory."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # Reject traversal — keys must be relative object paths only.
        normalized = key.replace("\\", "/").lstrip("/")
        if ".." in normalized.split("/"):
            raise ValueError(f"Invalid storage key: {key!r}")
        path = (self._root / normalized).resolve()
        if not str(path).startswith(str(self._root)):
            raise ValueError(f"Storage key escapes root: {key!r}")
        return path

    async def put(self, key: str, data: bytes) -> None:
        path = self._path(key)
        await asyncio.to_thread(self._write_bytes, path, data)

    @staticmethod
    def _write_bytes(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    async def get(self, key: str) -> bytes:
        path = self._path(key)
        if not path.is_file():
            raise FileNotFoundError(key)
        return await asyncio.to_thread(path.read_bytes)

    async def delete(self, key: str) -> None:
        path = self._path(key)
        if path.is_file():
            await asyncio.to_thread(path.unlink)

    async def exists(self, key: str) -> bool:
        return self._path(key).is_file()
