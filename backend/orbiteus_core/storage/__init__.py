"""Attachment filestore — local backend by default."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from orbiteus_core.config import settings
from orbiteus_core.storage.base import StorageBackend
from orbiteus_core.storage.local import LocalStorage


@lru_cache(maxsize=1)
def get_storage() -> StorageBackend:
    """Return the configured storage backend singleton."""
    backend = settings.attachment_storage.lower()
    if backend == "local":
        return LocalStorage(Path(settings.attachment_storage_path))
    raise RuntimeError(
        f"Unsupported ATTACHMENT_STORAGE={backend!r} — only 'local' is implemented"
    )


def build_storage_key(
    tenant_id: str,
    attachment_id: str,
    filename: str,
) -> str:
    """Deterministic object key: ``{tenant}/{id}/{safe_name}``."""
    from orbiteus_core.attachments import sanitize_filename

    safe = sanitize_filename(filename)
    return f"{tenant_id}/{attachment_id}/{safe}"
