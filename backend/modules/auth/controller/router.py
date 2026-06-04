"""Auth module router – login, refresh, logout, org picker, 2FA."""
from __future__ import annotations

import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from threading import Lock
from time import monotonic

import pyotp
from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from orbiteus_core.context import RequestContext
from orbiteus_core.config import settings
from orbiteus_core.db import get_session
from orbiteus_core.exceptions import NotFound
from orbiteus_core.security.cookies import (
    clear_auth_cookies,
    set_access_cookie,
    set_refresh_cookie,
)
from orbiteus_core.security.middleware import require_auth
from orbiteus_core.security.passwords import hash_password, verify_password
from orbiteus_core.security.tokens import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_password_reset_token,
    decode_refresh_token,
)
from orbiteus_core.user_agent import classify_login_device

router = APIRouter(tags=["auth"])
_RATE_LIMIT_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
_RATE_LIMIT_LOCK = Lock()


# ---------------------------------------------------------------------------
# Share-link endpoint (portal scope) — PR 12 / ADR-0007.
# ---------------------------------------------------------------------------

@router.post("/share")
async def issue_share_link(
    body: dict,
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Mint a portal-scoped JWT for a single resource.

    Body:
        {
          "resource_model": "crm.lead",
          "resource_id": "<uuid>",
          "permissions": ["read", "comment"],
          "ttl_days": 7
        }
    """
    from orbiteus_core import sharing

    if ctx.tenant_id is None or ctx.user_id is None:
        raise HTTPException(status_code=400, detail="tenant context required")

    try:
        token = sharing.issue(
            resource_model=str(body["resource_model"]),
            resource_id=uuid.UUID(str(body["resource_id"])),
            tenant_id=ctx.tenant_id,
            issued_by=ctx.user_id,
            permissions=list(body.get("permissions") or ["read"]),
            ttl_days=int(body.get("ttl_days") or 7),
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"token": token}


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


class RecoveryCodesResponse(BaseModel):
    codes: list[str]
    note: str = (
        "Store these one-time codes somewhere safe. They are shown ONCE; "
        "regenerate any time via POST /api/auth/2fa/recovery-codes."
    )


class PasswordResetRequestPayload(BaseModel):
    email: str


class PasswordResetConfirmPayload(BaseModel):
    token: str
    new_password: str


def _request_client_meta(request: Request) -> dict[str, str | None]:
    user_agent = request.headers.get("user-agent")
    client_host = request.client.host if request.client else None
    return {
        "ip": client_host,
        "user_agent": user_agent[:500] if user_agent else None,
        "device": classify_login_device(user_agent),
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Authenticate user and return JWT tokens."""
    _enforce_rate_limit(request, "login", limit=300, window_seconds=60)
    from modules.base.controller.repositories import UserRepository
    from orbiteus_core.audit import write_audit

    request_id = getattr(request.state, "request_id", None)
    client_meta = _request_client_meta(request)
    ip_meta = {k: v for k, v in client_meta.items() if v is not None}

    ctx = RequestContext(is_superadmin=True)
    repo = UserRepository(session, ctx)
    user = await repo.get_by_email(payload.email)

    if user is None or not verify_password(payload.password, user.password_hash):
        # Record the failed attempt before bouncing — `actor=user` is
        # the right label even when the user couldn't be identified
        # (the human submitting the form is still the actor).
        await write_audit(
            session,
            actor="user",
            operation="login_failed",
            model="auth.session",
            tenant_id=user.tenant_id if user else None,
            user_id=user.id if user else None,
            request_id=request_id,
            diff={"email": payload.email, "reason": "invalid_credentials"},
            metadata=ip_meta,
            autocommit=True,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        await write_audit(
            session,
            actor="user",
            operation="login_failed",
            model="auth.session",
            tenant_id=user.tenant_id,
            user_id=user.id,
            request_id=request_id,
            diff={"email": payload.email, "reason": "disabled"},
            metadata=ip_meta,
            autocommit=True,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account disabled")

    # TOTP check (incl. recovery codes — PR final).
    if user.totp_enabled:
        if not payload.totp_code:
            return TokenResponse(
                access_token="",
                refresh_token="",
                requires_totp=True,
            )

        # Recovery codes path: alphanumeric format, single-use.
        from orbiteus_core.security.recovery_codes import (
            normalize as _normalize_code,
            verify_and_consume as _verify_recovery,
        )

        normalized = _normalize_code(payload.totp_code)
        ok_recovery, remaining = _verify_recovery(normalized, list(user.recovery_codes_hashed or []))
        if ok_recovery:
            await repo.update(user.id, {"recovery_codes_hashed": remaining})
            await session.commit()
        else:
            totp = pyotp.TOTP(user.totp_secret)
            if not totp.verify(payload.totp_code):
                await write_audit(
                    session,
                    actor="user",
                    operation="login_failed",
                    model="auth.session",
                    tenant_id=user.tenant_id,
                    user_id=user.id,
                    request_id=request_id,
                    diff={"email": payload.email, "reason": "invalid_totp"},
                    metadata=ip_meta,
                    autocommit=True,
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid TOTP code",
                )

    # ── successful authentication ────────────────────────────────────────
    await repo.update(user.id, {
        "last_login": datetime.now(timezone.utc),
        "last_login_device": client_meta["device"],
    })

    await write_audit(
        session,
        actor="user",
        operation="login",
        model="auth.session",
        tenant_id=user.tenant_id,
        user_id=user.id,
        request_id=request_id,
        diff={"email": payload.email},
        metadata=ip_meta,
        autocommit=True,
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
        tokens = _issue_tokens(user, first_company, response)
        tokens.companies = companies
        return tokens

    company_id = company_ids[0] if company_ids else None
    return _issue_tokens(user, company_id, response)


@router.post("/select-company", response_model=TokenResponse)
async def select_company(
    payload: CompanySelectRequest,
    response: Response,
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

    return _issue_tokens(user, payload.company_id, response)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    payload: RefreshRequest | None = Body(default=None),
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """Issue new access token from refresh token (body OR `orbiteus_refresh` cookie)."""
    _enforce_rate_limit(request, "refresh", limit=600, window_seconds=60)

    refresh_token = ""
    if payload is not None and payload.refresh_token:
        refresh_token = payload.refresh_token
    if not refresh_token:
        refresh_token = request.cookies.get("orbiteus_refresh", "")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token")

    try:
        data = decode_refresh_token(refresh_token)
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

    # Rotation: revoke the consumed refresh `jti` so it cannot be replayed.
    old_jti = data.get("jti")
    if old_jti:
        try:
            from orbiteus_core.security.jti import revoke as _revoke_jti

            await _revoke_jti(old_jti, data.get("exp", 0))
        except Exception:
            # Redis outage must not block the refresh; logged elsewhere.
            pass

    return _issue_tokens(user, company_id, response)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Revoke the current `jti`, clear auth cookies, return ok."""
    clear_auth_cookies(response)

    # Best-effort: revoke the access token's jti via Redis. We re-decode the
    # bearer to read jti+exp; cookie path goes the same way.
    auth_header = request.headers.get("authorization") or ""
    raw = ""
    if auth_header.lower().startswith("bearer "):
        raw = auth_header.split(" ", 1)[1].strip()
    if not raw:
        raw = request.cookies.get("orbiteus_token", "")

    if raw:
        try:
            from orbiteus_core.security.jti import revoke as _revoke_jti
            from orbiteus_core.security.tokens import decode_access_token

            payload = decode_access_token(raw)
            if payload.get("jti"):
                await _revoke_jti(payload["jti"], payload.get("exp", 0))
        except Exception:
            pass

    return {"status": "ok"}


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
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
            "role_ids": ["base.group_user"],
            "is_superadmin": False,
        })
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    client_meta = _request_client_meta(request)
    await user_repo.update(user.id, {
        "last_login": datetime.now(timezone.utc),
        "last_login_device": client_meta["device"],
    })
    await session.commit()

    return _issue_tokens(user, company.id, response)


@router.get("/me")
async def me(
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> dict:
    """Return current user profile with live RBAC version for permission refresh."""
    from modules.base.controller.repositories import UserRepository
    from modules.base.model.schemas import UserRead
    from orbiteus_core.security import rbac

    repo = UserRepository(session, RequestContext(is_superadmin=True))
    try:
        user = await repo.get(ctx.user_id)
    except NotFound:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session invalid — please sign in again",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    body = UserRead.model_validate(user, from_attributes=True).model_dump()
    body["rbac_version"] = rbac.get_rbac_version()
    body["roles"] = user.role_ids or ctx.roles
    return body


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
# Password reset (DoD §3.4)
# ---------------------------------------------------------------------------
#
# Two endpoints, both rate-limited and intentionally non-revealing:
#
#   POST /api/auth/password/request   { email }
#       Always returns 200 (prevents user enumeration). When the email
#       matches an existing user we mint a `password_reset` JWT (TTL =
#       `settings.password_reset_ttl_minutes`) and call
#       `mail.send_mail(...)` with the reset URL. Per-email throttle
#       (`settings.password_reset_request_window_seconds`) prevents
#       mailbox flood.
#
#   POST /api/auth/password/reset     { token, new_password }
#       Validates the JWT, refuses tokens already consumed (single-use:
#       the `jti` is moved to the Redis revocation list as soon as the
#       password is rotated), then writes the new bcrypt hash and
#       returns 204.
#
# Login events / failed attempts are NOT audited here — that's task 1.3.

@router.post("/password/request", status_code=status.HTTP_200_OK)
async def password_reset_request(
    payload: PasswordResetRequestPayload,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Always-200 password-reset request — see module docstring.

    The 200 status is the same whether or not the email exists; the
    only side-effect a caller can observe is whether the email lands in
    their inbox. This is the canonical defence against user enumeration.
    """
    _enforce_rate_limit(request, "password_request_ip", limit=20, window_seconds=60)

    email = (payload.email or "").strip().lower()
    if not email:
        return {"status": "ok"}

    # Per-email throttle — one mail per `password_reset_request_window_seconds`.
    try:
        from orbiteus_core.cache import get_redis

        client = get_redis()
        gate_key = f"pwreset:throttle:{email}"
        was_set = await client.set(
            gate_key,
            "1",
            ex=settings.password_reset_request_window_seconds,
            nx=True,
        )
        if not was_set:
            # We've already accepted a request for this address very
            # recently; pretend nothing happened (still 200, no extra
            # mail).
            return {"status": "ok"}
    except Exception:  # noqa: BLE001
        # Redis outage MUST NOT brick password reset. Continue without
        # the throttle — the IP-level limit above is the fallback.
        pass

    from modules.base.controller.repositories import UserRepository
    from orbiteus_core.mail import send_mail

    superctx = RequestContext(is_superadmin=True)
    repo = UserRepository(session, superctx)
    user = await repo.get_by_email(email)

    if user is None or not user.is_active:
        # Same-shape response prevents enumeration via response timing /
        # status. We still log so an operator can spot probing.
        import logging
        logging.getLogger(__name__).info(
            "auth.password_reset.request_unknown_email email=%s", email,
        )
        return {"status": "ok"}

    token = create_password_reset_token(user.id)
    reset_url = f"{settings.frontend_base_url.rstrip('/')}/reset/{token}"
    body_text = (
        f"Hi {user.name or user.email},\n\n"
        f"Use the link below to reset your Orbiteus password. "
        f"It expires in {settings.password_reset_ttl_minutes} minutes "
        f"and can be used only once.\n\n"
        f"{reset_url}\n\n"
        f"If you did not request this, please ignore this email."
    )
    await send_mail(
        to=user.email,
        subject="Reset your Orbiteus password",
        body_text=body_text,
        session=session,
    )

    from orbiteus_core.audit import write_audit

    request_id = getattr(request.state, "request_id", None)
    client_host = request.client.host if request.client else None
    await write_audit(
        session,
        actor="user",
        operation="password_reset_requested",
        model="auth.session",
        tenant_id=user.tenant_id,
        user_id=user.id,
        request_id=request_id,
        diff={"email": user.email},
        metadata={"ip": client_host} if client_host else {},
        autocommit=True,
    )
    return {"status": "ok"}


@router.post("/password/reset", status_code=status.HTTP_200_OK)
async def password_reset_confirm(
    payload: PasswordResetConfirmPayload,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Consume a `password_reset` JWT and rotate the user's password."""
    _enforce_rate_limit(request, "password_reset_ip", limit=30, window_seconds=60)

    if not payload.new_password or len(payload.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters",
        )

    try:
        data = decode_password_reset_token(payload.token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired reset token",
        )

    jti = data.get("jti")
    if not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing jti",
        )

    # Single-use guard: refuse if already consumed.
    try:
        from orbiteus_core.security.jti import is_revoked

        if await is_revoked(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token already used",
            )
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001
        # Open-fail mirrors RBAC: if Redis is dead, we still let the
        # user reset their password. The token itself has a 30-minute
        # TTL so the blast radius is bounded.
        pass

    user_id_str = data.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has malformed subject",
        )

    from modules.base.controller.repositories import UserRepository

    superctx = RequestContext(is_superadmin=True)
    repo = UserRepository(session, superctx)
    try:
        user = await repo.get(user_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account disabled",
        )

    new_hash = hash_password(payload.new_password)
    await repo.update(user.id, {"password_hash": new_hash})
    await session.commit()

    # Move the consumed token's `jti` to the revocation list so a second
    # attempt with the same link yields 401 "Token already used".
    try:
        from orbiteus_core.security.jti import revoke as _revoke_jti

        await _revoke_jti(jti, data.get("exp", 0))
    except Exception:  # noqa: BLE001
        pass

    from orbiteus_core.audit import write_audit

    request_id = getattr(request.state, "request_id", None)
    client_host = request.client.host if request.client else None
    await write_audit(
        session,
        actor="user",
        operation="password_reset_completed",
        model="auth.session",
        tenant_id=user.tenant_id,
        user_id=user.id,
        request_id=request_id,
        diff={"email": user.email},
        metadata={"ip": client_host} if client_host else {},
        autocommit=True,
    )

    return {"status": "ok"}


@router.post("/2fa/recovery-codes", response_model=RecoveryCodesResponse)
async def regenerate_recovery_codes(
    session: AsyncSession = Depends(get_session),
    ctx: RequestContext = Depends(require_auth),
) -> RecoveryCodesResponse:
    """(Re)generate single-use TOTP recovery codes for the current user.

    Replaces any existing codes. The plain values are shown ONCE in the
    response — the server stores only bcrypt hashes.
    """
    from modules.base.controller.repositories import UserRepository
    from orbiteus_core.security.recovery_codes import generate_codes

    repo = UserRepository(session, ctx)
    user = await repo.get(ctx.user_id)
    if not user.totp_enabled:
        raise HTTPException(status_code=400, detail="Enable TOTP first")

    plain, hashed = generate_codes()
    await repo.update(ctx.user_id, {"recovery_codes_hashed": hashed})
    await session.commit()
    return RecoveryCodesResponse(codes=plain)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _issue_tokens(user, company_id, response: Response | None = None) -> TokenResponse:
    """Mint access + refresh tokens.

    When called from an HTTP handler (Response provided), the same tokens are
    also written as httpOnly cookies (`orbiteus_token`, `orbiteus_refresh`).
    The body keeps the JWTs for backward-compatible API clients.
    """
    from orbiteus_core.security import rbac

    token_data = {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        "company_id": str(company_id) if company_id else None,
        "roles": user.role_ids or [],
        "is_superadmin": user.is_superadmin,
        "rbac_ver": rbac.get_rbac_version(),
    }
    access = create_access_token(token_data)
    refresh = create_refresh_token(token_data)

    if response is not None:
        set_access_cookie(response, access)
        set_refresh_cookie(response, refresh)

    return TokenResponse(access_token=access, refresh_token=refresh)


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
