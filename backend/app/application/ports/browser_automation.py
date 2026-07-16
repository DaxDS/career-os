import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.infrastructure.db.automation_models import AutomationActionLog, AutomationRun, BrowserSession


@dataclass
class AutomationContext:
    """Runtime context passed to browser connectors — no site-specific logic."""

    user_id: uuid.UUID
    job_id: uuid.UUID
    application_id: uuid.UUID
    connector_key: str
    application_url: str
    job_title: str
    company: str
    resume_file: Path | None
    cover_letter_file: Path | None
    email_body: str
    profile_fields: dict[str, str] = field(default_factory=dict)
    stop_before_submit: bool = False
    source_config: dict[str, Any] = field(default_factory=dict)
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectorStepResult:
    success: bool
    paused_for_captcha: bool = False
    validation_errors: list[str] = field(default_factory=list)
    message: str = ""
    screenshot_path: str | None = None


class BrowserConnectorPort(ABC):
    """Site-specific browser automation — resolved by connector_key from job sources."""

    @property
    @abstractmethod
    def connector_key(self) -> str: ...

    @abstractmethod
    async def open_application_page(self, page: Any, context: AutomationContext) -> ConnectorStepResult: ...

    @abstractmethod
    async def navigate_application_flow(self, page: Any, context: AutomationContext) -> ConnectorStepResult: ...

    @abstractmethod
    async def upload_resume(self, page: Any, context: AutomationContext) -> ConnectorStepResult: ...

    @abstractmethod
    async def upload_cover_letter(self, page: Any, context: AutomationContext) -> ConnectorStepResult: ...

    @abstractmethod
    async def fill_recruiter_email(self, page: Any, context: AutomationContext) -> ConnectorStepResult: ...

    @abstractmethod
    async def fill_standard_fields(self, page: Any, context: AutomationContext) -> ConnectorStepResult: ...

    @abstractmethod
    async def detect_validation_errors(self, page: Any, context: AutomationContext) -> list[str]: ...

    @abstractmethod
    async def submit_application(self, page: Any, context: AutomationContext) -> ConnectorStepResult: ...

    @abstractmethod
    async def detect_captcha(self, page: Any, context: AutomationContext) -> bool: ...


class BrowserConnectorRegistryPort(ABC):
    @abstractmethod
    def get(self, connector_key: str) -> BrowserConnectorPort: ...

    @abstractmethod
    def list_keys(self) -> list[str]: ...


class AutomationRepositoryPort(ABC):
    @abstractmethod
    def get_session(
        self, user_id: uuid.UUID, connector_key: str
    ) -> BrowserSession | None: ...

    @abstractmethod
    def get_session_by_id(
        self, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> BrowserSession | None: ...

    @abstractmethod
    def upsert_session(self, session: BrowserSession) -> BrowserSession: ...

    @abstractmethod
    def list_sessions(self, user_id: uuid.UUID) -> list[BrowserSession]: ...

    @abstractmethod
    def create_run(self, run: AutomationRun) -> AutomationRun: ...

    @abstractmethod
    def update_run(self, run: AutomationRun) -> AutomationRun: ...

    @abstractmethod
    def get_run(self, run_id: uuid.UUID, user_id: uuid.UUID) -> AutomationRun | None: ...

    @abstractmethod
    def get_run_by_application(
        self, application_id: uuid.UUID, user_id: uuid.UUID
    ) -> AutomationRun | None: ...

    @abstractmethod
    def list_runs_for_job(self, user_id: uuid.UUID, job_id: uuid.UUID) -> list[AutomationRun]: ...

    @abstractmethod
    def get_paused_run_for_session(
        self, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> AutomationRun | None: ...

    @abstractmethod
    def log_action(self, log: AutomationActionLog) -> AutomationActionLog: ...

    @abstractmethod
    def list_action_logs(self, run_id: uuid.UUID) -> list[AutomationActionLog]: ...
