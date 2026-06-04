"""FastAPI security middleware – tenant resolution, JWT auth, company context.

Token resolution order:
  1. `Authorization: Bearer ...` header (machine clients, mobile apps).
  2. `orbiteus_token` httpOnly cookie (browser SSR; preferred for admin/portal UI).

See `docs/06-auth.md` and `docs/adr/0017-httponly-cookie-session.md`.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from orbiteus_core.context import RequestContext
from orbiteus_core.security.cookies import ACCESS_COOKIE
from orbiteus_core.security.tokens import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


async def _assert_active_user(user_id: uuid.UUID) -> None:
    """Reject tokens whose subject was deleted or deactivated (e.g. after DB reset)."""
    from sqlalchemy import select

    from orbiteus_core.db import AsyncSessionFactory
    from modules.base.model.mapping import users_table

    async with AsyncSessionFactory() as session:
        row = await session.execute(
            select(users_table.c.id).where(
                users_table.c.id == user_id,
                users_table.c.is_active == True,  # noqa: E712
                users_table.c.active == True,  # noqa: E712
            )
        )
        if row.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session invalid — please sign in again",
                headers={"WWW-Authenticate": "Bearer"},
            )


async def get_current_context(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> RequestContext:
    """FastAPI dependency – decode JWT and build RequestContext.

    Returns an unauthenticated context if no token is provided
    (public endpoints can allow it; protected ones should call
    require_auth() separately).
    """
    raw_token: str | None = None
    if credentials is not None and credentials.credentials:
        raw_token = credentials.credentials
    else:
        # Fallback: httpOnly cookie set by the auth router.
        raw_token = request.cookies.get(ACCESS_COOKIE) or None

    if raw_token is None:
        return RequestContext()

    try:
        payload = decode_access_token(raw_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # JWT revocation list (Redis); short-circuits compromised / logged-out tokens
    # before TTL.
    jti = payload.get("jti")
    if jti:
        try:
            from orbiteus_core.security.jti import is_revoked
            if await is_revoked(jti):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token revoked",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except HTTPException:
            raise
        except Exception:
            # Redis outage must not lock everyone out — log and proceed.
            import logging
            logging.getLogger(__name__).warning("jti revocation check failed (open-fail)")

    user_id = uuid.UUID(payload["sub"])
    roles = list(payload.get("roles", []))

    # Refresh role codes when RBAC matrix changed since token was minted.
    token_rbac_ver = int(payload.get("rbac_ver") or 0)
    from orbiteus_core.security import rbac

    if token_rbac_ver < rbac.get_rbac_version():
        from orbiteus_core.db import AsyncSessionFactory
        from orbiteus_core.role_resolver import resolve_role_codes

        async with AsyncSessionFactory() as session:
            roles = await resolve_role_codes(session, user_id)

    return RequestContext(
        user_id=user_id,
        tenant_id=uuid.UUID(payload["tenant_id"]) if payload.get("tenant_id") else None,
        company_id=uuid.UUID(payload["company_id"]) if payload.get("company_id") else None,
        roles=roles,
        is_superadmin=payload.get("is_superadmin", False),
        actor="user",
        scope=payload.get("scope", "internal"),
        request_id=request.headers.get("x-request-id"),
    )


async def require_auth(ctx: RequestContext = Depends(get_current_context)) -> RequestContext:
    """Dependency that enforces authentication."""
    if not ctx.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    await _assert_active_user(ctx.user_id)  # type: ignore[arg-type]
    return ctx


async def require_superadmin(ctx: RequestContext = Depends(require_auth)) -> RequestContext:
    """Dependency that enforces superadmin role."""
    if not ctx.is_superadmin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin required")
    return ctx
