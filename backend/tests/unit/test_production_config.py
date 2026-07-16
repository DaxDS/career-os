import pytest

from app.config import Settings
from app.infrastructure.config.production import validate_production_settings


def test_production_rejects_default_secret():
    settings = Settings(environment="production", secret_key="change-me-in-production-use-openssl-rand-hex-32")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validate_production_settings(settings)


def test_production_rejects_default_password():
    settings = Settings(
        environment="production",
        secret_key="a" * 40,
        default_user_password="careeros-dev-password",
    )
    with pytest.raises(RuntimeError, match="DEFAULT_USER_PASSWORD"):
        validate_production_settings(settings)


def test_development_allows_defaults():
    settings = Settings(environment="development")
    validate_production_settings(settings)


def test_cors_origins_parsed():
    settings = Settings(cors_origins="http://a.test, http://b.test")
    assert settings.cors_origin_list == ["http://a.test", "http://b.test"]
