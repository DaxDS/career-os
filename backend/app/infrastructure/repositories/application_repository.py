import uuid

from sqlalchemy.orm import Session, joinedload

from app.application.ports.application_repository import ApplicationRepositoryPort
from app.infrastructure.db.models import (
    ApplicationDocument,
    ApplicationScreenshot,
    JobApplication,
    JobPosting,
)


class SQLAlchemyApplicationRepository(ApplicationRepositoryPort):
    def __init__(self, db: Session):
        self._db = db

    def get_by_job(self, user_id: uuid.UUID, job_id: uuid.UUID) -> JobApplication | None:
        return (
            self._db.query(JobApplication)
            .options(
                joinedload(JobApplication.documents),
                joinedload(JobApplication.screenshots),
                joinedload(JobApplication.job),
            )
            .filter(JobApplication.user_id == user_id, JobApplication.job_id == job_id)
            .first()
        )

    def get_by_id(self, application_id: uuid.UUID, user_id: uuid.UUID) -> JobApplication | None:
        return (
            self._db.query(JobApplication)
            .options(
                joinedload(JobApplication.documents),
                joinedload(JobApplication.screenshots),
                joinedload(JobApplication.job),
            )
            .filter(JobApplication.id == application_id, JobApplication.user_id == user_id)
            .first()
        )

    def upsert(self, application: JobApplication) -> JobApplication:
        existing = self.get_by_job(application.user_id, application.job_id)
        if existing:
            existing.master_resume_id = application.master_resume_id
            existing.status = application.status
            existing.version = application.version
            existing.ats_fact_check_passed = application.ats_fact_check_passed
            existing.generation_metadata = application.generation_metadata
            existing.generated_at = application.generated_at
            existing.review_notes = application.review_notes
            existing.reviewed_at = application.reviewed_at
            existing.approved_at = application.approved_at
            existing.submitted_at = application.submitted_at
            existing.submission_url = application.submission_url
            existing.submission_method = application.submission_method
            existing.submission_notes = application.submission_notes
            self._db.commit()
            self._db.refresh(existing)
            return existing

        self._db.add(application)
        self._db.commit()
        self._db.refresh(application)
        return application

    def update(self, application: JobApplication) -> JobApplication:
        self._db.commit()
        self._db.refresh(application)
        return application

    def list_by_user(
        self,
        user_id: uuid.UUID,
        *,
        status: str | None = None,
        limit: int = 50,
    ) -> list[JobApplication]:
        query = (
            self._db.query(JobApplication)
            .options(
                joinedload(JobApplication.documents),
                joinedload(JobApplication.screenshots),
            )
            .filter(JobApplication.user_id == user_id)
            .order_by(JobApplication.updated_at.desc())
        )
        if status:
            query = query.filter(JobApplication.status == status)
        return query.limit(limit).all()

    def upsert_document(self, document: ApplicationDocument) -> ApplicationDocument:
        existing = (
            self._db.query(ApplicationDocument)
            .filter(
                ApplicationDocument.application_id == document.application_id,
                ApplicationDocument.document_type == document.document_type,
            )
            .first()
        )
        if existing:
            existing.file_path = document.file_path
            existing.content = document.content
            existing.version = document.version
            self._db.commit()
            self._db.refresh(existing)
            return existing

        self._db.add(document)
        self._db.commit()
        self._db.refresh(document)
        return document

    def list_documents(self, application_id: uuid.UUID) -> list[ApplicationDocument]:
        return (
            self._db.query(ApplicationDocument)
            .filter(ApplicationDocument.application_id == application_id)
            .order_by(ApplicationDocument.document_type)
            .all()
        )

    def get_document(
        self, application_id: uuid.UUID, document_type: str
    ) -> ApplicationDocument | None:
        return (
            self._db.query(ApplicationDocument)
            .filter(
                ApplicationDocument.application_id == application_id,
                ApplicationDocument.document_type == document_type,
            )
            .first()
        )

    def add_screenshot(self, screenshot: ApplicationScreenshot) -> ApplicationScreenshot:
        self._db.add(screenshot)
        self._db.commit()
        self._db.refresh(screenshot)
        return screenshot

    def list_screenshots(self, application_id: uuid.UUID) -> list[ApplicationScreenshot]:
        return (
            self._db.query(ApplicationScreenshot)
            .filter(ApplicationScreenshot.application_id == application_id)
            .order_by(ApplicationScreenshot.created_at.desc())
            .all()
        )

    def list_with_jobs(
        self,
        user_id: uuid.UUID,
        *,
        status: str | None = None,
        limit: int = 50,
    ) -> list[tuple[JobApplication, JobPosting]]:
        query = (
            self._db.query(JobApplication)
            .options(
                joinedload(JobApplication.documents),
                joinedload(JobApplication.screenshots),
                joinedload(JobApplication.job),
            )
            .filter(JobApplication.user_id == user_id)
            .order_by(JobApplication.updated_at.desc())
        )
        if status:
            query = query.filter(JobApplication.status == status)
        applications = query.limit(limit).all()
        return [(app, app.job) for app in applications if app.job]

    def count_by_status(self, user_id: uuid.UUID, status: str) -> int:
        return (
            self._db.query(JobApplication)
            .filter(JobApplication.user_id == user_id, JobApplication.status == status)
            .count()
        )
