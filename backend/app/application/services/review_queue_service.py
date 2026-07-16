import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.application.ports.application_repository import ApplicationRepositoryPort
from app.application.ports.audit import AuditPort
from app.application.ports.score_repository import ScoreRepositoryPort
from app.application.services.application_tracking_service import ApplicationTrackingService
from app.domain.enums import (
    ApplicationStatus,
    AuditActor,
    DocumentType,
    ReviewDecision,
)
from app.infrastructure.db.models import JobApplication, JobPosting, JobScore
from app.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)

_REVIEWABLE = {ApplicationStatus.GENERATED.value}


@dataclass
class ReviewQueueItem:
    application_id: uuid.UUID
    job_id: uuid.UUID
    title: str
    company: str
    location_province: str
    overall_score: int | None
    ats_fact_check_passed: bool | None
    resume_summary_preview: str
    cover_letter_preview: str
    generated_at: datetime
    version: int
    match_score: int | None = None
    ats_score: int | None = None
    immigration_score: int | None = None


@dataclass
class ReviewDetail:
    application: JobApplication
    job: JobPosting
    score: JobScore | None
    document_previews: dict[str, Any]


@dataclass
class BatchReviewResult:
    job_id: uuid.UUID
    success: bool
    status: str | None = None
    error: str | None = None


class ReviewQueueService:
    """Layer 8 — centralized review queue before application approval."""

    def __init__(
        self,
        application_repo: ApplicationRepositoryPort,
        score_repo: ScoreRepositoryPort,
        tracking_service: ApplicationTrackingService,
        audit: AuditPort | None = None,
    ):
        self._applications = application_repo
        self._scores = score_repo
        self._tracking = tracking_service
        self._audit = audit

    def get_queue(
        self,
        user_id: uuid.UUID,
        *,
        min_overall_score: int | None = None,
        limit: int = 50,
    ) -> list[ReviewQueueItem]:
        rows = self._applications.list_with_jobs(
            user_id,
            status=ApplicationStatus.GENERATED.value,
            limit=limit,
        )
        items: list[ReviewQueueItem] = []
        for application, job in rows:
            score = self._scores.get_by_job(user_id, job.id)
            if min_overall_score is not None:
                if not score or score.overall_score is None:
                    continue
                if score.overall_score < min_overall_score:
                    continue
            items.append(self._to_queue_item(application, job, score))
        return items

    def get_stats(self, user_id: uuid.UUID) -> dict[str, int]:
        return {
            "pending_review": self._applications.count_by_status(
                user_id, ApplicationStatus.GENERATED.value
            ),
            "revision_requested": self._applications.count_by_status(
                user_id, ApplicationStatus.REVISION_REQUESTED.value
            ),
            "rejected": self._applications.count_by_status(
                user_id, ApplicationStatus.REJECTED.value
            ),
            "approved": self._applications.count_by_status(
                user_id, ApplicationStatus.APPROVED.value
            ),
        }

    def get_review_detail(self, user_id: uuid.UUID, job_id: uuid.UUID) -> ReviewDetail:
        application = self._applications.get_by_job(user_id, job_id)
        if not application:
            raise ValueError("Application not found — generate documents first (Layer 6)")
        job = application.job
        if not job:
            raise ValueError("Job not found")
        score = self._scores.get_by_job(user_id, job_id)
        return ReviewDetail(
            application=application,
            job=job,
            score=score,
            document_previews=self._document_previews(application),
        )

    def decide(
        self,
        user_id: uuid.UUID,
        job_id: uuid.UUID,
        decision: ReviewDecision,
        *,
        notes: str = "",
    ) -> JobApplication:
        application = self._applications.get_by_job(user_id, job_id)
        if not application:
            raise ValueError("Application not found")
        if application.status not in _REVIEWABLE:
            raise ValueError(
                f"Application is not pending review (status: {application.status})"
            )

        if decision == ReviewDecision.APPROVE:
            application.review_notes = notes
            application.reviewed_at = datetime.now(timezone.utc)
            self._applications.update(application)
            if self._audit:
                self._audit.record_user_approval(
                    application.id,
                    approved=True,
                    details={"job_id": str(job_id), "notes": notes, "via": "review_queue"},
                )
                self._audit.record_application_action(
                    application.id,
                    action="review_approved",
                    actor=AuditActor.USER,
                    details={"job_id": str(job_id), "notes": notes},
                )
            return self._tracking.approve(user_id, job_id, approved=True, notes=notes)

        application.review_notes = notes
        application.reviewed_at = datetime.now(timezone.utc)

        if decision == ReviewDecision.REJECT:
            application.status = ApplicationStatus.REJECTED.value
            action = "review_rejected"
        else:
            application.status = ApplicationStatus.REVISION_REQUESTED.value
            action = "revision_requested"

        application = self._applications.update(application)

        if self._audit:
            self._audit.record_user_approval(
                application.id,
                approved=False,
                details={
                    "job_id": str(job_id),
                    "notes": notes,
                    "decision": decision.value,
                },
            )
            self._audit.record_application_action(
                application.id,
                action=action,
                actor=AuditActor.USER,
                details={"job_id": str(job_id), "notes": notes},
            )

        logger.info(
            "review_decision",
            job_id=str(job_id),
            decision=decision.value,
        )
        return application

    def batch_decide(
        self,
        user_id: uuid.UUID,
        job_ids: list[uuid.UUID],
        decision: ReviewDecision,
        *,
        notes: str = "",
    ) -> list[BatchReviewResult]:
        results: list[BatchReviewResult] = []
        for job_id in job_ids:
            try:
                application = self.decide(user_id, job_id, decision, notes=notes)
                results.append(
                    BatchReviewResult(
                        job_id=job_id,
                        success=True,
                        status=application.status,
                    )
                )
            except ValueError as exc:
                results.append(
                    BatchReviewResult(job_id=job_id, success=False, error=str(exc))
                )
        return results

    def _to_queue_item(
        self,
        application: JobApplication,
        job: JobPosting,
        score: JobScore | None,
    ) -> ReviewQueueItem:
        previews = self._document_previews(application)
        return ReviewQueueItem(
            application_id=application.id,
            job_id=job.id,
            title=job.title,
            company=job.company,
            location_province=job.location_province,
            overall_score=score.overall_score if score else None,
            match_score=score.match_score if score else None,
            ats_score=score.ats_score if score else None,
            immigration_score=score.immigration_score if score else None,
            ats_fact_check_passed=application.ats_fact_check_passed,
            resume_summary_preview=previews.get("resume_summary", ""),
            cover_letter_preview=previews.get("cover_letter_excerpt", ""),
            generated_at=application.generated_at,
            version=application.version,
        )

    @staticmethod
    def _document_previews(application: JobApplication) -> dict[str, Any]:
        previews: dict[str, Any] = {
            "resume_summary": "",
            "cover_letter_excerpt": "",
            "email_subject": "",
            "ats_score": None,
            "fact_check_passed": application.ats_fact_check_passed,
        }
        for doc in application.documents or []:
            content = doc.content or {}
            if doc.document_type == DocumentType.TAILORED_RESUME.value:
                previews["resume_summary"] = (content.get("summary") or "")[:300]
            elif doc.document_type == DocumentType.COVER_LETTER.value:
                text = content.get("full_text") or ""
                previews["cover_letter_excerpt"] = text[:300]
            elif doc.document_type == DocumentType.EMAIL.value:
                previews["email_subject"] = content.get("subject", "")
            elif doc.document_type == DocumentType.ATS_REPORT.value:
                previews["ats_score"] = content.get("ats_score")
                fact_check = content.get("fact_check", {})
                if isinstance(fact_check, dict) and fact_check.get("passed") is not None:
                    previews["fact_check_passed"] = fact_check.get("passed")
        return previews
