"""Per-IP, per-user, per-tenant rate-limit buckets — DoD §7.3 / §7.4.

The middleware in `orbiteus_core/security/rate_limit_middleware.py`
applies three independent buckets, in order:

  1. `rl:ip:<client_host>`        (always)
  2. `rl:tenant:<tenant_id>`      (when the request carries a verified
                                   access token)
  3. `rl:user:<user_id>`          (same)

Each bucket is a per-minute Redis counter. The first bucket that
exceeds its limit returns ``429`` with ``Retry-After`` and a body
``{"detail":"Rate limit exceeded","code":"rate_limit.exceeded",
"bucket": "<bucket_name>"}``.

Authenticated GET/list traffic is **not** limited (SPA navigation).
These tests cover mutation buckets and anonymous IP protection.

They run against the live dev compose backend on
``BACKEND_URL`` (default ``http://localhost:8000``). They flush the
relevant Redis keys via ``redis-cli`` before each scenario so a
previously-burned bucket from another test or from a manual session
doesn't poison this one. Skipped automatically when the backend isn't
reachable.
"""
from __future__ import annotations

import os
import subprocess
import time
import uuid
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


def _backend_alive() -> bool:
    try:
        import httpx
    except ImportError:
        return False
    try:
        r = httpx.get(f"{BACKEND_URL}/health", timeout=1.5)
        return r.status_code < 500
    except Exception:  # noqa: BLE001
        return False


def _flush_redis_pattern(pattern: str) -> None:
    """Delete every Redis key matching the given pattern.

    We shell out to ``redis-cli`` inside the dev compose stack so the
    test doesn't need to recreate an async client just for cleanup.
    """
    cmd = (
        f"docker compose exec -T redis sh -c "
        f"'redis-cli --scan --pattern \"{pattern}\" | "
        f"xargs -r redis-cli DEL >/dev/null'"
    )
    subprocess.run(cmd, shell=True, cwd=str(REPO_ROOT), check=False, timeout=5)


pytestmark = pytest.mark.skipif(
    not _backend_alive(),
    reason=f"Backend not reachable at {BACKEND_URL}",
)


@pytest.fixture(autouse=True)
def _flush_buckets_before_each_test():
    """Drop every `rl:*` key so a previous test's traffic doesn't
    pre-warm the IP bucket and turn this test into a flaky 429.

    Earlier integration tests in the suite (`test_password_reset`,
    `test_aggregate_endpoint`, `test_fk_resolution`) call register +
    login from the same localhost, so they share the IP bucket with
    these. Without an autouse flush the rate-limit suite has to wait
    a full minute for the previous tests' rate-limit window to roll
    over.
    """
    _flush_redis_pattern("rl:*")
    yield
    _flush_redis_pattern("rl:*")


def _register_user(prefix: str = "rl") -> tuple[str, str]:
    """Bootstrap a fresh tenant + user via `/api/auth/register`.

    Returns (email, password).
    """
    import httpx

    email = f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"
    password = "Init1234!"
    r = httpx.post(
        f"{BACKEND_URL}/api/auth/register",
        json={
            "name": "RL User",
            "email": email,
            "password": password,
            "tenant_name": f"Tenant {uuid.uuid4().hex[:6]}",
            "tenant_slug": f"t-{uuid.uuid4().hex[:8]}",
        },
        timeout=10,
    )
    assert r.status_code == 201, r.text
    return email, password


def _login(email: str, password: str) -> str:
    """Log in and return the access token."""
    import httpx

    r = httpx.post(
        f"{BACKEND_URL}/api/auth/login",
        json={"email": email, "password": password},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


# ---------------------------------------------------------------------------
# Per-user bucket
# ---------------------------------------------------------------------------

def test_user_bucket_returns_429_with_retry_after():
    """Hammering authenticated POST mutations past
    `rate_limit_user_mutations_per_minute` triggers 429."""
    import httpx

    email, password = _register_user("user_bucket")
    token = _login(email, password)
    headers = {"Authorization": f"Bearer {token}"}

    # Default mutation limit is 600/min. Burst POSTs (validation may fail,
    # but middleware counts every attempt).
    statuses: list[int] = []
    last_body: dict | None = None
    last_retry_after: str | None = None

    with httpx.Client(timeout=10) as http:
        for _ in range(650):
            r = http.post(
                f"{BACKEND_URL}/api/crm/person",
                headers=headers,
                json={},
            )
            statuses.append(r.status_code)
            if r.status_code == 429:
                last_body = r.json()
                last_retry_after = r.headers.get("retry-after")
                break

    assert 429 in statuses, (
        "user mutation bucket never refused even after 650 POSTs "
        f"(statuses sampled: {statuses[:10]} ... {statuses[-5:]})"
    )
    assert last_body is not None
    assert last_body["code"] == "rate_limit.exceeded"
    assert last_body["bucket"].startswith("user:"), (
        f"first bucket to trip should be user:, got {last_body['bucket']!r}"
    )
    assert last_retry_after is not None
    assert int(last_retry_after) > 0


def test_authenticated_list_reads_never_429_under_navigation_burst():
    """Rapid GET /api/crm/* (SPA navigation) must not hit 429."""
    import httpx

    email, password = _register_user("read_burst")
    token = _login(email, password)
    headers = {"Authorization": f"Bearer {token}"}

    with httpx.Client(timeout=10) as http:
        for model in ("person", "lead", "stage", "team") * 25:
            r = http.get(f"{BACKEND_URL}/api/crm/{model}", headers=headers)
            assert r.status_code != 429, (
                f"GET /api/crm/{model} returned 429 during navigation burst"
            )


# ---------------------------------------------------------------------------
# Per-tenant bucket
# ---------------------------------------------------------------------------

def test_tenant_bucket_blocks_when_exceeded():
    """Two distinct users in the same tenant share a tenant bucket.

    We mint two users in *different* tenants here (since `/register`
    creates a new tenant per call), so to keep the test self-contained
    and fast we only assert the fundamental invariant: when the tenant
    bucket key is artificially set above the limit in Redis, the very
    next authenticated request is refused with `bucket: "tenant:..."`.
    """
    import httpx

    # Cleanly create one user.
    email, password = _register_user("tenant_bucket")
    token = _login(email, password)
    headers = {"Authorization": f"Bearer {token}"}

    # Pull tenant_id out of /me.
    r = httpx.get(f"{BACKEND_URL}/api/auth/me", headers=headers, timeout=10)
    assert r.status_code == 200, r.text
    tenant_id = r.json().get("tenant_id")
    assert tenant_id, "user has no tenant_id"

    # Push the tenant bucket above the configured limit. Default limit
    # is 1000/min. We force it to 9999 so the very next request crosses.
    minute = int(time.time()) // 60
    bucket_key = f"rl:tenant:{tenant_id}:{minute}"
    cmd = (
        f"docker compose exec -T redis redis-cli SET '{bucket_key}' 9999 EX 90"
    )
    subprocess.run(cmd, shell=True, cwd=str(REPO_ROOT), check=True, timeout=5)

    try:
        r = httpx.get(f"{BACKEND_URL}/api/auth/me", headers=headers, timeout=10)
        # Any subsequent call MUST hit the tenant bucket first.
        assert r.status_code == 429, r.text
        body = r.json()
        assert body["code"] == "rate_limit.exceeded"
        assert body["bucket"].startswith("tenant:"), (
            f"expected tenant:* bucket, got {body['bucket']!r}"
        )
        assert int(r.headers.get("retry-after", "0")) > 0
    finally:
        # Clear so we don't poison subsequent tests.
        _flush_redis_pattern(f"rl:tenant:{tenant_id}:*")
        _flush_redis_pattern(f"rl:user:*")


# ---------------------------------------------------------------------------
# IP bucket still works for unauthenticated traffic
# ---------------------------------------------------------------------------

def test_ip_bucket_protects_anonymous_traffic():
    """`rl:ip:<host>` bucket continues to apply to unauthenticated paths.

    The default IP limit is 120/min. We aim a small burst at the
    public `/api/auth/login` endpoint with a deliberately wrong
    password so the request flows through the middleware (and hits
    the IP bucket) on every call.
    """
    import httpx

    # Clean slate.
    _flush_redis_pattern("rl:ip:*")

    statuses: list[int] = []
    last_body: dict | None = None

    with httpx.Client(timeout=10) as http:
        for _ in range(150):
            r = http.post(
                f"{BACKEND_URL}/api/auth/login",
                json={"email": "rl@example.com", "password": "WRONG"},
            )
            statuses.append(r.status_code)
            if r.status_code == 429:
                last_body = r.json()
                break

    assert 429 in statuses, (
        "ip bucket never refused after 150 requests "
        f"(statuses: ... {statuses[-10:]})"
    )
    assert last_body is not None
    assert last_body["bucket"].startswith("ip:")

    # Cleanup so the next test starts fresh.
    _flush_redis_pattern("rl:ip:*")
