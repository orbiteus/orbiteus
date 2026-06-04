"""Pure unit tests for BaseRepository diff/snapshot/redaction logic.

Avoids DB and SQLAlchemy by testing static helpers against a stub dataclass.
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path
from uuid import uuid4

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "backend"

# Make `orbiteus_core` importable.
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

# Stub modules that BaseRepository would otherwise pull in transitively.
import types

stub_db = types.ModuleType("orbiteus_core.db")
stub_db.metadata = None  # type: ignore[attr-defined]
sys.modules.setdefault("orbiteus_core.db", stub_db)


def _import_repo():
    # Import lazily so stubs above are honored.
    from orbiteus_core.base_domain import BaseModel
    from orbiteus_core.repository import BaseRepository

    return BaseRepository, BaseModel


@dataclasses.dataclass
class _Person:  # mimics a BaseModel-shaped dataclass without the real base
    id: object = None
    tenant_id: object = None
    company_id: object = None
    create_date: object = None
    write_date: object = None
    active: bool = True
    custom_fields: dict = dataclasses.field(default_factory=dict)
    created_by_id: object = None
    modified_by_id: object = None
    name: str = ""
    email: str = ""
    password_hash: str = ""


class _Repo:
    """Tiny shell that exposes the static helpers for unit testing."""

    domain_class = _Person

    _AUDIT_REDACT_FIELDS = {"password_hash", "totp_secret"}
    _AUDIT_SKIP_FIELDS = {"create_date", "write_date", "custom_fields"}

    # Bind the methods we want to exercise.
    from orbiteus_core.repository import BaseRepository as _Real

    _snapshot = _Real._snapshot
    _diff_for_create = _Real._diff_for_create
    _diff = staticmethod(_Real._diff)


def test_snapshot_skips_volatile_fields_and_redacts_secrets():
    repo = _Repo()
    p = _Person(name="Alice", password_hash="hunter2")
    snap = repo._snapshot(p)

    assert "create_date" not in snap
    assert "write_date" not in snap
    assert "custom_fields" not in snap
    assert snap["name"] == "Alice"
    assert snap["password_hash"] == "***"
    assert snap["active"] is True


def test_diff_for_create_omits_empties():
    repo = _Repo()
    p = _Person(name="Alice")
    diff = repo._diff_for_create(p)

    # Non-empty fields appear with [None, value]; empties are skipped.
    assert diff["name"] == [None, "Alice"]
    assert "email" not in diff
    assert "tenant_id" not in diff


def test_diff_returns_changed_fields_only():
    repo = _Repo()
    old = {"name": "Alice", "email": "a@b", "active": True}
    new = {"name": "Alice", "email": "c@d", "active": True}
    out = repo._diff(old, new)
    assert out == {"email": ["a@b", "c@d"]}


def test_diff_handles_added_or_removed_keys():
    repo = _Repo()
    old = {"name": "Alice"}
    new = {"name": "Alice", "email": "x@y"}
    assert repo._diff(old, new) == {"email": [None, "x@y"]}


def test_audit_optout_models_constant():
    from orbiteus_core.repository import AUDIT_OPTOUT_MODELS

    assert "base.audit-log" in AUDIT_OPTOUT_MODELS
    assert "base.outbox" in AUDIT_OPTOUT_MODELS
    assert "base.embedding-record" in AUDIT_OPTOUT_MODELS


def test_request_context_has_actor_and_request_id():
    from orbiteus_core.context import RequestContext

    ctx = RequestContext(actor="ai", request_id="req_test", scope="ai")
    assert ctx.actor == "ai"
    assert ctx.request_id == "req_test"
    assert ctx.scope == "ai"


def test_base_model_has_attribution_columns():
    from orbiteus_core.base_domain import BaseModel

    fields = {f.name for f in dataclasses.fields(BaseModel)}
    assert {"created_by_id", "modified_by_id"} <= fields


def test_make_base_columns_emits_attribution():
    from orbiteus_core.mapper import make_base_columns

    cols = {c.name for c in make_base_columns()}
    assert {"created_by_id", "modified_by_id"} <= cols
