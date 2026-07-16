"""Environment configuration."""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    agent_api_secret: str = ""

    jsearch_rapidapi_key: str = ""
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""

    claude_sonnet_model: str = "claude-sonnet-4-20250514"
    claude_haiku_model: str = "claude-haiku-4-5-20251001"

    scraper_delay_seconds: float = 3.0
    max_jobs_per_source: int = 25

    @model_validator(mode="after")
    def default_supabase_url(self) -> "Settings":
        import os

        if not self.supabase_url:
            self.supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
        return self


settings = Settings()
