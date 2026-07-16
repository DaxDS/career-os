import hashlib
import uuid

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.application.ports.resume_repository import ResumeRepositoryPort
from app.infrastructure.db.models import MasterResume, ResumeVersion


class SQLAlchemyResumeRepository(ResumeRepositoryPort):
    def __init__(self, db: Session):
        self._db = db

    def get_master_by_id(self, resume_id: uuid.UUID, user_id: uuid.UUID) -> MasterResume | None:
        return (
            self._db.query(MasterResume)
            .filter(MasterResume.id == resume_id, MasterResume.user_id == user_id)
            .first()
        )

    def get_master_by_label(self, user_id: uuid.UUID, label: str) -> MasterResume | None:
        return (
            self._db.query(MasterResume)
            .filter(MasterResume.user_id == user_id, MasterResume.label == label)
            .first()
        )

    def list_masters(self, user_id: uuid.UUID, active_only: bool = True) -> list[MasterResume]:
        q = self._db.query(MasterResume).filter(MasterResume.user_id == user_id)
        if active_only:
            q = q.filter(MasterResume.is_active.is_(True))
        return q.order_by(MasterResume.label).all()

    def create_master(self, resume: MasterResume) -> MasterResume:
        self._db.add(resume)
        self._db.commit()
        self._db.refresh(resume)
        return resume

    def update_master(self, resume: MasterResume) -> MasterResume:
        self._db.commit()
        self._db.refresh(resume)
        return resume

    def create_version(self, version: ResumeVersion) -> ResumeVersion:
        self._db.add(version)
        self._db.commit()
        self._db.refresh(version)
        return version

    def list_versions(self, master_resume_id: uuid.UUID) -> list[ResumeVersion]:
        return (
            self._db.query(ResumeVersion)
            .filter(ResumeVersion.master_resume_id == master_resume_id)
            .order_by(desc(ResumeVersion.version_number))
            .all()
        )


def compute_content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
