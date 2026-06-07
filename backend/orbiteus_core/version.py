"""Orbiteus release version (SemVer) for health probes and operator UI."""
from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_PYPROJECT = _BACKEND_ROOT / "pyproject.toml"


def _read_pyproject_version() -> str | None:
    """Read ``[project].version`` from the backend tree (works with dev volume mounts)."""
    if not _PYPROJECT.is_file():
        return None
    text = _PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    return match.group(1) if match else None


def _read_installed_version() -> str | None:
    try:
        from importlib.metadata import version

        return version("orbiteus")
    except Exception:
        return None


@lru_cache(maxsize=1)
def get_orbiteus_version() -> str:
    """Return the running Orbiteus version.

    Priority:
    1. ``ORBITEUS_VERSION`` env (CI / tagged deploy)
    2. ``backend/pyproject.toml`` on disk (dev bind-mount; avoids stale editable metadata)
    3. Installed package metadata (production wheels)
    4. ``dev``
    """
    override = os.environ.get("ORBITEUS_VERSION", "").strip()
    if override:
        return override

    from_file = _read_pyproject_version()
    if from_file:
        return from_file

    installed = _read_installed_version()
    if installed:
        return installed

    return "dev"
