from pathlib import Path
from typing import Any

import yaml

from app.application.ports.browser_automation import (
    AutomationContext,
    BrowserConnectorPort,
    ConnectorStepResult,
)
from app.infrastructure.browser.captcha_detector import detect_captcha
from app.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)


class ConfigDrivenBrowserConnector(BrowserConnectorPort):
    """Connector driven by YAML config — no site URLs in business logic."""

    def __init__(self, connector_key: str, config: dict[str, Any]):
        self._connector_key = connector_key
        self._config = config

    @property
    def connector_key(self) -> str:
        return self._connector_key

    async def open_application_page(self, page: Any, context: AutomationContext) -> ConnectorStepResult:
        url = context.application_url
        if not url:
            return ConnectorStepResult(success=False, message="No application URL available")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        if await detect_captcha(page, self._config):
            return ConnectorStepResult(success=False, paused_for_captcha=True, message="CAPTCHA detected")
        try:
            body_text = (await page.inner_text("body")).lower()
        except Exception:
            body_text = ""
        if "system maintenance" in body_text or "interruption des services" in body_text:
            return ConnectorStepResult(
                success=False,
                message=(
                    "Job Bank is down for nightly maintenance (12:00 a.m.–7:00 a.m. Eastern). "
                    "Try again after 7:00 a.m. ET or apply manually on the employer site."
                ),
            )
        return ConnectorStepResult(success=True, message=f"Opened {url}")

    async def navigate_application_flow(self, page: Any, context: AutomationContext) -> ConnectorStepResult:
        if await detect_captcha(page, self._config):
            return ConnectorStepResult(success=False, paused_for_captcha=True, message="CAPTCHA detected")
        apply_selector = self._config.get("selectors", {}).get("apply_button")
        if apply_selector:
            locator = page.locator(apply_selector).first
            if await locator.count() > 0:
                await locator.click()
                if hasattr(page, "wait_for_load_state"):
                    await page.wait_for_load_state("domcontentloaded", timeout=60000)
                if await detect_captcha(page, self._config):
                    return ConnectorStepResult(
                        success=False, paused_for_captcha=True, message="CAPTCHA after apply navigation"
                    )
                return ConnectorStepResult(success=True, message="Clicked apply entry point")
        return ConnectorStepResult(success=True, message="Navigation complete")

    async def upload_resume(self, page: Any, context: AutomationContext) -> ConnectorStepResult:
        return await self._upload_file(
            page, context, context.resume_file, "resume_upload", "Resume"
        )

    async def upload_cover_letter(self, page: Any, context: AutomationContext) -> ConnectorStepResult:
        return await self._upload_file(
            page, context, context.cover_letter_file, "cover_letter_upload", "Cover letter"
        )

    async def fill_recruiter_email(self, page: Any, context: AutomationContext) -> ConnectorStepResult:
        if not context.email_body:
            return ConnectorStepResult(success=True, message="No email body to fill")
        selector = self._config.get("selectors", {}).get("email_field")
        if not selector:
            return ConnectorStepResult(success=True, message="No email field configured")
        locator = page.locator(selector).first
        if await locator.count() == 0:
            return ConnectorStepResult(success=True, message="Email field not found on page")
        await locator.fill(context.email_body)
        return ConnectorStepResult(success=True, message="Email field filled")

    async def fill_standard_fields(self, page: Any, context: AutomationContext) -> ConnectorStepResult:
        fields = self._config.get("selectors", {}).get("text_fields", {})
        filled: list[str] = []
        for field_key, selector in fields.items():
            value = context.profile_fields.get(field_key, "")
            if not value:
                continue
            locator = page.locator(selector).first
            if await locator.count() > 0:
                await locator.fill(value)
                filled.append(field_key)
        return ConnectorStepResult(success=True, message=f"Filled fields: {filled}")

    async def detect_validation_errors(self, page: Any, context: AutomationContext) -> list[str]:
        selector = self._config.get("selectors", {}).get("validation_error")
        if not selector:
            return []
        errors: list[str] = []
        locator = page.locator(selector)
        count = await locator.count()
        for i in range(min(count, 10)):
            text = (await locator.nth(i).inner_text()).strip()
            if text:
                errors.append(text)
        return errors

    async def submit_application(self, page: Any, context: AutomationContext) -> ConnectorStepResult:
        if context.stop_before_submit:
            return ConnectorStepResult(
                success=True,
                message="Stopped before final submission as configured",
            )
        selector = self._config.get("selectors", {}).get("submit_button")
        if not selector:
            return ConnectorStepResult(success=False, message="Submit button not configured")
        locator = page.locator(selector).first
        if await locator.count() == 0:
            return ConnectorStepResult(success=False, message="Submit button not found")
        await locator.click()
        return ConnectorStepResult(success=True, message="Application submitted")

    async def detect_captcha(self, page: Any, context: AutomationContext) -> bool:
        return await detect_captcha(page, self._config)

    async def _upload_file(
        self,
        page: Any,
        context: AutomationContext,
        file_path: Path | None,
        selector_key: str,
        label: str,
    ) -> ConnectorStepResult:
        if not file_path or not file_path.exists():
            return ConnectorStepResult(success=True, message=f"No {label} file to upload")
        selector = self._config.get("selectors", {}).get(selector_key)
        if not selector:
            return ConnectorStepResult(success=True, message=f"No {label} upload selector configured")
        locator = page.locator(selector).first
        if await locator.count() == 0:
            return ConnectorStepResult(success=False, message=f"{label} upload field not found")
        await locator.set_input_files(str(file_path))
        return ConnectorStepResult(success=True, message=f"{label} uploaded")


def load_connector_config(connector_key: str) -> dict[str, Any]:
    config_path = Path(__file__).resolve().parent.parent / "configs" / f"{connector_key}.yaml"
    if not config_path.exists():
        raise ValueError(f"No browser connector config for: {connector_key}")
    with config_path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)
