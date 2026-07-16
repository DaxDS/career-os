import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.application.ports.browser_automation import AutomationRepositoryPort
from app.application.ports.browser_runner import BrowserSessionManagerPort
from app.domain.automation_enums import BrowserSessionStatus
from app.infrastructure.browser.settings import AutomationSettings
from app.infrastructure.db.automation_models import BrowserSession
from app.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)


class BrowserSessionManager(BrowserSessionManagerPort):
    """Manages persistent Playwright browser profiles and storage state."""

    def __init__(self, repo: AutomationRepositoryPort, settings: AutomationSettings):
        self._repo = repo
        self._settings = settings

    def get_or_create_session(
        self, user_id: uuid.UUID, connector_key: str, browser_name: str
    ) -> BrowserSession:
        existing = self._repo.get_session(user_id, connector_key)
        if existing:
            existing.status = BrowserSessionStatus.ACTIVE.value
            existing.last_used_at = datetime.now(timezone.utc)
            return self._repo.upsert_session(existing)

        profile_dir = self._profile_dir(user_id, connector_key)
        profile_dir.mkdir(parents=True, exist_ok=True)
        storage_path = profile_dir / "storage_state.json"

        session = BrowserSession(
            user_id=user_id,
            connector_key=connector_key,
            profile_path=str(profile_dir),
            storage_state_path=str(storage_path),
            status=BrowserSessionStatus.ACTIVE.value,
            browser_name=browser_name,
            last_used_at=datetime.now(timezone.utc),
        )
        created = self._repo.upsert_session(session)
        logger.info(
            "browser_session_created",
            session_id=str(created.id),
            connector_key=connector_key,
        )
        return created

    def save_storage_state(self, session: BrowserSession) -> None:
        logger.info(
            "browser_storage_state_saved",
            session_id=str(session.id),
            path=session.storage_state_path,
        )

    def restore_storage_state(self, session: BrowserSession) -> str | None:
        path = Path(session.storage_state_path)
        if path.exists():
            logger.info(
                "browser_storage_state_restored",
                session_id=str(session.id),
                path=str(path),
            )
            return str(path)
        return None

    def mark_idle(self, session: BrowserSession) -> BrowserSession:
        session.status = BrowserSessionStatus.IDLE.value
        session.last_used_at = datetime.now(timezone.utc)
        return self._repo.upsert_session(session)

    def _profile_dir(self, user_id: uuid.UUID, connector_key: str) -> Path:
        return self._settings.browser_profiles_path / str(user_id) / connector_key
