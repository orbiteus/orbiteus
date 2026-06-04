"""Audit-log helpers (DoD §4.x).

The `base_audit_log` table is the canonical, append-only ledger of "who
did what, when, on which record". The repository layer
(`BaseRepository.create/update/delete`) writes to it for every CRUD
mutation. The pieces that don't go through the repository — login
events, password resets, AI tool calls, share-link operations — write
directly via this helper.

Schema reminder (`modules/base/model/mapping.py:306`):

    id           uuid           PK
    create_date  timestamptz
    write_date   timestamptz
    tenant_id    uuid?          (NULL for system-level events)
    actor        varchar(20)    "user" | "ai" | "portal" | "system"
    user_id      uuid?          (NULL when no authenticated user yet)
    request_id   varchar(64)?
    model        varchar(255)   (e.g. "auth.session", "ai.tool", "crm.lead")
    record_id    uuid?
    operation    varchar(50)    (e.g. "login", "login_failed",
                                 "password_reset", "tool_call")
    diff         json           sanitized payload
    metadata     json           free-form context (IP, UA, model name…)

Sanitization
------------
Anything that may contain user-supplied free-text passes through
`orbiteus_core.ai.redaction.redact_payload` so passwords, secrets and
common PII don't end up persisted forever. Internal fields (jti, ids,
operation names) are passed through as-is.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


# Allow-list of `actor` values. Mirrors the `varchar(20)` column +
# documentation in `docs/04-data-model.md`.
_ALLOWED_ACTORS = frozenset({"user", "ai", "portal", "system"})


async def write_audit(
    session: AsyncSession,
    *,
    actor: str,
    operation: str,
    model: str,
    tenant_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    record_id: uuid.UUID | None = None,
    request_id: str | None = None,
    diff: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    redact: bool = True,
    autocommit: bool = False,
) -> None:
    """Append a row to `base_audit_log`.

    Errors are logged but never raised — observability MUST NOT break
    the user-visible request. (E.g. a transient DB hiccup during a
    failed-login audit must not turn the 401 into a 500.)

    Parameters
    ----------
    session
        An open `AsyncSession`. By default we DO NOT commit — the
        caller's surrounding transaction owns the lifecycle. Pass
        ``autocommit=True`` for code paths that don't have a clear
        transaction boundary (e.g. login, where the caller is about to
        return tokens regardless of audit success).
    actor
        One of "user", "ai", "portal", "system". Anything else is
        coerced to "system" with a warning.
    operation
        Free-form short string. Conventions:
            login / login_failed
            logout
            password_reset_requested / password_reset_completed
            tool_call                     (AI)
            create / update / delete      (repository CRUD)
    model
        Dotted model name (e.g. "auth.session", "ai.tool",
        "crm.lead"). For non-record events use a synthetic name in
        the `<module>.<noun>` namespace.
    redact
        When True (default), `diff` is passed through
        `redact_payload` so passwords / secrets / common PII are
        replaced with ``***`` before persisting.
    """
    if actor not in _ALLOWED_ACTORS:
        logger.warning("audit.unknown_actor coerced=system actor=%r", actor)
        actor = "system"

    safe_diff: dict[str, Any] = diff or {}
    if redact and safe_diff:
        try:
            from orbiteus_core.ai.redaction import redact_payload

            safe_diff = redact_payload(safe_diff)
        except Exception:  # noqa: BLE001
            # Never let redaction failure stop the audit row from being
            # written — but make sure we don't persist the raw payload.
            logger.warning("audit.redact_failed model=%s op=%s", model, operation, exc_info=True)
            safe_diff = {"_redaction_failed": True}

    safe_meta: dict[str, Any] = metadata or {}

    try:
        from modules.base.model.mapping import base_audit_log_table as audit

        now = datetime.now(timezone.utc)
        await session.execute(
            insert(audit).values(
                id=uuid.uuid4(),
                create_date=now,
                write_date=now,
                tenant_id=tenant_id,
                actor=actor,
                user_id=user_id,
                request_id=request_id,
                model=model,
                record_id=record_id,
                operation=operation,
                diff=safe_diff,
                metadata=safe_meta,
            )
        )
        if autocommit:
            await session.commit()
    except Exception:  # noqa: BLE001
        logger.exception(
            "audit.write_failed model=%s op=%s actor=%s", model, operation, actor,
        )
        if autocommit:
            try:
                await session.rollback()
            except Exception:  # noqa: BLE001
                pass
