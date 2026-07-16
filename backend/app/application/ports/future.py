"""Future-feature interfaces — stubs only, not implemented in V1."""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID


class FutureBrowserAutomationPort(ABC):
    """Future stub — superseded by Layer 9 ports in application/ports/browser_runner.py."""

    @abstractmethod
    async def submit_application(self, application_id: UUID) -> dict[str, Any]: ...

    @abstractmethod
    async def pause_for_captcha(self, session_id: UUID) -> None: ...

    @abstractmethod
    async def resume_after_captcha(self, session_id: UUID) -> None: ...


class DesktopPackagingPort(ABC):
    """V3: Tauri Windows desktop packaging."""

    @abstractmethod
    def get_local_api_url(self) -> str: ...

    @abstractmethod
    def spawn_sidecar(self) -> None: ...


class InterviewCoachingPort(ABC):
    """Future: AI interview preparation."""

    @abstractmethod
    async def generate_prep(self, application_id: UUID) -> dict[str, Any]: ...


class CompanyIntelligencePort(ABC):
    """Future: Company research and insights."""

    @abstractmethod
    async def get_company_profile(self, company_name: str) -> dict[str, Any]: ...


class RecruiterCRMPort(ABC):
    """Future: Recruiter relationship management."""

    @abstractmethod
    async def log_outreach(self, application_id: UUID, contact: dict[str, str]) -> None: ...
