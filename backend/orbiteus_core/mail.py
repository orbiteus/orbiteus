"""Minimal transactional mailer (DoD §3.4 + §11.7).

Configuration resolution order:
  1. Admin UI settings in ``base_config_params`` (when ``mail.smtp.configured``)
  2. Environment variables (``SMTP_*`` / ``settings.smtp_*``)
  3. Dev log mode when no host is configured
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.config import settings
from orbiteus_core.mail_settings import SmtpConfig, resolve_smtp_config
from orbiteus_core.mail_transport import send_via_smtp

logger = logging.getLogger("mail")


async def send_mail(
    *,
    to: str,
    subject: str,
    body_text: str,
    body_html: str | None = None,
    from_address: str | None = None,
    session: AsyncSession | None = None,
    smtp: SmtpConfig | None = None,
    raise_on_error: bool = False,
) -> bool:
    """Send a transactional email.

    Returns ``True`` when a message was handed off to SMTP (or dev-logged).
    By default errors are logged, not raised — except when ``raise_on_error=True``
    (admin test endpoints).
    """
    cfg = smtp or await resolve_smtp_config(session)
    sender = from_address or (cfg.from_address if cfg else settings.smtp_from_address)

    if cfg is None or not cfg.host:
        logger.info(
            "mail.dev_log to=%s subject=%r body=%r",
            to, subject, body_text,
        )
        return True

    try:
        await send_via_smtp(
            cfg,
            to=to,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            from_address=sender,
        )
        return True
    except Exception:  # noqa: BLE001
        logger.exception("mail.send_failed to=%s subject=%r", to, subject)
        if raise_on_error:
            raise
        return False
