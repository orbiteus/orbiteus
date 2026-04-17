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
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    # Temporal
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"

    # App
    app_name: str = "Orbiteus"
    environment: str = "development"
    debug: bool = True
    cors_origins: list[str] = ["http://localhost:3000"]
    allow_public_registration: bool = True
    bootstrap_admin_email: str = "admin@example.com"
    bootstrap_admin_password: str = "admin1234"

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
