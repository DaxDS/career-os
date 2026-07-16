import uuid

from app.application.ports.browser_automation import AutomationRepositoryPort
from app.application.ports.browser_runner import BrowserAutomationPort
from app.infrastructure.db.automation_models import AutomationRun, BrowserSession


class ApplicationAutomationService:
    """Layer 9 API facade — orchestrates browser automation without modifying prior layers."""

    def __init__(
        self,
        automation: BrowserAutomationPort,
        automation_repo: AutomationRepositoryPort,
    ):
        self._automation = automation
        self._repo = automation_repo

    async def start_submission(
        self,
        user_id: uuid.UUID,
        job_id: uuid.UUID,
        *,
        stop_before_submit: bool | None = None,
    ) -> dict:
        return await self._automation.run_job_submission(
            user_id=user_id,
            job_id=job_id,
            stop_before_submit=stop_before_submit,
        )

    async def resume_after_captcha(self, user_id: uuid.UUID, session_id: uuid.UUID) -> dict:
        return await self._automation.resume_after_captcha(session_id, user_id=user_id)

    def get_run(self, user_id: uuid.UUID, run_id: uuid.UUID) -> AutomationRun:
        run = self._repo.get_run(run_id, user_id)
        if not run:
            raise ValueError("Automation run not found")
        return run

    def list_runs(self, user_id: uuid.UUID, job_id: uuid.UUID) -> list[AutomationRun]:
        return self._repo.list_runs_for_job(user_id, job_id)

    def list_sessions(self, user_id: uuid.UUID) -> list[BrowserSession]:
        return self._repo.list_sessions(user_id)

    def get_action_logs(self, user_id: uuid.UUID, run_id: uuid.UUID) -> list:
        run = self.get_run(user_id, run_id)
        return self._repo.list_action_logs(run.id)
