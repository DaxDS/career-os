from pathlib import Path
from typing import Any, Awaitable, Callable

from app.application.ports.browser_runner import BrowserRunnerPort
from app.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)


class PlaywrightRunner(BrowserRunnerPort):
    """Real Playwright execution with persistent browser profiles."""

    async def execute_run(
        self,
        *,
        profile_path: str,
        storage_state_path: str | None,
        headless: bool,
        browser_name: str,
        steps: Callable[[Any, Any], Awaitable[dict[str, Any]]],
    ) -> dict[str, Any]:
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright is not installed. Run: pip install playwright && playwright install chromium"
            ) from exc

        Path(profile_path).mkdir(parents=True, exist_ok=True)
        async with async_playwright() as playwright:
            browser_factory = getattr(playwright, browser_name, playwright.chromium)
            context = await browser_factory.launch_persistent_context(
                profile_path,
                headless=headless,
            )
            page = context.pages[0] if context.pages else await context.new_page()
            try:
                result = await steps(page, context)
                if storage_state_path:
                    await context.storage_state(path=storage_state_path)
                return result
            finally:
                await context.close()


class MockBrowserRunner(BrowserRunnerPort):
    """Test double — simulates successful automation without Playwright."""

    def __init__(self, *, pause_captcha: bool = False, validation_errors: list[str] | None = None):
        self._pause_captcha = pause_captcha
        self._validation_errors = validation_errors or []

    async def execute_run(
        self,
        *,
        profile_path: str,
        storage_state_path: str | None,
        headless: bool,
        browser_name: str,
        steps: Callable[[Any, Any], Awaitable[dict[str, Any]]],
    ) -> dict[str, Any]:
        class _FakeLocator:
            def __init__(self, selector: str = ""):
                self._selector = selector

            async def count(self) -> int:
                lowered = self._selector.lower()
                if any(token in lowered for token in ("recaptcha", "hcaptcha", "captcha", "challenge")):
                    return 0
                return 1

            async def fill(self, _value: str) -> None:
                return None

            async def set_input_files(self, _path: str) -> None:
                return None

            async def click(self) -> None:
                return None

            async def inner_text(self) -> str:
                return ""

            async def get_attribute(self, _name: str):
                return None

            async def is_checked(self) -> bool:
                return False

            async def check(self) -> None:
                return None

            def nth(self, _index: int):
                return self

            @property
            def first(self):
                return self

            def nth(self, _index: int):
                return self

        class _FakePage:
            url = "https://mock.test/apply"

            async def goto(self, *_args, **_kwargs) -> None:
                return None

            def locator(self, selector: str) -> _FakeLocator:
                return _FakeLocator(selector)

            def get_by_role(self, _role: str, name=None) -> _FakeLocator:
                return _FakeLocator()

            async def inner_text(self, _selector: str) -> str:
                return ""

            async def title(self) -> str:
                return "Apply"

            async def screenshot(self, **_kwargs) -> None:
                return None

        return await steps(_FakePage(), object())

