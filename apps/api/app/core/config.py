"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Config — load monorepo root .env when running from apps/api
    _root_env = Path(__file__).resolve().parents[4] / ".env"
    model_config = SettingsConfigDict(
        env_file=(_root_env if _root_env.exists() else ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Unified Matter Intelligence Center"
    app_env: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    secret_key: str = Field(..., min_length=32)
    cors_origins: str = "http://localhost:3000"

    # Database
    database_url: str = Field(..., description="SQLAlchemy database URL")

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # JWT
    jwt_secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    password_hash_scheme: str = "bcrypt"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_v1_prefix: str = "/api/v1"
    rate_limit_login: str = "5/minute"
    rate_limit_default: str = "100/minute"

    # Seed admin
    seed_admin_email: str = "admin@example.com"
    seed_admin_password: str = "ChangeMeAdmin123!"
    seed_admin_first_name: str = "System"
    seed_admin_last_name: str = "Owner"

    # OAuth / integrations
    google_client_id: str = ""
    google_client_secret: str = ""
    google_api_key: str = ""
    google_gmail_api_key: str = ""
    google_redirect_uri: str = (
        "http://localhost:8000/api/v1/integrations/google/callback"
    )
    dropbox_app_key: str = ""
    dropbox_app_secret: str = ""
    dropbox_redirect_uri: str = (
        "http://localhost:8000/api/v1/integrations/dropbox/callback"
    )
    dropbox_access_token: str = ""

    @property
    def google_configured(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def dropbox_configured(self) -> bool:
        return bool(self.dropbox_access_token or (self.dropbox_app_key and self.dropbox_app_secret))

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, v: object) -> bool:
        if isinstance(v, str):
            return v.lower() in {"1", "true", "yes", "on"}
        return bool(v)


@lru_cache
def get_settings() -> Settings:
    return Settings()
