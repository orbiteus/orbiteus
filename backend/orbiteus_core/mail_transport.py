"""Low-level SMTP connect / send helpers."""
from __future__ import annotations

import logging
from email.message import EmailMessage

from orbiteus_core.mail_settings import SmtpConfig

logger = logging.getLogger("mail")


async def verify_smtp_connection(cfg: SmtpConfig) -> None:
    """Open SMTP, optionally STARTTLS + AUTH. Raises on failure."""
    import aiosmtplib

    smtp = aiosmtplib.SMTP(hostname=cfg.host, port=cfg.port, timeout=15.0)
    await smtp.connect()
    try:
        if cfg.use_tls:
            await smtp.starttls()
        if cfg.user:
            await smtp.login(cfg.user, cfg.password or "")
    finally:
        try:
            await smtp.quit()
        except Exception:  # noqa: BLE001
            pass


async def send_via_smtp(
    cfg: SmtpConfig,
    *,
    to: str,
    subject: str,
    body_text: str,
    body_html: str | None = None,
    from_address: str | None = None,
) -> None:
    import aiosmtplib

    sender = from_address or cfg.from_address
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body_text)
    if body_html:
        msg.add_alternative(body_html, subtype="html")

    await aiosmtplib.send(
        msg,
        hostname=cfg.host,
        port=cfg.port,
        username=cfg.user or None,
        password=cfg.password or None,
        start_tls=cfg.use_tls,
        timeout=15.0,
    )
    logger.info("mail.sent to=%s subject=%r host=%s", to, subject, cfg.host)
