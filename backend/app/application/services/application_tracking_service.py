import uuid
from datetime import datetime, timezone

from app.application.ports.application_repository import ApplicationRepositoryPort
from app.application.ports.audit import AuditPort
from app.application.ports.job_repository import JobRepositoryPort
from app.application.ports.storage import FileStoragePort
from app.domain.enums import (
    ApplicationStatus,
    AuditActor,
    JobStatus,
    StorageCategory,
    SubmissionMethod,
)
from app.infrastructure.db.models import ApplicationScreenshot, JobApplication, JobPosting
from app.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)

_APPROVABLE = {ApplicationStatus.GENERATED.value}
_SUBMITTABLE = {ApplicationStatus.APPROVED.value}
_WITHDRAWABLE = {
    ApplicationStatus.GENERATED.value,
    ApplicationStatus.APPROVED.value,
    ApplicationStatus.SUBMITTED.value,
    ApplicationStatus.FAILED.value,
}


class ApplicationTrackingService:
    """Layer 7 — user approval, manual submission tracking, and screenshots."""

    def __init__(
        self,
        application_repo: ApplicationRepositoryPort,
        job_repo: JobRepositoryPort,
        storage: FileStoragePort,
        audit: AuditPort | None = None,
    ):
        self._applications = application_repo
        self._jobs = job_repo
        self._storage = storage
        self._audit = audit

    def get_tracking(self, user_id: uuid.UUID, job_id: uuid.UUID) -> JobApplication:
        application = self._applications.get_by_job(user_id, job_id)
        if not application:
            raise ValueError("Application not found — generate documents first (Layer 6)")
        return application

    def list_applications(
        self,
        user_id: uuid.UUID,
        *,
        status: str | None = None,
        limit: int = 50,
    ) -> list[tuple[JobApplication, JobPosting]]:
        if status:
            self._validate_application_status(status)
        return self._applications.list_with_jobs(user_id, status=status, limit=limit)

    def approve(
        self,
        user_id: uuid.UUID,
        job_id: uuid.UUID,
        *,
        approved: bool = True,
        notes: str = "",
    ) -> JobApplication:
        application = self.get_tracking(user_id, job_id)

        if approved:
            if application.status not in _APPROVABLE:
                raise ValueError(
                    f"Cannot approve application in status '{application.status}'"
                )
            application.status = ApplicationStatus.APPROVED.value
            application.approved_at = datetime.now(timezone.utc)
        else:
            if application.status != ApplicationStatus.APPROVED.value:
                raise ValueError("Can only revoke approval from approved applications")
            application.status = ApplicationStatus.GENERATED.value
            application.approved_at = None

        application = self._applications.update(application)

        if self._audit:
            self._audit.record_user_approval(
                application.id,
                approved=approved,
                details={"job_id": str(job_id), "notes": notes},
            )
            self._audit.record_application_action(
                application.id,
                action="approved" if approved else "approval_revoked",
                actor=AuditActor.USER,
                details={"job_id": str(job_id), "notes": notes},
            )

        logger.info(
            "application_approval",
            application_id=str(application.id),
            approved=approved,
        )
        return application

    def record_submission(
        self,
        user_id: uuid.UUID,
        job_id: uuid.UUID,
        *,
        submission_url: str = "",
        submission_method: str = SubmissionMethod.MANUAL.value,
        notes: str = "",
        success: bool = True,
    ) -> JobApplication:
        application = self.get_tracking(user_id, job_id)
        if application.status not in _SUBMITTABLE:
            raise ValueError(
                f"Application must be approved before submission (current: {application.status})"
            )

        self._validate_submission_method(submission_method)
        now = datetime.now(timezone.utc)

        if success:
            application.status = ApplicationStatus.SUBMITTED.value
            application.submitted_at = now
            application.submission_url = submission_url
            application.submission_method = submission_method
            application.submission_notes = notes
            self._mark_job_applied(user_id, job_id)
        else:
            application.status = ApplicationStatus.FAILED.value
            application.submission_notes = notes

        application = self._applications.update(application)

        if self._audit:
            self._audit.record_application_action(
                application.id,
                action="submitted" if success else "submission_failed",
                actor=AuditActor.USER,
                details={
                    "job_id": str(job_id),
                    "submission_url": submission_url,
                    "submission_method": submission_method,
                    "notes": notes,
                },
            )

        logger.info(
            "application_submission_recorded",
            application_id=str(application.id),
            success=success,
            method=submission_method,
        )
        return application

    def withdraw(self, user_id: uuid.UUID, job_id: uuid.UUID, *, notes: str = "") -> JobApplication:
        application = self.get_tracking(user_id, job_id)
        if application.status not in _WITHDRAWABLE:
            raise ValueError(f"Cannot withdraw application in status '{application.status}'")

        application.status = ApplicationStatus.WITHDRAWN.value
        application.submission_notes = notes or application.submission_notes
        application = self._applications.update(application)

        if self._audit:
            self._audit.record_application_action(
                application.id,
                action="withdrawn",
                actor=AuditActor.USER,
                details={"job_id": str(job_id), "notes": notes},
            )
        return application

    def upload_screenshot(
        self,
        user_id: uuid.UUID,
        job_id: uuid.UUID,
        *,
        filename: str,
        content: bytes,
        caption: str = "",
    ) -> ApplicationScreenshot:
        application = self.get_tracking(user_id, job_id)
        if not filename:
            raise ValueError("Filename is required")

        path = self._storage.save(
            StorageCategory.SCREENSHOT,
            filename,
            content,
            application_id=application.id,
        )
        screenshot = ApplicationScreenshot(
            application_id=application.id,
            file_path=str(path),
            original_filename=filename,
            caption=caption,
            captured_at=datetime.now(timezone.utc),
        )
        screenshot = self._applications.add_screenshot(screenshot)

        if self._audit:
            self._audit.record_application_action(
                application.id,
                action="screenshot_uploaded",
                actor=AuditActor.USER,
                details={
                    "job_id": str(job_id),
                    "filename": filename,
                    "caption": caption,
                },
            )

        logger.info(
            "screenshot_uploaded",
            application_id=str(application.id),
            filename=filename,
        )
        return screenshot

    def _mark_job_applied(self, user_id: uuid.UUID, job_id: uuid.UUID) -> None:
        job = self._jobs.get_posting_by_id(job_id, user_id)
        if job and job.status != JobStatus.ARCHIVED.value:
            job.status = JobStatus.APPLIED.value
            self._jobs.update_posting(job)

    @staticmethod
    def _validate_application_status(status: str) -> None:
        valid = {s.value for s in ApplicationStatus}
        if status not in valid:
            raise ValueError(f"Invalid application status: {status}")

    @staticmethod
    def _validate_submission_method(method: str) -> None:
        valid = {s.value for s in SubmissionMethod}
        if method not in valid:
            raise ValueError(f"Invalid submission method: {method}")
