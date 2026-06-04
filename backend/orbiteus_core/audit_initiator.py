"""Human-readable initiator labels for `base_audit_log` rows.

The audit table stores machine-oriented fields (`actor`, `user_id`,
`request_id`, `metadata`). API list endpoints enrich each row with an
`initiator` object so admin UI can answer "who triggered this?" without
joining UUIDs client-side.
"""
from __future__ import annotations

import uuid
from typing import Any, Mapping


UserLookup = Mapping[str, tuple[str, str]]  # user_id str -> (email, name)


def _short_uuid(value: uuid.UUID | str | None) -> str:
    if value is None:
        return ""
    s = str(value)
    return f"{s[:8]}…" if len(s) >= 8 else s


def _user_display(
    user_id: uuid.UUID | str | None,
    users: UserLookup,
) -> tuple[str | None, str | None, str | None]:
    """Return (email, name, label) when the user row is known."""
    if user_id is None:
        return None, None, None
    key = str(user_id)
    row = users.get(key)
    if row is None:
        return None, None, f"User {_short_uuid(user_id)}"
    email, name = row
    name = (name or "").strip()
    email = (email or "").strip()
    if name and email:
        return email, name, f"{name} ({email})"
    if email:
        return email, name or None, email
    if name:
        return None, name, name
    return None, None, f"User {_short_uuid(user_id)}"


def _diff_email(diff: dict[str, Any] | None) -> str | None:
    if not diff:
        return None
    raw = diff.get("email")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def _metadata_str(metadata: dict[str, Any] | None, key: str) -> str | None:
    if not metadata:
        return None
    val = metadata.get(key)
    if val is None:
        return None
    s = str(val).strip()
    return s or None


def build_initiator(
    *,
    actor: str,
    user_id: uuid.UUID | str | None,
    request_id: str | None = None,
    diff: dict[str, Any] | None,
    metadata: dict[str, Any] | None,
    users: UserLookup,
) -> dict[str, Any]:
    """Build a stable `initiator` payload for one audit row."""
    meta = metadata or {}
    email, name, user_label = _user_display(user_id, users)
    details: list[str] = []

    if meta.get("superadmin"):
        details.append("superadmin session")
    if ip := _metadata_str(meta, "ip"):
        details.append(f"IP {ip}")
    if req := (request_id or _metadata_str(meta, "request_id")):
        details.append(f"request {req}")

    kind = actor if actor in {"user", "ai", "portal", "system"} else "system"

    if kind == "user":
        label = user_label or _diff_email(diff) or "Unknown user"
        if scope := _metadata_str(meta, "scope"):
            if scope not in ("internal",):
                details.append(f"scope {scope}")

    elif kind == "ai":
        provider = _metadata_str(meta, "provider")
        if user_label:
            label = f"AI · on behalf of {user_label}"
        else:
            label = "AI assistant"
        if provider:
            details.insert(0, f"provider {provider}")
        if run_id := _metadata_str(meta, "agent_run_id"):
            details.append(f"run {_short_uuid(run_id)}")

    elif kind == "portal":
        if user_label:
            label = f"Portal · shared by {user_label}"
        else:
            label = "Portal share link"

    else:  # system
        source = _metadata_str(meta, "source")
        webhook = _metadata_str(meta, "webhook_name") or _metadata_str(meta, "webhook_id")
        cron = _metadata_str(meta, "cron_job") or _metadata_str(meta, "task")
        if webhook:
            label = f"Webhook · {webhook}"
        elif cron:
            label = f"Scheduled job · {cron}"
        elif source:
            label = f"System · {source}"
        elif _metadata_str(meta, "scope") == "internal":
            label = "System job"
        else:
            label = "System"

    detail = " · ".join(details) if details else None

    return {
        "kind": kind,
        "label": label,
        "detail": detail,
        "user_email": email,
        "user_name": name,
    }


async def load_users_for_audit_rows(
    session: Any,
    rows: list[Mapping[str, Any]],
) -> UserLookup:
    """Batch-load `base_users` email/name for distinct `user_id` values."""
    from sqlalchemy import select

    from modules.base.model.mapping import users_table as users

    ids = {r["user_id"] for r in rows if r.get("user_id") is not None}
    if not ids:
        return {}

    result = await session.execute(
        select(users.c.id, users.c.email, users.c.name).where(users.c.id.in_(ids))
    )
    return {
        str(row.id): (row.email or "", row.name or "")
        for row in result
    }
