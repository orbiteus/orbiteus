"""Unit tests for audit initiator enrichment."""
from __future__ import annotations

import uuid

from orbiteus_core.audit_initiator import build_initiator


def test_user_initiator_uses_joined_email_and_name():
    uid = uuid.uuid4()
    users = {str(uid): ("admin@example.com", "Admin User")}
    out = build_initiator(
        actor="user",
        user_id=uid,
        diff=None,
        metadata={"ip": "10.0.0.1"},
        users=users,
    )
    assert out["kind"] == "user"
    assert out["label"] == "Admin User (admin@example.com)"
    assert out["user_email"] == "admin@example.com"
    assert "IP 10.0.0.1" in (out["detail"] or "")


def test_user_initiator_falls_back_to_diff_email():
    out = build_initiator(
        actor="user",
        user_id=None,
        diff={"email": "[email]", "reason": "invalid_credentials"},
        metadata={"ip": "172.20.0.5"},
        users={},
    )
    assert out["label"] == "[email]"


def test_ai_initiator_shows_delegated_user():
    uid = uuid.uuid4()
    users = {str(uid): ("owner@example.com", "Owner")}
    out = build_initiator(
        actor="ai",
        user_id=uid,
        diff={"name": "read_crm_lead"},
        metadata={"provider": "openai", "agent_run_id": str(uuid.uuid4())},
        users=users,
    )
    assert out["kind"] == "ai"
    assert "on behalf of Owner (owner@example.com)" in out["label"]
    assert out["detail"] and out["detail"].startswith("provider openai")


def test_portal_initiator_labels_share_owner():
    uid = uuid.uuid4()
    users = {str(uid): ("seller@example.com", "Seller")}
    out = build_initiator(
        actor="portal",
        user_id=uid,
        diff={"comment": "Looks good"},
        metadata={"scope": "portal"},
        users=users,
    )
    assert out["kind"] == "portal"
    assert out["label"] == "Portal · shared by Seller (seller@example.com)"


def test_system_initiator_webhook_and_cron():
    wh = build_initiator(
        actor="system",
        user_id=None,
        diff=None,
        metadata={"webhook_name": "CRM lead created"},
        users={},
    )
    assert wh["label"] == "Webhook · CRM lead created"

    cron = build_initiator(
        actor="system",
        user_id=None,
        diff=None,
        metadata={"cron_job": "outbox.dispatch"},
        users={},
    )
    assert cron["label"] == "Scheduled job · outbox.dispatch"
