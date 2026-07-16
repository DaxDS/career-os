import uuid
from abc import ABC, abstractmethod

from app.infrastructure.db.models import MasterResume, ResumeVersion


class ResumeRepositoryPort(ABC):
    @abstractmethod
    def get_master_by_id(self, resume_id: uuid.UUID, user_id: uuid.UUID) -> MasterResume | None: ...

    @abstractmethod
    def get_master_by_label(self, user_id: uuid.UUID, label: str) -> MasterResume | None: ...

    @abstractmethod
    def list_masters(self, user_id: uuid.UUID, active_only: bool = True) -> list[MasterResume]: ...

    @abstractmethod
    def create_master(self, resume: MasterResume) -> MasterResume: ...

    @abstractmethod
    def update_master(self, resume: MasterResume) -> MasterResume: ...

    @abstractmethod
    def create_version(self, version: ResumeVersion) -> ResumeVersion: ...

    @abstractmethod
    def list_versions(self, master_resume_id: uuid.UUID) -> list[ResumeVersion]: ...
