import uuid
from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class BrowserRunnerPort(ABC):
    """Abstraction over Playwright for testability."""

    @abstractmethod
    async def execute_run(
        self,
        *,
        profile_path: str,
        storage_state_path: str | None,
        headless: bool,
        browser_name: str,
        steps: Any,
    ) -> dict[str, Any]: ...


class BrowserSessionManagerPort(ABC):
    @abstractmethod
    def get_or_create_session(
        self, user_id: uuid.UUID, connector_key: str, browser_name: str
    ) -> Any: ...

    @abstractmethod
    def save_storage_state(self, session_id: uuid.UUID, storage_state_path: str) -> None: ...

    @abstractmethod
    def restore_storage_state(self, session_id: uuid.UUID) -> str | None: ...


class BrowserAutomationPort(ABC):
    """Layer 9 Playwright automation — implements the V2 contract from future.py."""

    @abstractmethod
    async def submit_application(
        self,
        application_id: UUID,
        *,
        user_id: UUID,
        stop_before_submit: bool | None = None,
    ) -> dict[str, Any]: ...

    @abstractmethod
    async def pause_for_captcha(self, session_id: UUID) -> None: ...

    @abstractmethod
    async def resume_after_captcha(self, session_id: UUID, *, user_id: UUID) -> dict[str, Any]: ...

    @abstractmethod
    async def run_job_submission(
        self,
        *,
        user_id: UUID,
        job_id: UUID,
        stop_before_submit: bool | None = None,
    ) -> dict[str, Any]: ...
