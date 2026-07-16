from typing import Any
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.application.ports.audit import AuditPort
from app.domain.enums import AuditAction, AuditActor
from app.infrastructure.db.models import AuditLog
from app.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)


class SQLAlchemyAuditLog(AuditPort):
    def __init__(self, db: Session):
        self._db = db

    def record(
        self,
        action: AuditAction,
        entity_type: str,
        entity_id: str | UUID,
        actor: AuditActor | str,
        details: dict[str, Any] | None = None,
    ) -> int:
        entry = AuditLog(
            entity_type=entity_type,
            entity_id=str(entity_id),
            action=action.value if isinstance(action, AuditAction) else action,
            actor=actor.value if isinstance(actor, AuditActor) else actor,
            details=details or {},
        )
        self._db.add(entry)
        self._db.commit()
        self._db.refresh(entry)
        logger.info(
            "audit_recorded",
            audit_id=entry.id,
            action=entry.action,
            entity_type=entity_type,
            entity_id=str(entity_id),
        )
        return entry.id

    def record_agent_decision(
        self,
        agent_name: str,
        entity_type: str,
        entity_id: str | UUID,
        decision: dict[str, Any],
    ) -> int:
        return self.record(
            action=AuditAction.AGENT_DECISION,
            entity_type=entity_type,
            entity_id=entity_id,
            actor=f"agent:{agent_name}",
            details={"agent": agent_name, "decision": decision},
        )

    def record_resume_selection(
        self,
        job_id: str | UUID,
        selected_resume_id: str | UUID,
        confidence: float,
        rationale: str,
        details: dict[str, Any] | None = None,
    ) -> int:
        payload = {
            "selected_resume_id": str(selected_resume_id),
            "confidence": confidence,
            "rationale": rationale,
            **(details or {}),
        }
        return self.record(
            action=AuditAction.RESUME_SELECTION,
            entity_type="job",
            entity_id=job_id,
            actor=AuditActor.AGENT,
            details=payload,
        )

    def record_application_action(
        self,
        application_id: str | UUID,
        action: str,
        actor: AuditActor | str,
        details: dict[str, Any] | None = None,
    ) -> int:
        return self.record(
            action=AuditAction.APPLICATION_ACTION,
            entity_type="application",
            entity_id=application_id,
            actor=actor,
            details={"sub_action": action, **(details or {})},
        )

    def record_user_approval(
        self,
        application_id: str | UUID,
        approved: bool,
        details: dict[str, Any] | None = None,
    ) -> int:
        return self.record(
            action=AuditAction.USER_APPROVAL,
            entity_type="application",
            entity_id=application_id,
            actor=AuditActor.USER,
            details={"approved": approved, **(details or {})},
        )

    def query(
        self,
        entity_type: str | None = None,
        entity_id: str | None = None,
        action: AuditAction | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        q = self._db.query(AuditLog).order_by(desc(AuditLog.created_at))
        if entity_type:
            q = q.filter(AuditLog.entity_type == entity_type)
        if entity_id:
            q = q.filter(AuditLog.entity_id == entity_id)
        if action:
            q = q.filter(AuditLog.action == action.value)
        rows = q.offset(offset).limit(limit).all()
        return [
            {
                "id": row.id,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "action": row.action,
                "actor": row.actor,
                "details": row.details,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]
