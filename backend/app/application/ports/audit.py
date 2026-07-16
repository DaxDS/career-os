"""Audit logging port — records immutable events for compliance and learning."""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from app.domain.enums import AuditAction, AuditActor


class AuditPort(ABC):
    @abstractmethod
    def record(
        self,
        action: AuditAction,
        entity_type: str,
        entity_id: str | UUID,
        actor: AuditActor | str,
        details: dict[str, Any] | None = None,
    ) -> int:
        """Append an immutable audit record. Returns audit log ID."""

    @abstractmethod
    def record_agent_decision(
        self,
        agent_name: str,
        entity_type: str,
        entity_id: str | UUID,
        decision: dict[str, Any],
    ) -> int: ...

    @abstractmethod
    def record_resume_selection(
        self,
        job_id: str | UUID,
        selected_resume_id: str | UUID,
        confidence: float,
        rationale: str,
        details: dict[str, Any] | None = None,
    ) -> int: ...

    @abstractmethod
    def record_application_action(
        self,
        application_id: str | UUID,
        action: str,
        actor: AuditActor | str,
        details: dict[str, Any] | None = None,
    ) -> int: ...

    @abstractmethod
    def record_user_approval(
        self,
        application_id: str | UUID,
        approved: bool,
        details: dict[str, Any] | None = None,
    ) -> int: ...

    @abstractmethod
    def query(
        self,
        entity_type: str | None = None,
        entity_id: str | None = None,
        action: AuditAction | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]: ...
