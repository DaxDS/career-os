"""Production settings validation."""

from app.config import Settings

_INSECURE_SECRET_MARKERS = ("change-me-in-production", "change-me")
_DEV_DEFAULT_PASSWORD = "careeros-dev-password"


def validate_production_settings(settings: Settings) -> None:
    if settings.environment.lower() != "production":
        return

    if any(marker in settings.secret_key for marker in _INSECURE_SECRET_MARKERS):
        raise RuntimeError(
            "SECRET_KEY must be set to a secure random value when ENVIRONMENT=production"
        )
    if len(settings.secret_key) < 32:
        raise RuntimeError("SECRET_KEY must be at least 32 characters in production")

    if settings.default_user_password == _DEV_DEFAULT_PASSWORD:
        raise RuntimeError(
            "DEFAULT_USER_PASSWORD must be changed when ENVIRONMENT=production"
        )

    if not settings.cors_origins.strip():
        raise RuntimeError("CORS_ORIGINS must be set when ENVIRONMENT=production")
