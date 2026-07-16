import uuid
from datetime import datetime, timezone
from typing import Any, TypedDict

from app.application.ports.audit import AuditPort
from app.application.ports.job_repository import JobRepositoryPort
from app.application.ports.resume_repository import ResumeRepositoryPort
from app.application.ports.score_repository import ScoreRepositoryPort
from app.application.ports.user_repository import UserRepositoryPort
from app.application.services.agents.ats_analysis_agent import AtsAnalysisAgent
from app.application.services.agents.immigration_scoring_agent import ImmigrationScoringAgent
from app.application.services.agents.job_scoring_agent import JobScoringAgent
from app.application.services.agents.resume_selection_agent import ResumeSelectionAgent
from app.config import Settings
from app.domain.enums import JobStatus, WorkflowType
from app.infrastructure.db.models import JobPosting, JobScore
from app.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)


class IntelligenceState(TypedDict, total=False):
    user_id: str
    job_id: str
    workflow_type: str
    immigration: dict[str, Any]
    scoring: dict[str, Any]
    ats: dict[str, Any]
    selection: dict[str, Any]
    job_score_id: str
    errors: list[str]


class JobIntelligenceService:
    """Orchestrates Layer 5 intelligence agents and persists job scores."""

    def __init__(
        self,
        job_repo: JobRepositoryPort,
        user_repo: UserRepositoryPort,
        resume_repo: ResumeRepositoryPort,
        score_repo: ScoreRepositoryPort,
        immigration_agent: ImmigrationScoringAgent,
        scoring_agent: JobScoringAgent,
        ats_agent: AtsAnalysisAgent,
        selection_agent: ResumeSelectionAgent,
        settings: Settings,
        audit: AuditPort | None = None,
    ):
        self._jobs = job_repo
        self._users = user_repo
        self._resumes = resume_repo
        self._scores = score_repo
        self._immigration = immigration_agent
        self._scoring = scoring_agent
        self._ats = ats_agent
        self._selection = selection_agent
        self._settings = settings
        self._audit = audit
        self._graph = self._build_graph()

    def analyze_job(
        self,
        user_id: uuid.UUID,
        job_id: uuid.UUID,
        workflow_type: WorkflowType = WorkflowType.SINGLE_JOB,
    ) -> JobScore:
        if not self._settings.ai_enabled:
            raise ValueError("AI is disabled. Set AI_ENABLED=true and configure API keys.")

        job = self._jobs.get_posting_by_id(job_id, user_id)
        if not job:
            raise ValueError("Job not found")

        if len((job.description or "").strip()) < 80:
            raise ValueError(
                "Job description is missing or too short to score. "
                "Re-run the pipeline after Job Bank is available, or paste the description under Jobs."
            )

        state: IntelligenceState = {
            "user_id": str(user_id),
            "job_id": str(job_id),
            "workflow_type": workflow_type.value,
            "errors": [],
        }
        result = self._graph.invoke(state)
        return self._persist_from_state(user_id, job, result)

    def batch_analyze(self, user_id: uuid.UUID, limit: int = 20) -> list[JobScore]:
        job_ids = self._scores.list_unscored_job_ids(user_id, limit=limit)
        scores: list[JobScore] = []
        for job_id in job_ids:
            try:
                scores.append(
                    self.analyze_job(user_id, job_id, workflow_type=WorkflowType.BATCH_INTELLIGENCE)
                )
            except Exception as exc:
                logger.warning("batch_analyze_job_failed", job_id=str(job_id), error=str(exc))
        return scores

    def get_scores(self, user_id: uuid.UUID, job_id: uuid.UUID) -> JobScore:
        score = self._scores.get_by_job(user_id, job_id)
        if not score:
            raise ValueError("Job scores not found")
        return score

    def list_ranked(
        self,
        user_id: uuid.UUID,
        *,
        min_overall_score: int | None = None,
        province: str | None = None,
        role_family: str | None = None,
        limit: int = 50,
    ) -> list[tuple[JobScore, JobPosting]]:
        return self._scores.list_ranked(
            user_id,
            min_overall_score=min_overall_score,
            province=province,
            role_family=role_family,
            limit=limit,
        )

    def _build_graph(self):
        from langgraph.graph import END, StateGraph

        graph = StateGraph(IntelligenceState)
        graph.add_node("immigration", self._node_immigration)
        graph.add_node("scoring", self._node_scoring)
        graph.add_node("ats", self._node_ats)
        graph.add_node("selection", self._node_selection)
        graph.set_entry_point("immigration")
        graph.add_edge("immigration", "scoring")
        graph.add_edge("scoring", "ats")
        graph.add_edge("ats", "selection")
        graph.add_edge("selection", END)
        return graph.compile()

    def _node_immigration(self, state: IntelligenceState) -> IntelligenceState:
        user_id = uuid.UUID(state["user_id"])
        job_id = uuid.UUID(state["job_id"])
        job, profile, _ = self._load_context(user_id, job_id)
        try:
            state["immigration"] = self._immigration.score(user_id, job, profile)
        except Exception as exc:
            state.setdefault("errors", []).append(f"immigration: {exc}")
            state["immigration"] = {}
        return state

    def _node_scoring(self, state: IntelligenceState) -> IntelligenceState:
        user_id = uuid.UUID(state["user_id"])
        job_id = uuid.UUID(state["job_id"])
        job, profile, _ = self._load_context(user_id, job_id)
        try:
            state["scoring"] = self._scoring.score(user_id, job, profile)
        except Exception as exc:
            state.setdefault("errors", []).append(f"scoring: {exc}")
            state["scoring"] = {}
        return state

    def _node_ats(self, state: IntelligenceState) -> IntelligenceState:
        user_id = uuid.UUID(state["user_id"])
        job_id = uuid.UUID(state["job_id"])
        job, profile, resumes = self._load_context(user_id, job_id)
        try:
            state["ats"] = self._ats.analyze(user_id, job, profile, resumes)
        except Exception as exc:
            state.setdefault("errors", []).append(f"ats: {exc}")
            state["ats"] = {}
        return state

    def _node_selection(self, state: IntelligenceState) -> IntelligenceState:
        user_id = uuid.UUID(state["user_id"])
        job_id = uuid.UUID(state["job_id"])
        job, profile, resumes = self._load_context(user_id, job_id)
        try:
            state["selection"] = self._selection.select(user_id, job, profile, resumes)
        except Exception as exc:
            state.setdefault("errors", []).append(f"selection: {exc}")
            state["selection"] = {}
        return state

    def _load_context(self, user_id: uuid.UUID, job_id: uuid.UUID):
        job = self._jobs.get_posting_by_id(job_id, user_id)
        if not job:
            raise ValueError("Job not found")
        profile = self._users.get_profile(user_id)
        if not profile:
            raise ValueError("User profile not found")
        resumes = self._resumes.list_masters(user_id)
        return job, profile, resumes

    def _persist_from_state(
        self, user_id: uuid.UUID, job: JobPosting, state: IntelligenceState
    ) -> JobScore:
        immigration = state.get("immigration") or {}
        scoring = state.get("scoring") or {}
        ats = state.get("ats") or {}
        selection = state.get("selection") or {}

        ats_score = scoring.get("ats_score") or ats.get("ats_score")
        match_score = scoring.get("match_score")
        pr_score = scoring.get("pr_score")
        immigration_score = immigration.get("immigration_score")
        overall = scoring.get("overall_score")
        if overall is None and any(
            s is not None for s in (ats_score, match_score, immigration_score, pr_score)
        ):
            parts = [s for s in (ats_score, match_score, immigration_score, pr_score) if s is not None]
            overall = round(sum(parts) / len(parts))

        selected_resume_id = selection.get("selected_resume_id")
        try:
            resume_uuid = uuid.UUID(str(selected_resume_id)) if selected_resume_id else None
        except (ValueError, TypeError):
            resume_uuid = None

        score = JobScore(
            user_id=user_id,
            job_id=job.id,
            ats_score=ats_score,
            match_score=match_score,
            immigration_score=immigration_score,
            pr_score=pr_score,
            overall_score=overall,
            selected_master_resume_id=resume_uuid,
            resume_selection_confidence=selection.get("confidence"),
            immigration_details=immigration,
            ats_details=ats,
            match_details={
                "score_breakdown": scoring.get("score_breakdown", {}),
                "rationale": scoring.get("rationale", ""),
                "red_flags": scoring.get("red_flags", []),
                "green_flags": scoring.get("green_flags", []),
            },
            selection_details=selection,
            scoring_method="llm" if not state.get("errors") else "partial",
            agent_metadata={
                "workflow_type": state.get("workflow_type"),
                "errors": state.get("errors", []),
            },
            scored_at=datetime.now(timezone.utc),
        )
        score = self._scores.upsert(score)

        job.status = JobStatus.SCORED.value
        self._jobs.update_posting(job)

        logger.info(
            "job_intelligence_complete",
            job_id=str(job.id),
            overall_score=overall,
            errors=state.get("errors", []),
        )
        return score
