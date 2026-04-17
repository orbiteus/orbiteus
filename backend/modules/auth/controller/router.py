"""Auth module router – login, refresh, logout, org picker, 2FA."""
from __future__ import annotations

import uuid
from collections import defaultdict, deque
from threading import Lock
from time import monotonic

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext
from orbiteus_core.config import settings
from orbiteus_core.db import get_session
from orbiteus_core.security.middleware import require_auth
from orbiteus_core.security.passwords import hash_password, verify_password
from orbiteus_core.security.tokens import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)

router = APIRouter(tags=["auth"])
_RATE_LIMIT_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
_RATE_LIMIT_LOCK = Lock()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: str
    password: str
    totp_code: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    requires_totp: bool = False
    requires_company_selection: bool = False
    companies: list[dict] | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class CompanySelectRequest(BaseModel):
    company_id: uuid.UUID


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    tenant_name: str
    tenant_slug: str


class TOTPSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str


class TOTPVerifyRequest(BaseModel):
    code: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Authenticate user and return JWT tokens."""
    _enforce_rate_limit(request, "login", limit=300, window_seconds=60)
    from modules.base.controller.repositories import UserRepository

    ctx = RequestContext(is_superadmin=True)
    repo = UserRepository(session, ctx)
    user = await repo.get_by_email(payload.email)

    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account disabled")

    # TOTP check
    if user.totp_enabled:
        if not payload.totp_code:
            return TokenResponse(
                access_token="",
                refresh_token="",
                requires_totp=True,
            )
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(payload.totp_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid TOTP code",
            )

    # For now, issue a token with the first available company to avoid
    # blocking users when the frontend has no dedicated company picker yet.
    company_ids = user.company_ids or []
    if len(company_ids) > 1:
        from modules.base.controller.repositories import CompanyRepository
        company_ctx = RequestContext(tenant_id=user.tenant_id, is_superadmin=True)
        company_repo = CompanyRepository(session, company_ctx)
        companies = []
        for cid in company_ids:
            try:
                c = await company_repo.get(cid)
                companies.append({"id": str(c.id), "name": c.name})
            except Exception:
                pass
        first_company = company_ids[0]
        tokens = _issue_tokens(user, first_company)
        tokens.companies = companies
        return tokens

    company_id = company_ids[0] if company_ids else None
    return _issue_tokens(user, company_id)


@router.post("/select-company", response_model=TokenResponse)
async def select_company(
    payload: CompanySelectRequest,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> TokenResponse:
    """Issue tokens after user selects a company (org picker step)."""
    from modules.base.controller.repositories import UserRepository

    superctx = RequestContext(is_superadmin=True)
    repo = UserRepository(session, superctx)
    user = await repo.get(ctx.user_id)

    if str(payload.company_id) not in [str(c) for c in (user.company_ids or [])]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Company not accessible")

    return _issue_tokens(user, payload.company_id)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Issue new access token from refresh token."""
    _enforce_rate_limit(request, "refresh", limit=600, window_seconds=60)
    try:
        data = decode_refresh_token(payload.refresh_token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    from modules.base.controller.repositories import UserRepository
    ctx = RequestContext(is_superadmin=True)
    repo = UserRepository(session, ctx)
    user = await repo.get(uuid.UUID(data["sub"]))

    company_id = uuid.UUID(data["company_id"]) if data.get("company_id") else None
    return _issue_tokens(user, company_id)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Self-service registration – creates tenant + first user (owner)."""
    if not settings.allow_public_registration:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Public registration is disabled",
        )
    _enforce_rate_limit(request, "register", limit=300, window_seconds=60)
    from sqlalchemy.exc import IntegrityError

    from modules.base.controller.repositories import (
        CompanyRepository,
        TenantRepository,
        UserRepository,
    )

    superctx = RequestContext(is_superadmin=True)

    # Check for duplicate email upfront to return a clean 409
    user_check_repo = UserRepository(session, superctx)
    existing = await user_check_repo.get_by_email(payload.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    tenant_repo = TenantRepository(session, superctx)
    tenant = await tenant_repo.create({
        "name": payload.tenant_name,
        "slug": payload.tenant_slug,
        "plan": "free",
    })

    company_repo_ctx = RequestContext(tenant_id=tenant.id, is_superadmin=True)
    company_repo = CompanyRepository(session, company_repo_ctx)
    company = await company_repo.create({"name": payload.tenant_name})

    user_repo = UserRepository(session, RequestContext(tenant_id=tenant.id, is_superadmin=True))
    try:
        user = await user_repo.create({
            "email": payload.email,
            "name": payload.name,
            "password_hash": hash_password(payload.password),
            "tenant_id": tenant.id,
            "company_id": company.id,
            "company_ids": [str(company.id)],
            "role_ids": ["base.group_user", "crm.group_crm_manager"],
            "is_superadmin": False,
        })
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    return _issue_tokens(user, company.id)


@router.get("/me")
async def me(
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Return current user profile."""
    from modules.base.controller.repositories import UserRepository
    from modules.base.model.schemas import UserRead

    repo = UserRepository(session, RequestContext(is_superadmin=True))
    user = await repo.get(ctx.user_id)
    return UserRead.model_validate(user, from_attributes=True).model_dump()


@router.post("/totp/setup", response_model=TOTPSetupResponse)
async def setup_totp(
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> TOTPSetupResponse:
    """Generate TOTP secret and provisioning URI for authenticator app."""
    from modules.base.controller.repositories import UserRepository

    repo = UserRepository(session, ctx)
    user = await repo.get(ctx.user_id)

    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=user.email, issuer_name="Orbiteus")

    await repo.update(ctx.user_id, {"totp_secret": secret})

    return TOTPSetupResponse(secret=secret, provisioning_uri=uri)


@router.post("/totp/verify")
async def verify_totp(
    payload: TOTPVerifyRequest,
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Confirm TOTP code and enable 2FA for the user."""
    from modules.base.controller.repositories import UserRepository

    repo = UserRepository(session, ctx)
    user = await repo.get(ctx.user_id)

    if not user.totp_secret:
        raise HTTPException(status_code=400, detail="TOTP not set up")

    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(payload.code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")

    await repo.update(ctx.user_id, {"totp_enabled": True})
    return {"message": "2FA enabled successfully"}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _issue_tokens(user, company_id) -> TokenResponse:
    token_data = {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        "company_id": str(company_id) if company_id else None,
        "roles": user.role_ids or [],
        "is_superadmin": user.is_superadmin,
    }
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


def _enforce_rate_limit(request: Request, action: str, limit: int, window_seconds: int) -> None:
    client = request.client.host if request.client else "unknown"
    key = f"{action}:{client}"
    now = monotonic()
    threshold = now - window_seconds

    with _RATE_LIMIT_LOCK:
        bucket = _RATE_LIMIT_BUCKETS[key]
        while bucket and bucket[0] < threshold:
            bucket.popleft()
        if len(bucket) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests, please retry later",
            )
        bucket.append(now)
