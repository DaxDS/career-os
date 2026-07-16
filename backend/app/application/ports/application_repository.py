import uuid
from abc import ABC, abstractmethod

from app.infrastructure.db.models import (
    ApplicationDocument,
    ApplicationScreenshot,
    JobApplication,
    JobPosting,
)


class ApplicationRepositoryPort(ABC):
    @abstractmethod
    def get_by_job(self, user_id: uuid.UUID, job_id: uuid.UUID) -> JobApplication | None: ...

    @abstractmethod
    def get_by_id(self, application_id: uuid.UUID, user_id: uuid.UUID) -> JobApplication | None: ...

    @abstractmethod
    def upsert(self, application: JobApplication) -> JobApplication: ...

    @abstractmethod
    def update(self, application: JobApplication) -> JobApplication: ...

    @abstractmethod
    def list_by_user(
        self,
        user_id: uuid.UUID,
        *,
        status: str | None = None,
        limit: int = 50,
    ) -> list[JobApplication]: ...

    @abstractmethod
    def upsert_document(self, document: ApplicationDocument) -> ApplicationDocument: ...

    @abstractmethod
    def list_documents(self, application_id: uuid.UUID) -> list[ApplicationDocument]: ...

    @abstractmethod
    def get_document(
        self, application_id: uuid.UUID, document_type: str
    ) -> ApplicationDocument | None: ...

    @abstractmethod
    def add_screenshot(self, screenshot: ApplicationScreenshot) -> ApplicationScreenshot: ...

    @abstractmethod
    def list_screenshots(self, application_id: uuid.UUID) -> list[ApplicationScreenshot]: ...

    @abstractmethod
    def list_with_jobs(
        self,
        user_id: uuid.UUID,
        *,
        status: str | None = None,
        limit: int = 50,
    ) -> list[tuple[JobApplication, JobPosting]]: ...

    @abstractmethod
    def count_by_status(self, user_id: uuid.UUID, status: str) -> int: ...
