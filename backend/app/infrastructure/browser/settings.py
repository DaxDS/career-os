from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class AutomationSettings(BaseSettings):
    """Layer 9 browser automation settings — isolated from Layer 0 config."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    browser_profiles_path: Path = Path("storage/browser_profiles")
    browser_screenshots_path: Path = Path("storage/browser_screenshots")
    browser_headless: bool = True
    browser_stop_before_submit: bool = False
    playwright_browser: str = "chromium"
    automation_enabled: bool = True
    job_bank_email: str = ""
    job_bank_password: str = ""


@lru_cache
def get_automation_settings() -> AutomationSettings:
    return AutomationSettings()


def resolve_automation_paths(settings: AutomationSettings, project_root: Path) -> AutomationSettings:
    if not settings.browser_profiles_path.is_absolute():
        settings.browser_profiles_path = project_root / settings.browser_profiles_path
    if not settings.browser_screenshots_path.is_absolute():
        settings.browser_screenshots_path = project_root / settings.browser_screenshots_path
    return settings
