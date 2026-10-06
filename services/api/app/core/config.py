from enum import StrEnum
from functools import lru_cache
from typing import Annotated

from pydantic import Field, PostgresDsn, RedisDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

MIN_PRODUCTION_SECRET_LENGTH = 32


class AppEnv(StrEnum):
    LOCAL = "local"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class ProvidersMode(StrEnum):
    REAL = "real"
    FAKE = "fake"


class Settings(BaseSettings):
    """Application settings, loaded from environment variables (and `.env` in local dev)."""

    model_config = SettingsConfigDict(env_file=(".env", "../../.env"), extra="ignore")

    app_env: AppEnv = AppEnv.LOCAL
    log_level: str = "INFO"
    log_json: bool = True

    web_base_url: str = "http://localhost:3000"
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    database_url: PostgresDsn = PostgresDsn("postgresql+asyncpg://atu:atu@localhost:5432/atu")
    database_pool_size: int = 5
    database_echo: bool = False
    redis_url: RedisDsn = RedisDsn("redis://localhost:6379/0")

    auth_secret: SecretStr = SecretStr("dev-only-insecure-secret-change-me")

    providers_mode: ProvidersMode = ProvidersMode.FAKE

    readiness_timeout_s: float = 2.0

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def _force_asyncpg(cls, value: object) -> object:
        # Accept plain postgresql:// URLs (as most platforms provide) and use the asyncpg driver.
        if isinstance(value, str) and value.startswith(("postgresql://", "postgres://")):
            return "postgresql+asyncpg://" + value.split("://", 1)[1]
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env is AppEnv.PRODUCTION

    def assert_safe_for_production(self) -> None:
        if not self.is_production:
            return
        secret = self.auth_secret.get_secret_value()
        if secret.startswith("dev-only") or len(secret) < MIN_PRODUCTION_SECRET_LENGTH:
            raise RuntimeError(
                f"AUTH_SECRET must be set to a random value of at least "
                f"{MIN_PRODUCTION_SECRET_LENGTH} characters in production"
            )
        if self.providers_mode is not ProvidersMode.REAL:
            raise RuntimeError("PROVIDERS_MODE must be 'real' in production")


@lru_cache
def get_settings() -> Settings:
    return Settings()
