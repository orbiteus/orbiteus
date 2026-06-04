"""Instance-wide SMTP settings stored in ``base_config_params``.

Admin UI persists operator overrides here; environment variables remain the
bootstrap fallback until an operator saves settings in Connectivity → Mail.
"""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.config import settings
from orbiteus_core.context import RequestContext

logger = logging.getLogger(__name__)

CONFIGURED_KEY = "mail.smtp.configured"
HOST_KEY = "mail.smtp.host"
PORT_KEY = "mail.smtp.port"
USER_KEY = "mail.smtp.user"
PASSWORD_KEY = "mail.smtp.password"
USE_TLS_KEY = "mail.smtp.use_tls"
FROM_KEY = "mail.smtp.from_address"

_ALL_KEYS = (
    CONFIGURED_KEY,
    HOST_KEY,
    PORT_KEY,
    USER_KEY,
    PASSWORD_KEY,
    USE_TLS_KEY,
    FROM_KEY,
)


@dataclass(frozen=True)
class SmtpConfig:
    host: str
    port: int
    user: str
    password: str
    use_tls: bool
    from_address: str
    source: Literal["environment", "database"]


def _encrypt_password(plain: str) -> str:
    try:
        from orbiteus_core.ai.keys import encrypt

        return "fernet:" + encrypt(plain).decode("ascii")
    except RuntimeError:
        if settings.environment.lower() == "production":
            raise
        return "dev:" + base64.b64encode(plain.encode("utf-8")).decode("ascii")


def _decrypt_password(stored: str) -> str:
    if stored.startswith("fernet:"):
        from orbiteus_core.ai.keys import decrypt

        return decrypt(stored[7:].encode("ascii"))
    if stored.startswith("dev:"):
        if settings.environment.lower() == "production":
            raise RuntimeError("Dev-only SMTP password encoding is not allowed in production")
        return base64.b64decode(stored[4:].encode("ascii")).decode("utf-8")
    raise RuntimeError("Unknown SMTP password encoding")


def smtp_config_from_env() -> SmtpConfig | None:
    if not settings.smtp_host:
        return None
    return SmtpConfig(
        host=settings.smtp_host,
        port=settings.smtp_port,
        user=settings.smtp_user,
        password=settings.smtp_password,
        use_tls=settings.smtp_use_tls,
        from_address=settings.smtp_from_address,
        source="environment",
    )


async def _load_param_map(session: AsyncSession) -> dict[str, str]:
    from modules.base.controller.repositories import ConfigParamRepository

    repo = ConfigParamRepository(session, RequestContext(is_superadmin=True))
    out: dict[str, str] = {}
    for key in _ALL_KEYS:
        rows, _ = await repo.search(domain=[("key", "=", key)], limit=1)
        if rows and rows[0].value is not None:
            out[key] = str(rows[0].value)
    return out


async def resolve_smtp_config(session: AsyncSession | None) -> SmtpConfig | None:
    """Effective SMTP config: database override when configured, else env."""
    if session is not None:
        params = await _load_param_map(session)
        if params.get(CONFIGURED_KEY, "").lower() in {"1", "true", "yes", "on"}:
            host = params.get(HOST_KEY, "").strip()
            if not host:
                return None
            password = ""
            raw_pw = params.get(PASSWORD_KEY, "")
            if raw_pw:
                try:
                    password = _decrypt_password(raw_pw)
                except Exception:
                    logger.exception("mail_settings.password_decrypt_failed")
                    return None
            try:
                port = int(params.get(PORT_KEY, "587"))
            except ValueError:
                port = 587
            use_tls = params.get(USE_TLS_KEY, "true").lower() in {"1", "true", "yes", "on"}
            return SmtpConfig(
                host=host,
                port=port,
                user=params.get(USER_KEY, ""),
                password=password,
                use_tls=use_tls,
                from_address=params.get(FROM_KEY, settings.smtp_from_address),
                source="database",
            )

    return smtp_config_from_env()


async def get_mail_settings_public(session: AsyncSession) -> dict[str, Any]:
    """Settings payload for GET — never includes the password."""
    params = await _load_param_map(session)
    configured = params.get(CONFIGURED_KEY, "").lower() in {"1", "true", "yes", "on"}

    if configured:
        return {
            "source": "database",
            "configured": True,
            "host": params.get(HOST_KEY, ""),
            "port": int(params.get(PORT_KEY, "587") or 587),
            "user": params.get(USER_KEY, ""),
            "use_tls": params.get(USE_TLS_KEY, "true").lower() in {"1", "true", "yes", "on"},
            "from_address": params.get(FROM_KEY, settings.smtp_from_address),
            "has_password": bool(params.get(PASSWORD_KEY)),
        }

    env = smtp_config_from_env()
    if env:
        return {
            "source": "environment",
            "configured": False,
            "host": env.host,
            "port": env.port,
            "user": env.user,
            "use_tls": env.use_tls,
            "from_address": env.from_address,
            "has_password": bool(env.password),
        }

    return {
        "source": "environment",
        "configured": False,
        "host": "",
        "port": settings.smtp_port,
        "user": "",
        "use_tls": settings.smtp_use_tls,
        "from_address": settings.smtp_from_address,
        "has_password": False,
    }


async def _upsert_param(
    session: AsyncSession,
    ctx: RequestContext,
    key: str,
    value: str,
    description: str,
) -> None:
    from modules.base.controller.repositories import ConfigParamRepository

    repo = ConfigParamRepository(session, ctx)
    existing, _ = await repo.search(domain=[("key", "=", key)], limit=1)
    if existing:
        await repo.update(existing[0].id, {"value": value})
    else:
        await repo.create({"key": key, "value": value, "description": description})


async def save_mail_settings(
    session: AsyncSession,
    ctx: RequestContext,
    *,
    host: str,
    port: int,
    user: str,
    password: str | None,
    use_tls: bool,
    from_address: str,
) -> dict[str, Any]:
    host = host.strip()
    if not host:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="SMTP host is required")

    params = await _load_param_map(session)
    existing_pw = params.get(PASSWORD_KEY, "")

    if password is not None and password.strip():
        stored_pw = _encrypt_password(password.strip())
    elif existing_pw:
        stored_pw = existing_pw
    else:
        stored_pw = ""

    await _upsert_param(session, ctx, CONFIGURED_KEY, "true", "Mail: SMTP configured via admin UI")
    await _upsert_param(session, ctx, HOST_KEY, host, "Mail: SMTP host")
    await _upsert_param(session, ctx, PORT_KEY, str(port), "Mail: SMTP port")
    await _upsert_param(session, ctx, USER_KEY, user.strip(), "Mail: SMTP username")
    await _upsert_param(session, ctx, PASSWORD_KEY, stored_pw, "Mail: SMTP password (encrypted at rest)")
    await _upsert_param(session, ctx, USE_TLS_KEY, "true" if use_tls else "false", "Mail: SMTP STARTTLS")
    await _upsert_param(session, ctx, FROM_KEY, from_address.strip(), "Mail: default From address")
    await session.commit()
    return await get_mail_settings_public(session)


def smtp_config_from_payload(
    *,
    host: str,
    port: int,
    user: str,
    password: str,
    use_tls: bool,
    from_address: str,
) -> SmtpConfig:
    return SmtpConfig(
        host=host.strip(),
        port=port,
        user=user.strip(),
        password=password,
        use_tls=use_tls,
        from_address=from_address.strip() or settings.smtp_from_address,
        source="database",
    )


async def resolve_smtp_for_test(
    session: AsyncSession,
    *,
    host: str | None = None,
    port: int | None = None,
    user: str | None = None,
    password: str | None = None,
    use_tls: bool | None = None,
    from_address: str | None = None,
) -> SmtpConfig:
    """Build SMTP config for test endpoints — request overrides saved settings."""
    saved = await resolve_smtp_config(session)
    base = saved or smtp_config_from_env()

    if host is not None:
        eff_host = host.strip()
    else:
        eff_host = (base.host if base else "").strip()
    if not eff_host:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="SMTP host is required")

    eff_port = port if port is not None else (base.port if base else settings.smtp_port)
    eff_user = user if user is not None else (base.user if base else "")
    eff_tls = use_tls if use_tls is not None else (base.use_tls if base else settings.smtp_use_tls)
    eff_from = (from_address or (base.from_address if base else settings.smtp_from_address)).strip()

    eff_password = password if password is not None else ""
    if not eff_password and base:
        eff_password = base.password
    if not eff_password and saved is None and base and base.source == "environment":
        eff_password = base.password

    return smtp_config_from_payload(
        host=eff_host,
        port=eff_port,
        user=eff_user,
        password=eff_password,
        use_tls=eff_tls,
        from_address=eff_from,
    )
