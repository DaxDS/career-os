"""Tests for Workday and Greenhouse browser connectors — mirrors test_job_bank_connector.py."""

import uuid

import pytest

from app.application.ports.browser_automation import AutomationContext
from app.infrastructure.browser.connectors.ats_connectors import (
    GreenhouseBrowserConnector,
    WorkdayBrowserConnector,
)


class _FakeLocator:
    def __init__(self, page: "_FakePage", selector: str):
        self._page = page
        self._selector = selector

    async def count(self) -> int:
        for fragment, count in self._page.selector_counts.items():
            if fragment in self._selector:
                return count
        return 0

    @property
    def first(self):
        return self

    async def click(self) -> None:
        self._page.clicked.append(self._selector)

    async def fill(self, value: str) -> None:
        self._page.filled[self._selector] = value


class _FakePage:
    """Selector fragments in selector_counts control which elements 'exist'."""

    def __init__(
        self,
        body: str = "",
        url: str = "https://example.com/job/1",
        selector_counts: dict[str, int] | None = None,
    ):
        self._body = body
        self.url = url
        self.selector_counts = selector_counts or {}
        self.clicked: list[str] = []
        self.filled: dict[str, str] = {}

    async def inner_text(self, _selector: str) -> str:
        return self._body

    async def title(self) -> str:
        return ""

    async def goto(self, url: str, **_kwargs) -> None:
        self.url = url

    async def wait_for_load_state(self, *_args, **_kwargs) -> None:
        pass

    def locator(self, selector: str) -> _FakeLocator:
        return _FakeLocator(self, selector)


def _context(connector_key: str, **kwargs) -> AutomationContext:
    defaults = dict(
        user_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        application_id=uuid.uuid4(),
        connector_key=connector_key,
        application_url="https://example.com/job/1",
        job_title="AI Engineer",
        company="Acme",
        resume_file=None,
        cover_letter_file=None,
        email_body="",
    )
    defaults.update(kwargs)
    return AutomationContext(**defaults)


# ---------------------------------------------------------------- Workday


@pytest.mark.asyncio
async def test_workday_open_page_pauses_on_captcha():
    connector = WorkdayBrowserConnector()
    page = _FakePage(body="please verify you are human")
    result = await connector.open_application_page(
        page, _context("workday", application_url="https://acme.wd5.myworkdayjobs.com/job/R1")
    )
    assert result.success is False
    assert result.paused_for_captcha is True


@pytest.mark.asyncio
async def test_workday_navigate_clicks_apply_then_manual():
    connector = WorkdayBrowserConnector()
    page = _FakePage(
        body="AI Engineer at Acme",
        selector_counts={"adventureButton": 1, "applyManually": 1},
    )
    result = await connector.navigate_application_flow(page, _context("workday"))
    assert result.success is True
    assert any("adventureButton" in s for s in page.clicked)
    assert any("applyManually" in s for s in page.clicked)


@pytest.mark.asyncio
async def test_workday_navigate_detects_sign_in_wall():
    connector = WorkdayBrowserConnector()
    page = _FakePage(
        body="Sign In to continue. Email Address / Password",
        selector_counts={"signInFormOkButton": 1},
    )
    result = await connector.navigate_application_flow(page, _context("workday"))
    assert result.success is False
    assert "account" in result.message.lower()


@pytest.mark.asyncio
async def test_workday_stop_before_submit_never_clicks():
    connector = WorkdayBrowserConnector()
    page = _FakePage(selector_counts={"pageFooterNextButton": 1})
    result = await connector.submit_application(
        page, _context("workday", stop_before_submit=True)
    )
    assert result.success is True
    assert "before final submission" in result.message.lower()
    assert page.clicked == []


@pytest.mark.asyncio
async def test_workday_fills_split_name_fields():
    connector = WorkdayBrowserConnector()
    page = _FakePage(selector_counts={"legalNameSection_firstName": 1, "legalNameSection_lastName": 1})
    context = _context("workday", profile_fields={"name": "Ada Lovelace King"})
    result = await connector.fill_standard_fields(page, context)
    assert result.success is True
    first = next(v for k, v in page.filled.items() if "firstName" in k)
    last = next(v for k, v in page.filled.items() if "lastName" in k)
    assert first == "Ada"
    assert last == "Lovelace King"


# -------------------------------------------------------------- Greenhouse


@pytest.mark.asyncio
async def test_greenhouse_open_page_pauses_on_captcha():
    connector = GreenhouseBrowserConnector()
    page = _FakePage(body="complete the captcha to continue")
    result = await connector.open_application_page(
        page, _context("greenhouse", application_url="https://boards.greenhouse.io/acme/jobs/1")
    )
    assert result.success is False
    assert result.paused_for_captcha is True


@pytest.mark.asyncio
async def test_greenhouse_navigate_succeeds_when_form_inline():
    connector = GreenhouseBrowserConnector()
    page = _FakePage(selector_counts={"#application": 1})
    result = await connector.navigate_application_flow(page, _context("greenhouse"))
    assert result.success is True
    assert page.clicked == []


@pytest.mark.asyncio
async def test_greenhouse_navigate_fails_without_form():
    connector = GreenhouseBrowserConnector()
    page = _FakePage(body="This job is no longer accepting applications")
    result = await connector.navigate_application_flow(page, _context("greenhouse"))
    assert result.success is False
    assert "form not found" in result.message.lower()


@pytest.mark.asyncio
async def test_greenhouse_stop_before_submit_never_clicks():
    connector = GreenhouseBrowserConnector()
    page = _FakePage(selector_counts={"submit_app": 1})
    result = await connector.submit_application(
        page, _context("greenhouse", stop_before_submit=True)
    )
    assert result.success is True
    assert page.clicked == []


@pytest.mark.asyncio
async def test_greenhouse_fills_split_name_fields():
    connector = GreenhouseBrowserConnector()
    page = _FakePage(selector_counts={"first_name": 1, "last_name": 1})
    context = _context("greenhouse", profile_fields={"name": "Grace Hopper"})
    result = await connector.fill_standard_fields(page, context)
    assert result.success is True
    assert any(v == "Grace" for v in page.filled.values())
    assert any(v == "Hopper" for v in page.filled.values())
