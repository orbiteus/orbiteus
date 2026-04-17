"""Auth module — routes live in ``controller.router`` (single source of truth).

The registry prefers ``modules.auth.controller.router``; this module re-exports
the same ``router`` so ``modules.auth.router`` remains a valid fallback path.
"""
from __future__ import annotations

from modules.auth.controller.router import router

__all__ = ["router"]
