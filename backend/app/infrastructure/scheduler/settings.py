from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class SchedulerSettings(BaseSettings):
    """Layer 10 scheduler settings — isolated from Layer 0 config."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    scheduler_enabled: bool = True
    scheduler_hour: int = 7
    scheduler_minute: int = 0
    scheduler_timezone: str = "America/Toronto"


@lru_cache
def get_scheduler_settings() -> SchedulerSettings:
    return SchedulerSettings()
