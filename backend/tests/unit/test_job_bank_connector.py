"""Tests for Job Bank browser connector."""

import pytest

from app.application.ports.browser_automation import AutomationContext
from app.infrastructure.browser.connectors.job_bank_connector import JobBankCanadaBrowserConnector


class _FakePage:
    def __init__(self, body: str, url: str = "https://www.jobbank.gc.ca/jobsearch/jobposting/1"):
        self._body = body
        self.url = url

    async def inner_text(self, _selector: str) -> str:
        return self._body

    async def goto(self, url: str, **_kwargs) -> None:
        self.url = url

    def locator(self, _selector: str):
        return _FakeLocator()

    def get_by_role(self, _role: str, name=None):
        return _FakeLocator()


class _FakeLocator:
    async def count(self) -> int:
        return 0

    @property
    def first(self):
        return self


def _context(**extras) -> AutomationContext:
    import uuid

    return AutomationContext(
        user_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        application_id=uuid.uuid4(),
        connector_key="job_bank_canada",
        application_url="https://www.jobbank.gc.ca/jobsearch/jobposting/49788195",
        job_title="AI consultant",
        company="Bell Canada",
        resume_file=None,
        cover_letter_file=None,
        email_body="",
        extras=extras,
    )


@pytest.mark.asyncio
async def test_open_page_detects_maintenance():
    connector = JobBankCanadaBrowserConnector()
    page = _FakePage("Job Bank's website will be unavailable due to system maintenance")
    result = await connector.open_application_page(page, _context())
    assert result.success is False
    assert "maintenance" in result.message.lower()


@pytest.mark.asyncio
async def test_navigate_fails_without_apply_options():
    connector = JobBankCanadaBrowserConnector()
    page = _FakePage("Software developer role at Acme")
    result = await connector.navigate_application_flow(page, _context())
    assert result.success is False
    assert "Direct Apply" in result.message or "employer" in result.message.lower()
