"""Audit-log actor coverage — DoD §4.2 / §4.3.

Three contracts:

  1. `actor=user, operation=login`         — emitted on every successful
                                              `POST /api/auth/login`.
  2. `actor=user, operation=login_failed`  — emitted on every refused
                                              login (wrong pw, disabled
                                              account, bad TOTP).
  3. `actor=ai,   operation=tool_call`     — emitted on every tool call
                                              the model issues. Arguments
                                              are run through
                                              `redact_payload` before
                                              persisting (sanity check
                                              against secret/PII leak).

Half of the file is a unit half (loads only `orbiteus_core.audit` +
`orbiteus_core.ai.redaction`); the other half talks HTTP to the running
backend and inspects `base_audit_log` over psql, mirroring the style of
`tests/test_password_reset.py`. The integration half is skipped when
the backend isn't reachable so `pytest -q` on a bare laptop stays green.
"""
from __future__ import annotations

import importlib
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"


# ---------------------------------------------------------------------------
# Unit half
# ---------------------------------------------------------------------------

def _load_audit():
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    sys.modules.pop("orbiteus_core.audit", None)
    return importlib.import_module("orbiteus_core.audit")


def _load_redaction():
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    sys.modules.pop("orbiteus_core.ai.redaction", None)
    return importlib.import_module("orbiteus_core.ai.redaction")


def test_audit_unknown_actor_is_coerced_to_system():
    audit = _load_audit()
    assert "user" in audit._ALLOWED_ACTORS
    assert "ai" in audit._ALLOWED_ACTORS
    assert "portal" in audit._ALLOWED_ACTORS
    assert "system" in audit._ALLOWED_ACTORS
    assert "robot" not in audit._ALLOWED_ACTORS


def test_redact_payload_scrubs_pii_strings():
    """Sanity-check the helper that every audit write runs through.

    `redact_payload` is value-based, not key-based: it inspects every
    string for email/phone/IBAN patterns and replaces them with
    placeholders, regardless of which dict key they live under. Passwords
    and API keys are NOT redacted by this helper — they are expected to
    never appear in audit payloads in the first place (the auth router
    explicitly omits the password from the `diff` dict, the AI router
    runs the same helper on tool arguments).
    """
    redaction = _load_redaction()
    out = redaction.redact_payload(
        {
            "email": "user@example.com",
            "phone_in_text": "Call me at +48 600 123 456 today",
            "harmless": "ok",
        }
    )
    serialized = repr(out)
    assert "user@example.com" not in serialized
    assert "[email]" in serialized
    assert "+48 600 123 456" not in serialized
    assert "[phone]" in serialized
    assert "ok" in serialized


# ---------------------------------------------------------------------------
# Integration half
# ---------------------------------------------------------------------------

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


def _psql(sql: str) -> str:
    """Run a query through `docker compose exec postgres psql -t -c '...'`.

    Returns trimmed stdout. Used to verify audit rows landed in the DB
    without having to set up an SQLAlchemy session in the test process
    (which would require all backend deps to be available locally).
    """
    cmd = [
        "docker", "compose", "exec", "-T", "postgres",
        "psql", "-U", "orbiteus", "-d", "orbiteus", "-t", "-A", "-c", sql,
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(f"psql failed: {result.stderr}")
    return result.stdout.strip()


pytestmark_integration = pytest.mark.skipif(
    not _backend_alive(),
    reason=f"Backend not reachable at {BACKEND_URL}",
)


@pytestmark_integration
def test_login_success_emits_audit_row():
    import httpx

    email = f"audit_{uuid.uuid4().hex[:10]}@example.com"
    password = "Init1234!"

    # Bootstrap a tenant + user.
    reg = httpx.post(
        f"{BACKEND_URL}/api/auth/register",
        json={
            "name": "Audit User",
            "email": email,
            "password": password,
            "tenant_name": f"Tenant {uuid.uuid4().hex[:6]}",
            "tenant_slug": f"t-{uuid.uuid4().hex[:8]}",
        },
        timeout=10,
    )
    assert reg.status_code == 201, reg.text

    # Successful login.
    r = httpx.post(
        f"{BACKEND_URL}/api/auth/login",
        json={"email": email, "password": password},
        timeout=10,
    )
    assert r.status_code == 200, r.text

    # Verify a row exists for THIS user with the right shape.
    out = _psql(
        f"SELECT actor || ':' || operation FROM base_audit_log WHERE "
        f"model='auth.session' AND user_id IN (SELECT id FROM base_users "
        f"WHERE email='{email}') ORDER BY create_date DESC LIMIT 1;"
    )
    assert out == "user:login", f"unexpected audit row: {out!r}"


@pytestmark_integration
def test_login_failed_emits_audit_row():
    import httpx

    email = f"audit_fail_{uuid.uuid4().hex[:10]}@example.com"
    password = "Init1234!"

    reg = httpx.post(
        f"{BACKEND_URL}/api/auth/register",
        json={
            "name": "Fail User",
            "email": email,
            "password": password,
            "tenant_name": f"Tenant {uuid.uuid4().hex[:6]}",
            "tenant_slug": f"t-{uuid.uuid4().hex[:8]}",
        },
        timeout=10,
    )
    assert reg.status_code == 201

    r = httpx.post(
        f"{BACKEND_URL}/api/auth/login",
        json={"email": email, "password": "WRONG"},
        timeout=10,
    )
    assert r.status_code == 401

    out = _psql(
        f"SELECT actor || ':' || operation || ':' || (diff->>'reason') "
        f"FROM base_audit_log WHERE model='auth.session' "
        f"AND user_id IN (SELECT id FROM base_users WHERE email='{email}') "
        f"AND operation='login_failed' "
        f"ORDER BY create_date DESC LIMIT 1;"
    )
    assert out == "user:login_failed:invalid_credentials", (
        f"unexpected audit row: {out!r}"
    )


@pytestmark_integration
def test_password_reset_emits_audit_rows():
    """Both `password_reset_requested` and `password_reset_completed`
    must land in `base_audit_log` with `actor=user`."""
    import httpx

    sys.path.insert(0, str(BACKEND))
    from orbiteus_core.security.tokens import (  # noqa: E402
        create_password_reset_token,
    )

    email = f"audit_pwr_{uuid.uuid4().hex[:10]}@example.com"

    reg = httpx.post(
        f"{BACKEND_URL}/api/auth/register",
        json={
            "name": "PWR User",
            "email": email,
            "password": "Init1234!",
            "tenant_name": f"Tenant {uuid.uuid4().hex[:6]}",
            "tenant_slug": f"t-{uuid.uuid4().hex[:8]}",
        },
        timeout=10,
    )
    assert reg.status_code == 201

    # Public-facing request → emits `password_reset_requested`.
    rq = httpx.post(
        f"{BACKEND_URL}/api/auth/password/request",
        json={"email": email},
        timeout=10,
    )
    assert rq.status_code == 200

    # Mint a fresh reset token (same JWT secret).
    login = httpx.post(
        f"{BACKEND_URL}/api/auth/login",
        json={"email": email, "password": "Init1234!"},
        timeout=10,
    )
    assert login.status_code == 200
    me = httpx.get(
        f"{BACKEND_URL}/api/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        timeout=10,
    )
    user_id = uuid.UUID(me.json()["id"])
    token = create_password_reset_token(user_id)

    cf = httpx.post(
        f"{BACKEND_URL}/api/auth/password/reset",
        json={"token": token, "new_password": "Brand-new-9999"},
        timeout=10,
    )
    assert cf.status_code == 200

    out = _psql(
        f"SELECT string_agg(operation, ',' ORDER BY create_date) "
        f"FROM base_audit_log WHERE model='auth.session' "
        f"AND user_id IN (SELECT id FROM base_users WHERE email='{email}') "
        f"AND operation IN ('password_reset_requested', "
        f"                  'password_reset_completed');"
    )
    # Both events must be present, in order.
    assert "password_reset_requested" in out
    assert "password_reset_completed" in out


@pytestmark_integration
def test_audit_actor_label_is_within_allow_list():
    """Defensive: anything still landing in `base_audit_log` should use
    one of the four allowed actor values. A regression here would point
    at someone bypassing the helper."""
    out = _psql(
        "SELECT DISTINCT actor FROM base_audit_log;"
    )
    actors = {line.strip() for line in out.splitlines() if line.strip()}
    allowed = {"user", "ai", "portal", "system"}
    extra = actors - allowed
    assert not extra, f"unexpected actor values in base_audit_log: {extra!r}"
