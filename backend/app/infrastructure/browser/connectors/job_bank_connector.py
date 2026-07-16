"""Job Bank Canada — login, Direct Apply, and external employer application flows."""

from __future__ import annotations

import re
from typing import Any

from app.application.ports.browser_automation import AutomationContext, ConnectorStepResult
from app.infrastructure.browser.captcha_detector import detect_captcha
from app.infrastructure.browser.connectors.base import ConfigDrivenBrowserConnector, load_connector_config
from app.infrastructure.browser.settings import get_automation_settings
from app.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)

_MAINTENANCE_MARKERS = (
    "system maintenance",
    "interruption des services",
    "outage / interruption",
)

_APPLY_SECTION_LABELS = (
    "Show how to apply",
    "Voir comment postuler",
    "How to apply",
)

_DIRECT_APPLY_LABELS = (
    "Direct Apply",
    "Postuler directement",
    "Apply on Job Bank",
    "Apply directly",
)

_EXTERNAL_LINK_LABELS = (
    "Employer's website",
    "Site Web de l'employeur",
    "External website",
    "Company website",
)


class JobBankCanadaBrowserConnector(ConfigDrivenBrowserConnector):
    """Job Bank–specific automation beyond generic form filling."""

    def __init__(self):
        super().__init__("job_bank_canada", load_connector_config("job_bank_canada"))
        self._company = ConfigDrivenBrowserConnector(
            "company_career_pages", load_connector_config("company_career_pages")
        )

    async def open_application_page(self, page: Any, context: AutomationContext) -> ConnectorStepResult:
        url = context.application_url
        if not url:
            return ConnectorStepResult(success=False, message="No application URL available")

        await page.goto(url, wait_until="domcontentloaded", timeout=90000)
        maintenance = await self._is_maintenance(page)
        if maintenance:
            return ConnectorStepResult(success=False, message=maintenance)

        if await detect_captcha(page, self._config):
            return ConnectorStepResult(success=False, paused_for_captcha=True, message="CAPTCHA detected")

        logged_in = await self._ensure_logged_in(page)
        if logged_in is False:
            return ConnectorStepResult(
                success=False,
                message=(
                    "Job Bank login failed. Add JOB_BANK_EMAIL and JOB_BANK_PASSWORD to backend/.env "
                    "(Job Bank Plus account required for Direct Apply)."
                ),
            )

        # Re-open posting after login redirect
        if page.url != url and "jobposting" not in page.url:
            await page.goto(url, wait_until="domcontentloaded", timeout=90000)
            maintenance = await self._is_maintenance(page)
            if maintenance:
                return ConnectorStepResult(success=False, message=maintenance)

        return ConnectorStepResult(success=True, message=f"Opened {url}")

    async def navigate_application_flow(self, page: Any, context: AutomationContext) -> ConnectorStepResult:
        if await detect_captcha(page, self._config):
            return ConnectorStepResult(success=False, paused_for_captcha=True, message="CAPTCHA detected")

        await self._expand_apply_section(page)

        external_url = await self._find_external_apply_url(page)
        if external_url:
            context.extras["apply_mode"] = "external"
            context.extras["external_url"] = external_url
            await page.goto(external_url, wait_until="domcontentloaded", timeout=90000)
            if await detect_captcha(page, self._company._config):
                return ConnectorStepResult(
                    success=False, paused_for_captcha=True, message="CAPTCHA on employer site"
                )
            return ConnectorStepResult(success=True, message=f"Opened employer site {external_url}")

        clicked = await self._click_direct_apply(page)
        if clicked:
            context.extras["apply_mode"] = "direct_apply"
            if hasattr(page, "wait_for_load_state"):
                await page.wait_for_load_state("domcontentloaded", timeout=60000)
            return ConnectorStepResult(success=True, message="Opened Job Bank Direct Apply flow")

        context.extras["apply_mode"] = "posting_only"
        return ConnectorStepResult(
            success=False,
            message=(
                "No Direct Apply button or employer website link found. "
                "This posting may require email/phone application, or Job Bank may still be in maintenance."
            ),
        )

    async def upload_resume(self, page: Any, context: AutomationContext) -> ConnectorStepResult:
        mode = context.extras.get("apply_mode", "")
        if mode == "external":
            return await self._company.upload_resume(page, context)

        result = await self._upload_file_flexible(page, context, context.resume_file, "Resume")
        if result.success:
            return result

        # Job Bank may offer "Upload a document" instead of visible file input on first paint
        for label in ("Upload a document", "Add a document", "Upload resume", "Téléverser"):
            trigger = page.get_by_role("button", name=re.compile(label, re.I))
            if await trigger.count() == 0:
                trigger = page.locator(f"a:has-text('{label}')")
            if await trigger.count() > 0:
                await trigger.first.click()
                result = await self._upload_file_flexible(page, context, context.resume_file, "Resume")
                if result.success:
                    return result

        if mode == "direct_apply":
            return ConnectorStepResult(
                success=False,
                message="Direct Apply form opened but resume upload field was not found",
            )
        return ConnectorStepResult(success=False, message=result.message or "Resume upload field not found")

    async def upload_cover_letter(self, page: Any, context: AutomationContext) -> ConnectorStepResult:
        if context.extras.get("apply_mode") == "external":
            return await self._company.upload_cover_letter(page, context)
        return await self._upload_file_flexible(
            page, context, context.cover_letter_file, "Cover letter", optional=True
        )

    async def fill_recruiter_email(self, page: Any, context: AutomationContext) -> ConnectorStepResult:
        if context.extras.get("apply_mode") == "external":
            return await self._company.fill_recruiter_email(page, context)
        return await super().fill_recruiter_email(page, context)

    async def fill_standard_fields(self, page: Any, context: AutomationContext) -> ConnectorStepResult:
        if context.extras.get("apply_mode") == "external":
            return await self._company.fill_standard_fields(page, context)
        await super().fill_standard_fields(page, context)
        # Job Bank consent checkbox for Direct Apply
        for label in (
            "I agree to share my email",
            "J'accepte de communiquer mon adresse courriel",
        ):
            box = page.locator(f"label:has-text('{label}') input[type='checkbox']")
            if await box.count() == 0:
                box = page.get_by_role("checkbox", name=re.compile(label[:20], re.I))
            if await box.count() > 0:
                if not await box.first.is_checked():
                    await box.first.check()
        return ConnectorStepResult(success=True, message="Standard fields filled")

    async def submit_application(self, page: Any, context: AutomationContext) -> ConnectorStepResult:
        if context.stop_before_submit:
            return ConnectorStepResult(success=True, message="Stopped before final submission as configured")

        if context.extras.get("apply_mode") == "external":
            return await self._company.submit_application(page, context)

        for label in _DIRECT_APPLY_LABELS + ("Submit", "Send application", "Envoyer"):
            btn = page.get_by_role("button", name=re.compile(re.escape(label), re.I))
            if await btn.count() > 0:
                await btn.first.click()
                return ConnectorStepResult(success=True, message=f"Clicked {label}")
            link = page.get_by_role("link", name=re.compile(re.escape(label), re.I))
            if await link.count() > 0:
                await link.first.click()
                return ConnectorStepResult(success=True, message=f"Clicked {label}")

        return await super().submit_application(page, context)

    async def _is_maintenance(self, page: Any) -> str | None:
        try:
            body = (await page.inner_text("body")).lower()
        except Exception:
            return None
        if any(marker in body for marker in _MAINTENANCE_MARKERS):
            return (
                "Job Bank is down for nightly maintenance (12:00 a.m.–7:00 a.m. Eastern). "
                "Try again after 7:00 a.m. ET."
            )
        return None

    async def _ensure_logged_in(self, page: Any) -> bool | None:
        settings = get_automation_settings()
        email = settings.job_bank_email.strip()
        password = settings.job_bank_password
        if not email or not password:
            logger.info("job_bank_login_skipped", reason="no_credentials")
            return None

        if await page.locator("text=Sign out").count() > 0 or await page.locator("text=Sign Out").count() > 0:
            return True

        await page.goto("https://www.jobbank.gc.ca/login", wait_until="domcontentloaded", timeout=60000)
        if await page.locator("text=Sign out").count() > 0:
            return True

        email_input = page.locator(
            "input[type='email'], input[name*='email'], input[id*='email'], input[name*='user']"
        ).first
        password_input = page.locator("input[type='password']").first
        if await email_input.count() == 0 or await password_input.count() == 0:
            return False

        await email_input.fill(email)
        await password_input.fill(password)
        submit = page.locator(
            "button[type='submit'], input[type='submit'], button:has-text('Sign in'), button:has-text('Log in')"
        ).first
        if await submit.count() > 0:
            await submit.click()
            if hasattr(page, "wait_for_load_state"):
                await page.wait_for_load_state("domcontentloaded", timeout=60000)

        if await page.locator("text=Sign out").count() > 0 or await page.locator("text=Sign Out").count() > 0:
            logger.info("job_bank_login_success")
            return True

        logger.warning("job_bank_login_failed")
        return False

    async def _expand_apply_section(self, page: Any) -> None:
        for label in _APPLY_SECTION_LABELS:
            loc = page.get_by_role("button", name=re.compile(label, re.I))
            if await loc.count() == 0:
                loc = page.locator(f"a:has-text('{label}')")
            if await loc.count() > 0:
                await loc.first.click()
                if hasattr(page, "wait_for_timeout"):
                    await page.wait_for_timeout(800)
                return

    async def _click_direct_apply(self, page: Any) -> bool:
        for label in _DIRECT_APPLY_LABELS:
            loc = page.get_by_role("button", name=re.compile(label, re.I))
            if await loc.count() == 0:
                loc = page.get_by_role("link", name=re.compile(label, re.I))
            if await loc.count() == 0:
                loc = page.locator(f"a:has-text('{label}'), button:has-text('{label}')")
            if await loc.count() > 0:
                await loc.first.click()
                return True
        return False

    async def _find_external_apply_url(self, page: Any) -> str | None:
        for label in _EXTERNAL_LINK_LABELS:
            loc = page.get_by_role("link", name=re.compile(label, re.I))
            if await loc.count() > 0:
                href = await loc.first.get_attribute("href")
                if href and href.startswith("http"):
                    return href

        # Any external link in apply/details section pointing off jobbank
        for loc in [
            page.locator(".job-posting-detail-apply a[href^='http']"),
            page.locator("[class*='apply'] a[href^='http']"),
        ]:
            count = await loc.count()
            for i in range(min(count, 5)):
                href = await loc.nth(i).get_attribute("href")
                if href and "jobbank.gc.ca" not in href:
                    return href
        return None

    async def _upload_file_flexible(
        self,
        page: Any,
        context: AutomationContext,
        file_path: Any,
        label: str,
        *,
        optional: bool = False,
    ) -> ConnectorStepResult:
        from pathlib import Path

        path = Path(file_path) if file_path else None
        if not path or not path.exists():
            return ConnectorStepResult(success=True, message=f"No {label} file to upload")

        selectors = [
            self._config.get("selectors", {}).get("resume_upload", ""),
            "input[type='file']",
        ]
        if label == "Cover letter":
            selectors.insert(0, self._config.get("selectors", {}).get("cover_letter_upload", ""))

        for selector in selectors:
            if not selector:
                continue
            locator = page.locator(selector).first
            if await locator.count() > 0:
                await locator.set_input_files(str(path))
                return ConnectorStepResult(success=True, message=f"{label} uploaded")

        if optional:
            return ConnectorStepResult(success=True, message=f"No {label} upload field (optional)")
        return ConnectorStepResult(success=False, message=f"{label} upload field not found")
