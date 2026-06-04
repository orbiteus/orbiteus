"""HMAC-signed webhook delivery (Standard-Webhooks-style)."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select, update

logger = logging.getLogger(__name__)


def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


async def deliver_webhook_async(
    *,
    event: str,
    payload: dict[str, Any],
    webhook_id: str | None,
) -> None:
    """Look up the webhook subscriber, sign the payload, POST it.

    Raises on HTTP error so the outbox drainer can retry / dead-letter.
    """
    if not webhook_id:
        raise ValueError("webhook task requires target_ref=webhook_id")

    from modules.base.model.mapping import base_webhooks_table
    from orbiteus_core.db import AsyncSessionFactory

    async with AsyncSessionFactory() as session:
        row = (
            await session.execute(
                select(
                    base_webhooks_table.c.url,
                    base_webhooks_table.c.secret,
                    base_webhooks_table.c.is_active,
                    base_webhooks_table.c.active,
                    base_webhooks_table.c.auth_header_name,
                    base_webhooks_table.c.auth_header_value,
                ).where(base_webhooks_table.c.id == webhook_id)
            )
        ).first()

        if row is None:
            raise ValueError(f"webhook {webhook_id} not found")
        url, secret, is_active, active, auth_h_name, auth_h_value = row
        if not is_active or not active:
            logger.info("webhook.skip_inactive", extra={"webhook_id": webhook_id})
            return

        body = json.dumps({"event": event, "payload": payload}, default=str).encode("utf-8")
        signature = _sign(secret, body)
        headers = {
            "Content-Type": "application/json",
            "X-Orbiteus-Event": event,
            "X-Orbiteus-Signature": signature,
        }
        # Optional inbound-auth header (e.g. `Authorization: Bearer …`).
        # HMAC signing in `X-Orbiteus-Signature` remains unconditional —
        # this is *additional* auth for receivers that gate webhooks on
        # a header on top of HMAC verification.
        if auth_h_name and auth_h_value:
            headers[auth_h_name] = auth_h_value

        async with httpx.AsyncClient(timeout=15.0) as http:
            resp = await http.post(url, content=body, headers=headers)

        # Update last_delivery_* on the row (best effort).
        await session.execute(
            update(base_webhooks_table)
            .where(base_webhooks_table.c.id == webhook_id)
            .values(
                last_delivery_at=datetime.now(timezone.utc).isoformat(),
                last_delivery_status=str(resp.status_code),
            )
        )
        await session.commit()

        resp.raise_for_status()
