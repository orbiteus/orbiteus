"""FastAPI security middleware – tenant resolution, JWT auth, company context."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from orbiteus_core.context import RequestContext
from orbiteus_core.security.tokens import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_context(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> RequestContext:
    """FastAPI dependency – decode JWT and build RequestContext.

    Returns an unauthenticated context if no token is provided
    (public endpoints can allow it; protected ones should call
    require_auth() separately).
    """
    if credentials is None:
        return RequestContext()

    try:
        payload = decode_access_token(credentials.credentials)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return RequestContext(
        user_id=uuid.UUID(payload["sub"]),
        tenant_id=uuid.UUID(payload["tenant_id"]) if payload.get("tenant_id") else None,
        company_id=uuid.UUID(payload["company_id"]) if payload.get("company_id") else None,
        roles=payload.get("roles", []),
        is_superadmin=payload.get("is_superadmin", False),
    )


async def require_auth(ctx: RequestContext = Depends(get_current_context)) -> RequestContext:
    """Dependency that enforces authentication."""
    if not ctx.is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return ctx


async def require_superadmin(ctx: RequestContext = Depends(require_auth)) -> RequestContext:
    """Dependency that enforces superadmin role."""
    if not ctx.is_superadmin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin required")
    return ctx
