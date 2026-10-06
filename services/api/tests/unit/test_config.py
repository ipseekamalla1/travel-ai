from typing import Any

import pytest

from app.core.config import Settings


def _settings(**values: Any) -> Settings:
    # Never read the developer's .env in tests.
    return Settings(_env_file=None, **values)


def test_plain_postgres_url_uses_asyncpg_driver() -> None:
    settings = _settings(database_url="postgresql://u:p@db:5432/atu")

    assert str(settings.database_url).startswith("postgresql+asyncpg://")


def test_cors_origins_accept_comma_separated_string() -> None:
    settings = _settings(cors_origins="http://a.test, http://b.test")

    assert settings.cors_origins == ["http://a.test", "http://b.test"]


@pytest.mark.parametrize("secret", ["dev-only-insecure-secret-change-me", "", "short"])
def test_production_rejects_weak_secret(secret: str) -> None:
    settings = _settings(app_env="production", providers_mode="real", auth_secret=secret)

    with pytest.raises(RuntimeError, match="AUTH_SECRET"):
        settings.assert_safe_for_production()


def test_production_rejects_fake_providers() -> None:
    settings = _settings(app_env="production", auth_secret="a" * 64, providers_mode="fake")

    with pytest.raises(RuntimeError, match="PROVIDERS_MODE"):
        settings.assert_safe_for_production()


def test_production_accepts_strong_configuration() -> None:
    settings = _settings(app_env="production", auth_secret="a" * 64, providers_mode="real")

    settings.assert_safe_for_production()
