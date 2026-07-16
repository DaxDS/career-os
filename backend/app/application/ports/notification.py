import uuid
from abc import ABC, abstractmethod
from typing import Any


class NotificationPort(ABC):
    @abstractmethod
    def notify_user(
        self,
        user_id: uuid.UUID,
        message: str,
        *,
        pipeline_run_id: uuid.UUID,
        details: dict[str, Any] | None = None,
    ) -> None: ...
