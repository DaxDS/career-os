import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from app.infrastructure.db.models import JobPosting, JobSource


class JobRepositoryPort(ABC):
    @abstractmethod
    def get_source_by_id(self, source_id: uuid.UUID, user_id: uuid.UUID) -> JobSource | None: ...

    @abstractmethod
    def get_source_by_preset_key(self, user_id: uuid.UUID, preset_key: str) -> JobSource | None: ...

    @abstractmethod
    def get_source_by_name(self, user_id: uuid.UUID, name: str) -> JobSource | None: ...

    @abstractmethod
    def list_sources(self, user_id: uuid.UUID, active_only: bool = False) -> list[JobSource]: ...

    @abstractmethod
    def create_source(self, source: JobSource) -> JobSource: ...

    @abstractmethod
    def update_source(self, source: JobSource) -> JobSource: ...

    @abstractmethod
    def get_posting_by_id(self, job_id: uuid.UUID, user_id: uuid.UUID) -> JobPosting | None: ...

    @abstractmethod
    def find_by_external_id(
        self, user_id: uuid.UUID, source_id: uuid.UUID, external_id: str
    ) -> JobPosting | None: ...

    @abstractmethod
    def find_by_normalized_url(self, user_id: uuid.UUID, normalized_url: str) -> JobPosting | None: ...

    @abstractmethod
    def find_by_dedup_key(self, user_id: uuid.UUID, dedup_key: str) -> JobPosting | None: ...

    @abstractmethod
    def find_by_description_hash(self, user_id: uuid.UUID, description_hash: str) -> JobPosting | None: ...

    @abstractmethod
    def list_postings(
        self,
        user_id: uuid.UUID,
        *,
        province: str | None = None,
        role_family: str | None = None,
        status: str | None = None,
        source_id: uuid.UUID | None = None,
        exclude_archived: bool = True,
    ) -> list[JobPosting]: ...

    @abstractmethod
    def create_posting(self, posting: JobPosting) -> JobPosting: ...

    @abstractmethod
    def update_posting(self, posting: JobPosting) -> JobPosting: ...

    @abstractmethod
    def touch_source_sync(self, source_id: uuid.UUID, synced_at: datetime) -> None: ...
