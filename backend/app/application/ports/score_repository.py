import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from app.infrastructure.db.models import AgentRun, JobScore

if TYPE_CHECKING:
    from app.infrastructure.db.models import JobPosting


class ScoreRepositoryPort(ABC):
    @abstractmethod
    def get_by_job(self, user_id: uuid.UUID, job_id: uuid.UUID) -> JobScore | None: ...

    @abstractmethod
    def list_for_jobs(
        self, user_id: uuid.UUID, job_ids: list[uuid.UUID]
    ) -> list[JobScore]: ...

    @abstractmethod
    def upsert(self, score: JobScore) -> JobScore: ...

    @abstractmethod
    def list_ranked(
        self,
        user_id: uuid.UUID,
        *,
        min_overall_score: int | None = None,
        province: str | None = None,
        role_family: str | None = None,
        limit: int = 50,
    ) -> list[tuple[JobScore, "JobPosting"]]: ...

    @abstractmethod
    def list_unscored_job_ids(self, user_id: uuid.UUID, limit: int = 20) -> list[uuid.UUID]: ...


class AgentRunRepositoryPort(ABC):
    @abstractmethod
    def create(self, run: AgentRun) -> AgentRun: ...

    @abstractmethod
    def complete(
        self,
        run_id: uuid.UUID,
        *,
        status: str,
        output: dict,
        error_message: str | None = None,
        llm_provider: str | None = None,
        llm_model: str | None = None,
    ) -> AgentRun: ...

    @abstractmethod
    def list_for_job(self, user_id: uuid.UUID, job_id: uuid.UUID) -> list[AgentRun]: ...
