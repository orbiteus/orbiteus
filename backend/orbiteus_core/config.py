"""Application configuration via environment variables."""
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://orbiteus:orbiteus@localhost:5432/orbiteus"

    # Auth
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15      # PR 6 — was 60; tighter blast radius
    refresh_token_expire_days: int = 7         # PR 6 — was 30; aligns with rotation
    refresh_token_rotate_on_use: bool = True

    # Redis (cache, jti revocation, rate limit, pubsub backplane).
    redis_url: str = "redis://localhost:6379/0"

    # Rate limit defaults (per minute). Override in production via env.
    # Interactive admin UI: authenticated GET/list/SSE traffic is not limited
    # (see rate_limit_middleware). These caps apply to mutations + anonymous IP.
    rate_limit_tenant_per_minute: int = 5000
    rate_limit_user_mutations_per_minute: int = 600
    rate_limit_user_per_minute: int = 120  # expensive authenticated GETs only
    rate_limit_ip_per_minute: int = 300
    rate_limit_anonymous_per_minute: int = 30

    # Password reset flow (DoD §3.4).
    password_reset_ttl_minutes: int = 30
    # Per-email throttle on `POST /api/auth/password/request` to prevent
    # mailbox flood. The endpoint always returns 200, so this is the
    # only line of defence.
    password_reset_request_window_seconds: int = 60
    # Public URL the password-reset email points users at. The frontend
    # serves the token-input page at `${frontend_base_url}/reset/<jwt>`.
    frontend_base_url: str = "http://localhost:3000"

    # SMTP / mailer (DoD §3.4 + §11.7 transactional mail).
    # When `smtp_host` is empty (default for dev) the mailer logs the
    # message to stdout instead of opening a TCP connection. This keeps
    # local + CI environments free of an external dependency while
    # still exercising the full code path.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_from_address: str = "no-reply@orbiteus.local"

    # Attachment filestore (local filesystem by default).
    attachment_storage: str = "local"
    attachment_storage_path: str = "./data/attachments"
    attachment_max_bytes: int = 52_428_800  # 50 MiB

    # Demo dataset (development only). See orbiteus_core/demo_seed.py.
    seed_demo_data: bool = False
    reset_demo_data: bool = False

    # AI provider key encryption (Fernet) — used in PR 8.
    ai_secret_key: str = "change-me-with-fernet-key"

    # App
    app_name: str = "Orbiteus"
    environment: str = "development"
    debug: bool = True
    cors_origins: list[str] = ["http://localhost:3000"]
    allow_public_registration: bool = True
    bootstrap_admin_email: str = "admin@example.com"
    bootstrap_admin_password: str = "admin1234"
    # Default tenant created on first startup; the bootstrap admin is bound
    # to this tenant so AI BYOK, audit attribution and multi-tenancy work
    # out of the box. Override in production to brand the default org.
    bootstrap_admin_tenant_name: str = "Orbiteus"
    bootstrap_admin_tenant_slug: str = "orbiteus"

    @model_validator(mode="after")
    def validate_production_safety(self) -> "Settings":
        if self.environment.lower() == "production":
            if self.secret_key in {"change-me-in-production", "change-me-in-production-use-openssl-rand-hex-32"}:
                raise ValueError("SECRET_KEY must be changed in production")
            if self.debug:
                raise ValueError("DEBUG must be false in production")
            if self.bootstrap_admin_password == "admin1234":
                raise ValueError("Set BOOTSTRAP_ADMIN_PASSWORD in production")
        return self


settings = Settings()
