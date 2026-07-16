from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_CORS = (
    "http://localhost:3000,"
    "http://127.0.0.1:3000,"
    "http://localhost:1420,"
    "http://127.0.0.1:1420,"
    "tauri://localhost,"
    "https://tauri.localhost"
)


def _settings_env_files() -> tuple[str, ...]:
    """Load project-root .env (Docker) then backend/.env (local overrides)."""
    backend_dir = Path(__file__).resolve().parents[1]
    project_root = backend_dir.parent
    files: list[Path] = []
    root_env = project_root / ".env"
    backend_env = backend_dir / ".env"
    if root_env.is_file():
        files.append(root_env)
    if backend_env.is_file():
        files.append(backend_env)
    return tuple(str(path) for path in files) or (".env",)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_settings_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Career OS"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # Single-user system
    single_user_mode: bool = True
    default_user_email: str = "user@example.com"

    database_url: str = "postgresql://careeros:careeros@localhost:5432/careeros"
    redis_url: str = "redis://localhost:6379/0"

    secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    access_token_expire_minutes: int = 60 * 24 * 7
    default_user_password: str = "careeros-dev-password"

    storage_path: Path = Path("storage")
    prompts_path: Path = Path("prompts")

    log_level: str = "INFO"
    log_json: bool = False

    cors_origins: str = _DEFAULT_CORS

    # AI infrastructure (Layer 4)
    ai_enabled: bool = False
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro: str = ""
    stripe_price_team: str = ""
    stripe_checkout_success_url: str = "http://localhost:3000/app/plan"
    stripe_checkout_cancel_url: str = "http://localhost:3000/app/plan"

    @field_validator("environment")
    @classmethod
    def normalize_environment(cls, value: str) -> str:
        return value.strip().lower()

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return not self.is_production

    @property
    def dev_auth_bypass(self) -> bool:
        """Single-user local dev: API accepts requests without a bearer token."""
        return self.single_user_mode and self.is_development

    @property
    def resumes_path(self) -> Path:
        return self.storage_path / "resumes"

    @property
    def applications_path(self) -> Path:
        return self.storage_path / "applications"

    @property
    def templates_path(self) -> Path:
        return self.storage_path / "templates"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def resolve_paths(settings: Settings, project_root: Path) -> Settings:
    """Resolve relative paths for local development outside Docker."""
    if not settings.storage_path.is_absolute():
        settings.storage_path = project_root / "storage"
    if not settings.prompts_path.is_absolute():
        settings.prompts_path = project_root / "prompts"
    return settings
