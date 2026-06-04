"""Unit tests for rate-limit middleware policy helpers."""
from __future__ import annotations

from orbiteus_core.security.rate_limit_middleware import (
    _is_exempt_path,
    _is_expensive_get,
    _is_safe_authenticated_read,
)


def test_ui_config_and_realtime_are_exempt():
    assert _is_exempt_path("/api/base/ui-config")
    assert _is_exempt_path("/api/realtime/subscribe")


def test_authenticated_list_reads_are_safe():
    assert _is_safe_authenticated_read("GET", "/api/base/company")
    assert _is_safe_authenticated_read("GET", "/api/base/user")
    assert _is_safe_authenticated_read("HEAD", "/api/auth/me")


def test_mutations_are_not_safe_reads():
    assert not _is_safe_authenticated_read("POST", "/api/base/company")
    assert not _is_safe_authenticated_read("PUT", "/api/base/company/abc")
    assert not _is_safe_authenticated_read("DELETE", "/api/base/company/abc")


def test_ai_gets_remain_expensive():
    assert _is_expensive_get("GET", "/api/ai/actions")
    assert not _is_safe_authenticated_read("GET", "/api/ai/actions")
