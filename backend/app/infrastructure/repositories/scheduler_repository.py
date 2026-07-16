import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.application.ports.scheduler_repository import PipelineRunRepositoryPort
from app.infrastructure.db.scheduler_models import PipelineNotification, PipelineRun


class SQLAlchemyPipelineRunRepository(PipelineRunRepositoryPort):
    def __init__(self, db: Session):
        self._db = db

    def create_run(self, run: PipelineRun) -> PipelineRun:
        self._db.add(run)
        self._db.commit()
        self._db.refresh(run)
        return run

    def update_run(self, run: PipelineRun) -> PipelineRun:
        self._db.commit()
        self._db.refresh(run)
        return run

    def get_run(self, user_id: uuid.UUID, run_id: uuid.UUID) -> PipelineRun | None:
        return (
            self._db.query(PipelineRun)
            .filter(PipelineRun.id == run_id, PipelineRun.user_id == user_id)
            .first()
        )

    def list_runs(self, user_id: uuid.UUID, *, limit: int = 20) -> list[PipelineRun]:
        return (
            self._db.query(PipelineRun)
            .filter(PipelineRun.user_id == user_id)
            .order_by(PipelineRun.created_at.desc())
            .limit(limit)
            .all()
        )

    def create_notification(self, notification: PipelineNotification) -> PipelineNotification:
        self._db.add(notification)
        self._db.commit()
        self._db.refresh(notification)
        return notification

    def list_notifications(
        self, user_id: uuid.UUID, *, limit: int = 10, unread_only: bool = False
    ) -> list[PipelineNotification]:
        q = self._db.query(PipelineNotification).filter(PipelineNotification.user_id == user_id)
        if unread_only:
            q = q.filter(PipelineNotification.read_at.is_(None))
        return q.order_by(PipelineNotification.created_at.desc()).limit(limit).all()

    def mark_notification_read(
        self, user_id: uuid.UUID, notification_id: uuid.UUID
    ) -> PipelineNotification | None:
        notification = (
            self._db.query(PipelineNotification)
            .filter(
                PipelineNotification.id == notification_id,
                PipelineNotification.user_id == user_id,
            )
            .first()
        )
        if not notification:
            return None
        notification.read_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(notification)
        return notification
