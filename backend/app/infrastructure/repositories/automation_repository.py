import uuid

from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from app.application.ports.browser_automation import AutomationRepositoryPort
from app.infrastructure.db.automation_models import (
    AutomationActionLog,
    AutomationRun,
    BrowserSession,
)


class SQLAlchemyAutomationRepository(AutomationRepositoryPort):
    def __init__(self, db: Session):
        self._db = db

    def get_session(self, user_id: uuid.UUID, connector_key: str) -> BrowserSession | None:
        return (
            self._db.query(BrowserSession)
            .filter(
                BrowserSession.user_id == user_id,
                BrowserSession.connector_key == connector_key,
            )
            .first()
        )

    def get_session_by_id(
        self, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> BrowserSession | None:
        return (
            self._db.query(BrowserSession)
            .filter(BrowserSession.id == session_id, BrowserSession.user_id == user_id)
            .first()
        )

    def upsert_session(self, session: BrowserSession) -> BrowserSession:
        existing = self.get_session(session.user_id, session.connector_key)
        if existing:
            existing.profile_path = session.profile_path
            existing.storage_state_path = session.storage_state_path
            existing.status = session.status
            existing.browser_name = session.browser_name
            existing.session_metadata = session.session_metadata
            existing.last_used_at = session.last_used_at
            self._db.commit()
            self._db.refresh(existing)
            return existing
        self._db.add(session)
        self._db.commit()
        self._db.refresh(session)
        return session

    def list_sessions(self, user_id: uuid.UUID) -> list[BrowserSession]:
        return (
            self._db.query(BrowserSession)
            .filter(BrowserSession.user_id == user_id)
            .order_by(BrowserSession.connector_key)
            .all()
        )

    def create_run(self, run: AutomationRun) -> AutomationRun:
        self._db.add(run)
        self._db.commit()
        self._db.refresh(run)
        return run

    def update_run(self, run: AutomationRun) -> AutomationRun:
        self._db.commit()
        self._db.refresh(run)
        return run

    def get_run(self, run_id: uuid.UUID, user_id: uuid.UUID) -> AutomationRun | None:
        return (
            self._db.query(AutomationRun)
            .options(joinedload(AutomationRun.action_logs))
            .filter(AutomationRun.id == run_id, AutomationRun.user_id == user_id)
            .first()
        )

    def get_run_by_application(
        self, application_id: uuid.UUID, user_id: uuid.UUID
    ) -> AutomationRun | None:
        return (
            self._db.query(AutomationRun)
            .filter(
                AutomationRun.application_id == application_id,
                AutomationRun.user_id == user_id,
            )
            .order_by(desc(AutomationRun.created_at))
            .first()
        )

    def list_runs_for_job(self, user_id: uuid.UUID, job_id: uuid.UUID) -> list[AutomationRun]:
        return (
            self._db.query(AutomationRun)
            .filter(AutomationRun.user_id == user_id, AutomationRun.job_id == job_id)
            .order_by(desc(AutomationRun.created_at))
            .all()
        )

    def get_paused_run_for_session(
        self, session_id: uuid.UUID, user_id: uuid.UUID
    ) -> AutomationRun | None:
        from app.domain.automation_enums import AutomationRunStatus

        return (
            self._db.query(AutomationRun)
            .filter(
                AutomationRun.browser_session_id == session_id,
                AutomationRun.user_id == user_id,
                AutomationRun.status == AutomationRunStatus.PAUSED_CAPTCHA.value,
            )
            .order_by(desc(AutomationRun.created_at))
            .first()
        )

    def log_action(self, log: AutomationActionLog) -> AutomationActionLog:
        self._db.add(log)
        self._db.commit()
        self._db.refresh(log)
        return log

    def list_action_logs(self, run_id: uuid.UUID) -> list[AutomationActionLog]:
        return (
            self._db.query(AutomationActionLog)
            .filter(AutomationActionLog.run_id == run_id)
            .order_by(AutomationActionLog.created_at)
            .all()
        )
