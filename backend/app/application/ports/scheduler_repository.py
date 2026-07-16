import uuid
from abc import ABC, abstractmethod

from app.infrastructure.db.scheduler_models import PipelineNotification, PipelineRun


class PipelineRunRepositoryPort(ABC):
    @abstractmethod
    def create_run(self, run: PipelineRun) -> PipelineRun: ...

    @abstractmethod
    def update_run(self, run: PipelineRun) -> PipelineRun: ...

    @abstractmethod
    def get_run(self, user_id: uuid.UUID, run_id: uuid.UUID) -> PipelineRun | None: ...

    @abstractmethod
    def list_runs(self, user_id: uuid.UUID, *, limit: int = 20) -> list[PipelineRun]: ...

    @abstractmethod
    def create_notification(self, notification: PipelineNotification) -> PipelineNotification: ...

    @abstractmethod
    def list_notifications(
        self, user_id: uuid.UUID, *, limit: int = 10, unread_only: bool = False
    ) -> list[PipelineNotification]: ...

    @abstractmethod
    def mark_notification_read(
        self, user_id: uuid.UUID, notification_id: uuid.UUID
    ) -> PipelineNotification | None: ...
