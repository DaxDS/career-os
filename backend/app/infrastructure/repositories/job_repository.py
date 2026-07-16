import uuid
from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.application.ports.job_repository import JobRepositoryPort
from app.domain.enums import JobStatus
from app.infrastructure.db.models import JobPosting, JobSource


class SQLAlchemyJobRepository(JobRepositoryPort):
    def __init__(self, db: Session):
        self._db = db

    def get_source_by_id(self, source_id: uuid.UUID, user_id: uuid.UUID) -> JobSource | None:
        return (
            self._db.query(JobSource)
            .filter(JobSource.id == source_id, JobSource.user_id == user_id)
            .first()
        )

    def get_source_by_preset_key(self, user_id: uuid.UUID, preset_key: str) -> JobSource | None:
        return (
            self._db.query(JobSource)
            .filter(JobSource.user_id == user_id, JobSource.preset_key == preset_key)
            .first()
        )

    def get_source_by_name(self, user_id: uuid.UUID, name: str) -> JobSource | None:
        return (
            self._db.query(JobSource)
            .filter(JobSource.user_id == user_id, JobSource.name == name)
            .first()
        )

    def list_sources(self, user_id: uuid.UUID, active_only: bool = False) -> list[JobSource]:
        q = self._db.query(JobSource).filter(JobSource.user_id == user_id)
        if active_only:
            q = q.filter(JobSource.is_active.is_(True))
        return q.order_by(JobSource.name).all()

    def create_source(self, source: JobSource) -> JobSource:
        self._db.add(source)
        self._db.commit()
        self._db.refresh(source)
        return source

    def update_source(self, source: JobSource) -> JobSource:
        self._db.commit()
        self._db.refresh(source)
        return source

    def get_posting_by_id(self, job_id: uuid.UUID, user_id: uuid.UUID) -> JobPosting | None:
        return (
            self._db.query(JobPosting)
            .filter(JobPosting.id == job_id, JobPosting.user_id == user_id)
            .first()
        )

    def find_by_external_id(
        self, user_id: uuid.UUID, source_id: uuid.UUID, external_id: str
    ) -> JobPosting | None:
        return (
            self._db.query(JobPosting)
            .filter(
                JobPosting.user_id == user_id,
                JobPosting.source_id == source_id,
                JobPosting.external_id == external_id,
            )
            .first()
        )

    def find_by_normalized_url(self, user_id: uuid.UUID, normalized_url: str) -> JobPosting | None:
        if not normalized_url:
            return None
        return (
            self._db.query(JobPosting)
            .filter(JobPosting.user_id == user_id, JobPosting.normalized_url == normalized_url)
            .first()
        )

    def find_by_dedup_key(self, user_id: uuid.UUID, dedup_key: str) -> JobPosting | None:
        return (
            self._db.query(JobPosting)
            .filter(JobPosting.user_id == user_id, JobPosting.dedup_key == dedup_key)
            .first()
        )

    def find_by_description_hash(self, user_id: uuid.UUID, description_hash: str) -> JobPosting | None:
        return (
            self._db.query(JobPosting)
            .filter(JobPosting.user_id == user_id, JobPosting.description_hash == description_hash)
            .first()
        )

    def list_postings(
        self,
        user_id: uuid.UUID,
        *,
        province: str | None = None,
        role_family: str | None = None,
        status: str | None = None,
        source_id: uuid.UUID | None = None,
        exclude_archived: bool = True,
    ) -> list[JobPosting]:
        q = self._db.query(JobPosting).filter(JobPosting.user_id == user_id)
        if exclude_archived:
            q = q.filter(JobPosting.status != JobStatus.ARCHIVED.value)
        if province:
            q = q.filter(JobPosting.location_province == province.upper())
        if role_family:
            q = q.filter(JobPosting.role_family == role_family)
        if status:
            q = q.filter(JobPosting.status == status)
        if source_id:
            q = q.filter(JobPosting.source_id == source_id)
        return q.order_by(desc(JobPosting.date_found)).all()

    def create_posting(self, posting: JobPosting) -> JobPosting:
        self._db.add(posting)
        self._db.commit()
        self._db.refresh(posting)
        return posting

    def update_posting(self, posting: JobPosting) -> JobPosting:
        self._db.commit()
        self._db.refresh(posting)
        return posting

    def touch_source_sync(self, source_id: uuid.UUID, synced_at: datetime) -> None:
        source = self._db.query(JobSource).filter(JobSource.id == source_id).first()
        if source:
            source.last_synced_at = synced_at
            self._db.commit()
