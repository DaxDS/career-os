import uuid
from typing import Any

from app.application.ports.browser_automation import AutomationRepositoryPort
from app.domain.automation_enums import AutomationActionType
from app.infrastructure.db.automation_models import AutomationActionLog
from app.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)


class AutomationActionLogger:
    """Logs every browser action to DB and structured logs."""

    def __init__(self, repo: AutomationRepositoryPort):
        self._repo = repo

    def log(
        self,
        run_id: uuid.UUID,
        action: AutomationActionType | str,
        details: dict[str, Any] | None = None,
    ) -> AutomationActionLog:
        action_value = action.value if isinstance(action, AutomationActionType) else action
        entry = AutomationActionLog(
            run_id=run_id,
            action=action_value,
            details=details or {},
        )
        saved = self._repo.log_action(entry)
        logger.info("browser_action", run_id=str(run_id), action=action_value, **(details or {}))
        return saved
