import uuid
from typing import Any

from app.application.ports.audit import AuditPort
from app.application.ports.notification import NotificationPort
from app.application.ports.scheduler_repository import PipelineRunRepositoryPort
from app.domain.enums import AuditAction, AuditActor
from app.infrastructure.db.scheduler_models import PipelineNotification
from app.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)


class PipelineNotifier(NotificationPort):
    def __init__(self, scheduler_repo: PipelineRunRepositoryPort, audit: AuditPort | None = None):
        self._repo = scheduler_repo
        self._audit = audit

    def notify_user(
        self,
        user_id: uuid.UUID,
        message: str,
        *,
        pipeline_run_id: uuid.UUID,
        details: dict[str, Any] | None = None,
    ) -> None:
        notification = PipelineNotification(
            user_id=user_id,
            pipeline_run_id=pipeline_run_id,
            message=message,
            details=details or {},
        )
        self._repo.create_notification(notification)
        if self._audit:
            self._audit.record(
                action=AuditAction.SYSTEM_EVENT,
                entity_type="pipeline_notification",
                entity_id=str(notification.id),
                actor=AuditActor.SYSTEM,
                details={"message": message, "pipeline_run_id": str(pipeline_run_id), **(details or {})},
            )
        logger.info(
            "pipeline_notification_sent",
            user_id=str(user_id),
            pipeline_run_id=str(pipeline_run_id),
            message=message,
        )
