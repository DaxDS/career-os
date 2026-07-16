import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from app.application.ports.application_repository import ApplicationRepositoryPort
from app.application.ports.audit import AuditPort
from app.application.ports.browser_automation import (
    AutomationContext,
    AutomationRepositoryPort,
    BrowserConnectorRegistryPort,
)
from app.application.ports.browser_runner import BrowserAutomationPort, BrowserRunnerPort
from app.application.ports.job_repository import JobRepositoryPort
from app.application.ports.resume_repository import ResumeRepositoryPort
from app.application.ports.storage import FileStoragePort
from app.application.ports.user_repository import UserRepositoryPort
from app.application.services.connector_resolver import (
    resolve_application_url,
    resolve_browser_connector_key,
)
from app.domain.automation_enums import AutomationActionType, AutomationRunStatus
from app.domain.enums import ApplicationStatus, AuditActor, DocumentType
from app.infrastructure.browser.action_logger import AutomationActionLogger
from app.infrastructure.browser.session_manager import BrowserSessionManager
from app.infrastructure.browser.settings import AutomationSettings
from app.infrastructure.db.automation_models import AutomationRun, BrowserSession
from app.infrastructure.db.models import JobApplication, JobPosting
from app.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)

_STEP_ORDER = (
    "open_application_page",
    "navigate_application_flow",
    "upload_resume",
    "upload_cover_letter",
    "fill_recruiter_email",
    "fill_standard_fields",
    "submit_application",
)


class PlaywrightBrowserAutomation(BrowserAutomationPort):
    """Layer 9 — Playwright-based job application submission."""

    def __init__(
        self,
        application_repo: ApplicationRepositoryPort,
        job_repo: JobRepositoryPort,
        user_repo: UserRepositoryPort,
        resume_repo: ResumeRepositoryPort,
        automation_repo: AutomationRepositoryPort,
        connector_registry: BrowserConnectorRegistryPort,
        session_manager: BrowserSessionManager,
        runner: BrowserRunnerPort,
        storage: FileStoragePort,
        settings: AutomationSettings,
        tracking_service: Any | None = None,
        audit: AuditPort | None = None,
    ):
        self._applications = application_repo
        self._jobs = job_repo
        self._users = user_repo
        self._resumes = resume_repo
        self._automation = automation_repo
        self._connectors = connector_registry
        self._sessions = session_manager
        self._runner = runner
        self._storage = storage
        self._settings = settings
        self._tracking = tracking_service
        self._audit = audit
        self._action_logger = AutomationActionLogger(automation_repo)

    async def run_job_submission(
        self,
        *,
        user_id: UUID,
        job_id: UUID,
        stop_before_submit: bool | None = None,
    ) -> dict[str, Any]:
        application = self._applications.get_by_job(user_id, job_id)
        if not application:
            raise ValueError("Application not found — generate documents first (Layer 6)")
        if application.status != ApplicationStatus.APPROVED.value:
            raise ValueError(
                f"Application must be approved before automation (status: {application.status})"
            )
        return await self.submit_application(
            application.id, user_id=user_id, stop_before_submit=stop_before_submit
        )

    async def submit_application(
        self, application_id: UUID, *, user_id: UUID, stop_before_submit: bool | None = None
    ) -> dict[str, Any]:
        if not self._settings.automation_enabled:
            raise ValueError("Browser automation is disabled")

        application = self._applications.get_by_id(application_id, user_id)
        if not application:
            raise ValueError("Application not found")
        if application.status != ApplicationStatus.APPROVED.value:
            raise ValueError(f"Application must be approved (status: {application.status})")

        job = self._jobs.get_posting_by_id(application.job_id, user_id)
        if not job:
            raise ValueError("Job not found")

        source = self._jobs.get_source_by_id(job.source_id, user_id) if job.source_id else None
        connector_key = resolve_browser_connector_key(source, job)
        connector = self._connectors.get(connector_key)
        profile = self._users.get_profile(user_id)

        stop = (
            stop_before_submit
            if stop_before_submit is not None
            else self._settings.browser_stop_before_submit
        )

        browser_session = self._sessions.get_or_create_session(
            user_id, connector_key, self._settings.playwright_browser
        )

        run = AutomationRun(
            user_id=user_id,
            job_id=job.id,
            application_id=application.id,
            browser_session_id=browser_session.id,
            connector_key=connector_key,
            status=AutomationRunStatus.RUNNING.value,
            browser_name=self._settings.playwright_browser,
            stop_before_submit=stop,
            started_at=datetime.now(timezone.utc),
        )
        run = self._automation.create_run(run)

        context = self._build_context(
            user_id=user_id,
            job=job,
            application=application,
            connector_key=connector_key,
            source=source,
            stop_before_submit=stop,
            profile=profile,
            documents=application.documents or [],
        )

        self._action_logger.log(
            run.id,
            AutomationActionType.SESSION_RESTORE,
            {"session_id": str(browser_session.id), "connector_key": connector_key},
        )

        try:
            result = await self._runner.execute_run(
                profile_path=browser_session.profile_path,
                storage_state_path=self._sessions.restore_storage_state(browser_session),
                headless=self._settings.browser_headless,
                browser_name=self._settings.playwright_browser,
                steps=lambda page, _ctx: self._execute_steps(
                    page, run.id, user_id, connector, context, start_at=0
                ),
            )
            run = self._automation.get_run(run.id, user_id) or run
            return await self._finalize_run(run, result, user_id, job, browser_session)
        except Exception as exc:
            reason = str(exc).strip() or f"{type(exc).__name__}"
            logger.exception("automation_run_failed", run_id=str(run.id), error=reason)
            return await self._fail_run(run, user_id, reason, browser_session)

    async def pause_for_captcha(self, session_id: UUID) -> None:
        logger.info("automation_paused_for_captcha", session_id=str(session_id))

    async def resume_after_captcha(self, session_id: UUID, *, user_id: UUID) -> dict[str, Any]:
        session = self._automation.get_session_by_id(session_id, user_id)
        if not session:
            raise ValueError("Browser session not found")

        run = self._automation.get_paused_run_for_session(session_id, user_id)
        if not run:
            raise ValueError("No paused automation run found for this session")

        application = self._applications.get_by_id(run.application_id, user_id)
        job = self._jobs.get_posting_by_id(run.job_id, user_id)
        if not application or not job:
            raise ValueError("Application or job not found for paused run")

        source = self._jobs.get_source_by_id(job.source_id, user_id) if job.source_id else None
        connector = self._connectors.get(run.connector_key)
        profile = self._users.get_profile(user_id)

        context = self._build_context(
            user_id=user_id,
            job=job,
            application=application,
            connector_key=run.connector_key,
            source=source,
            stop_before_submit=run.stop_before_submit,
            profile=profile,
            documents=application.documents or [],
        )

        run.status = AutomationRunStatus.RUNNING.value
        self._automation.update_run(run)

        start_at = int(run.run_state.get("last_completed_step", -1)) + 1
        self._action_logger.log(
            run.id,
            AutomationActionType.NAVIGATE,
            {"resumed_after_captcha": True, "start_at": start_at},
        )

        try:
            result = await self._runner.execute_run(
                profile_path=session.profile_path,
                storage_state_path=self._sessions.restore_storage_state(session),
                headless=self._settings.browser_headless,
                browser_name=run.browser_name,
                steps=lambda page, _ctx: self._execute_steps(
                    page, run.id, user_id, connector, context, start_at=start_at
                ),
            )
            run = self._automation.get_run(run.id, user_id) or run
            return await self._finalize_run(run, result, user_id, job, session)
        except Exception as exc:
            return await self._fail_run(run, user_id, str(exc), session)

    async def _execute_steps(
        self,
        page: Any,
        run_id: uuid.UUID,
        user_id: uuid.UUID,
        connector: Any,
        context: AutomationContext,
        *,
        start_at: int,
    ) -> dict[str, Any]:
        for index, step_name in enumerate(_STEP_ORDER):
            if index < start_at:
                continue

            if await connector.detect_captcha(page, context):
                screenshot = await self._capture_screenshot(page, run_id, user_id, context.job_id)
                self._action_logger.log(
                    run_id,
                    AutomationActionType.CAPTCHA_DETECTED,
                    {"screenshot": screenshot, "step": step_name},
                )
                run = self._automation.get_run(run_id, user_id)
                if run:
                    run.status = AutomationRunStatus.PAUSED_CAPTCHA.value
                    run.run_state = {"last_completed_step": index - 1, "paused_at_step": step_name}
                    run.result_metadata = {"screenshot": screenshot, "message": "CAPTCHA detected"}
                    self._automation.update_run(run)
                return {
                    "status": AutomationRunStatus.PAUSED_CAPTCHA.value,
                    "paused_for_captcha": True,
                    "run_id": str(run_id),
                    "message": "CAPTCHA detected — resolve manually and call resume endpoint",
                }

            step_fn = getattr(connector, step_name)
            step_result = await step_fn(page, context)
            self._action_logger.log(
                run_id,
                step_name,
                {"success": step_result.success, "message": step_result.message},
            )

            if not step_result.success:
                screenshot = await self._capture_screenshot(page, run_id, user_id, context.job_id)
                return {
                    "status": AutomationRunStatus.FAILED.value,
                    "success": False,
                    "message": step_result.message,
                    "screenshot": screenshot,
                    "step": step_name,
                }

            validation_errors = await connector.detect_validation_errors(page, context)
            if validation_errors:
                screenshot = await self._capture_screenshot(page, run_id, user_id, context.job_id)
                self._action_logger.log(
                    run_id,
                    AutomationActionType.VALIDATION_ERROR,
                    {"errors": validation_errors, "screenshot": screenshot},
                )
                return {
                    "status": AutomationRunStatus.FAILED.value,
                    "success": False,
                    "validation_errors": validation_errors,
                    "screenshot": screenshot,
                    "step": step_name,
                }

            run = self._automation.get_run(run_id, user_id)
            if run:
                run.run_state = {"last_completed_step": index}
                self._automation.update_run(run)

            if step_name == "submit_application" and context.stop_before_submit:
                self._action_logger.log(run_id, AutomationActionType.STOP_BEFORE_SUBMIT, {})
                return {
                    "status": AutomationRunStatus.STOPPED_BEFORE_SUBMIT.value,
                    "success": True,
                    "submitted": False,
                    "message": "Stopped before final submission as configured",
                }

        return {
            "status": AutomationRunStatus.COMPLETED.value,
            "success": True,
            "submitted": not context.stop_before_submit,
        }

    async def _finalize_run(
        self,
        run: AutomationRun,
        result: dict[str, Any],
        user_id: uuid.UUID,
        job: JobPosting,
        session: BrowserSession,
    ) -> dict[str, Any]:
        status = result.get("status", AutomationRunStatus.FAILED.value)
        run.status = status
        run.completed_at = datetime.now(timezone.utc)
        run.result_metadata = result
        run.submitted = bool(result.get("submitted"))

        if status in (AutomationRunStatus.FAILED.value, AutomationRunStatus.PAUSED_CAPTCHA.value):
            run.failure_reason = result.get("message") or str(result.get("validation_errors", ""))
        else:
            run.failure_reason = None

        if status == AutomationRunStatus.COMPLETED.value and run.submitted and self._tracking:
            try:
                self._tracking.record_submission(
                    user_id,
                    job.id,
                    submission_url=job.source_url,
                    submission_method="company_portal",
                    notes="Submitted via Playwright automation (Layer 9)",
                )
                run.submission_recorded_at = datetime.now(timezone.utc)
            except Exception as exc:
                logger.warning("automation_tracking_record_failed", error=str(exc))

        self._automation.update_run(run)
        self._sessions.save_storage_state(session)
        self._sessions.mark_idle(session)

        if self._audit:
            self._audit.record_application_action(
                run.application_id,
                action="browser_automation_complete",
                actor=AuditActor.SYSTEM,
                details={
                    "run_id": str(run.id),
                    "status": status,
                    "connector_key": run.connector_key,
                    "browser": run.browser_name,
                },
            )

        self._action_logger.log(
            run.id,
            AutomationActionType.COMPLETE,
            {"status": status, "submitted": run.submitted},
        )

        return {
            "run_id": str(run.id),
            "session_id": str(session.id),
            "status": status,
            "submitted": run.submitted,
            "connector_key": run.connector_key,
            "browser": run.browser_name,
            "paused_for_captcha": status == AutomationRunStatus.PAUSED_CAPTCHA.value,
            "failure_reason": run.failure_reason,
            "result": result,
        }

    async def _fail_run(
        self,
        run: AutomationRun,
        user_id: uuid.UUID,
        error: str,
        session: BrowserSession,
    ) -> dict[str, Any]:
        run.status = AutomationRunStatus.FAILED.value
        run.failure_reason = error
        run.completed_at = datetime.now(timezone.utc)
        self._automation.update_run(run)
        self._sessions.mark_idle(session)
        self._action_logger.log(run.id, AutomationActionType.ERROR, {"error": error})
        return {
            "run_id": str(run.id),
            "session_id": str(session.id),
            "status": AutomationRunStatus.FAILED.value,
            "success": False,
            "failure_reason": error,
        }

    async def _capture_screenshot(
        self, page: Any, run_id: uuid.UUID, user_id: uuid.UUID, job_id: uuid.UUID
    ) -> str | None:
        try:
            filename = f"failure_{run_id}.png"
            screenshot_dir = self._settings.browser_screenshots_path / str(user_id) / str(job_id)
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            path = screenshot_dir / filename
            if hasattr(page, "screenshot"):
                await page.screenshot(path=str(path), full_page=True)
            else:
                path.write_bytes(b"")
            self._action_logger.log(
                run_id,
                AutomationActionType.SCREENSHOT,
                {"path": str(path)},
            )
            return str(path)
        except Exception as exc:
            logger.warning("screenshot_capture_failed", error=str(exc))
            return None

    def _build_context(
        self,
        *,
        user_id: uuid.UUID,
        job: JobPosting,
        application: JobApplication,
        connector_key: str,
        source: Any,
        stop_before_submit: bool,
        profile: Any,
        documents: list,
    ) -> AutomationContext:
        resume_path = cover_path = None
        email_body = ""
        uploadable = {".pdf", ".doc", ".docx"}
        for doc in documents:
            if doc.document_type == DocumentType.TAILORED_RESUME.value and doc.file_path:
                candidate = Path(doc.file_path)
                if candidate.suffix.lower() in uploadable:
                    resume_path = candidate
            elif doc.document_type == DocumentType.COVER_LETTER.value and doc.file_path:
                cover_path = Path(doc.file_path)
            elif doc.document_type == DocumentType.EMAIL.value:
                email_body = (doc.content or {}).get("body_text", "")

        if not resume_path and application.master_resume_id:
            master = self._resumes.get_master_by_id(application.master_resume_id, user_id)
            if master and master.file_path:
                resume_path = Path(master.file_path)

        profile_fields: dict[str, str] = {}
        if profile:
            profile_fields = {
                "name": profile.legal_name,
                "email": getattr(profile, "email", "") or "",
                "phone": profile.phone,
                "city": profile.location_city,
            }

        return AutomationContext(
            user_id=user_id,
            job_id=job.id,
            application_id=application.id,
            connector_key=connector_key,
            application_url=resolve_application_url(job, source),
            job_title=job.title,
            company=job.company,
            resume_file=resume_path,
            cover_letter_file=cover_path,
            email_body=email_body,
            profile_fields=profile_fields,
            stop_before_submit=stop_before_submit,
            source_config=source.config if source else {},
        )
