"""Lightweight User-Agent classification for login metadata."""
from __future__ import annotations

import re

_DEVICE_MOBILE = re.compile(
    r"(android|iphone|ipod|mobile|phone|blackberry|windows phone)",
    re.IGNORECASE,
)
_DEVICE_TABLET = re.compile(
    r"(ipad|tablet|kindle|playbook|silk)",
    re.IGNORECASE,
)


def classify_login_device(user_agent: str | None) -> str:
    """Return ``desktop``, ``mobile``, ``tablet``, or ``unknown``."""
    if not user_agent or not user_agent.strip():
        return "unknown"
    ua = user_agent.strip()
    if _DEVICE_TABLET.search(ua):
        return "tablet"
    if _DEVICE_MOBILE.search(ua):
        return "mobile"
    return "desktop"
