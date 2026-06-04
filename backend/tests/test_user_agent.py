"""User-Agent device classification."""
from __future__ import annotations

import pytest

from orbiteus_core.user_agent import classify_login_device


@pytest.mark.parametrize(
    ("user_agent", "expected"),
    [
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0",
            "desktop",
        ),
        (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
            "mobile",
        ),
        (
            "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
            "tablet",
        ),
        ("", "unknown"),
        (None, "unknown"),
    ],
)
def test_classify_login_device(user_agent: str | None, expected: str) -> None:
    assert classify_login_device(user_agent) == expected
