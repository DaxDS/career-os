"""Workday and Greenhouse ATS connectors — apply-flow navigation on top of the config-driven base.

Both reuse the base-class safety guarantees unchanged:
- CAPTCHA is detected and pauses the run (never bypassed).
- submit_application honours context.stop_before_submit before touching the page.
"""

from __future__ import annotations

from typing import Any

from app.application.ports.browser_automation import AutomationContext, ConnectorStepResult
from app.infrastructure.browser.captcha_detector import detect_captcha
from app.infrastructure.browser.connectors.base import (
    ConfigDrivenBrowserConnector,
    load_connector_config,
)
from app.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)


class _SplitNameMixin(ConfigDrivenBrowserConnector):
    """Workday and Greenhouse split legal name into first/last fields."""

    async def fill_standard_fields(self, page: Any, context: AutomationContext) -> ConnectorStepResult:
        result = await super().fill_standard_fields(page, context)
        filled = await self._fill_split_name(page, context)
        if filled:
            return ConnectorStepResult(
                success=True, message=f"{result.message} + name fields: {filled}"
            )
        return result

    async def _fill_split_name(self, page: Any, context: AutomationContext) -> list[str]:
        full_name = (context.profile_fields.get("name") or "").strip()
        if not full_name:
            return []
        parts = full_name.split()
        first, last = parts[0], " ".join(parts[1:]) if len(parts) > 1 else ""
        selectors = self._config.get("selectors", {})
        filled: list[str] = []
        for key, value in (("first_name_field", first), ("last_name_field", last)):
            selector = selectors.get(key)
            if not selector or not value:
                continue
            locator = page.locator(selector).first
            if await locator.count() > 0:
                await locator.fill(value)
                filled.append(key)
        return filled


class WorkdayBrowserConnector(_SplitNameMixin):
    """Workday-hosted postings (*.myworkdayjobs.com) — multi-step apply flow."""

    def __init__(self):
        super().__init__("workday", load_connector_config("workday"))

    async def navigate_application_flow(self, page: Any, context: AutomationContext) -> ConnectorStepResult:
        if await detect_captcha(page, self._config):
            return ConnectorStepResult(success=False, paused_for_captcha=True, message="CAPTCHA detected")

        selectors = self._config.get("selectors", {})

        apply_btn = page.locator(selectors.get("apply_button", "")).first
        if await apply_btn.count() > 0:
            await apply_btn.click()
            await self._wait_loaded(page)
            if await detect_captcha(page, self._config):
                return ConnectorStepResult(
                    success=False, paused_for_captcha=True, message="CAPTCHA after apply navigation"
                )

        # Prefer the manual path over "Autofill with Resume" so field mapping stays deterministic
        manual_btn = page.locator(selectors.get("apply_manually", "")).first
        if await manual_btn.count() > 0:
            await manual_btn.click()
            await self._wait_loaded(page)
            if await detect_captcha(page, self._config):
                return ConnectorStepResult(
                    success=False, paused_for_captcha=True, message="CAPTCHA on application form"
                )

        if await self._is_sign_in_wall(page):
            return ConnectorStepResult(
                success=False,
                message=(
                    "Workday requires a candidate account for this employer. "
                    "Create/sign in to the account in the browser session, then retry — "
                    "Career OS will not create accounts automatically."
                ),
            )

        return ConnectorStepResult(success=True, message="Workday application form opened")

    async def _is_sign_in_wall(self, page: Any) -> bool:
        selector = self._config.get("selectors", {}).get("sign_in_form", "")
        if selector and await page.locator(selector).count() > 0:
            return True
        try:
            body = (await page.inner_text("body")).lower()
        except Exception:
            return False
        return "sign in" in body and "password" in body

    @staticmethod
    async def _wait_loaded(page: Any) -> None:
        if hasattr(page, "wait_for_load_state"):
            await page.wait_for_load_state("domcontentloaded", timeout=60000)


class GreenhouseBrowserConnector(_SplitNameMixin):
    """Greenhouse-hosted boards (boards.greenhouse.io, job-boards.greenhouse.io)."""

    def __init__(self):
        super().__init__("greenhouse", load_connector_config("greenhouse"))

    async def navigate_application_flow(self, page: Any, context: AutomationContext) -> ConnectorStepResult:
        if await detect_captcha(page, self._config):
            return ConnectorStepResult(success=False, paused_for_captcha=True, message="CAPTCHA detected")

        selectors = self._config.get("selectors", {})

        # Legacy boards render the form inline; the newer board needs the Apply button first
        form = page.locator(selectors.get("application_form", "")).first
        if await form.count() > 0:
            return ConnectorStepResult(success=True, message="Greenhouse application form visible")

        apply_btn = page.locator(selectors.get("apply_button", "")).first
        if await apply_btn.count() > 0:
            await apply_btn.click()
            if hasattr(page, "wait_for_load_state"):
                await page.wait_for_load_state("domcontentloaded", timeout=60000)
            if await detect_captcha(page, self._config):
                return ConnectorStepResult(
                    success=False, paused_for_captcha=True, message="CAPTCHA after apply navigation"
                )
            form = page.locator(selectors.get("application_form", "")).first
            if await form.count() > 0:
                return ConnectorStepResult(success=True, message="Greenhouse application form opened")

        return ConnectorStepResult(
            success=False,
            message=(
                "Greenhouse application form not found on this page. "
                "The posting may be closed or hosted on a customized board."
            ),
        )
