import json
import uuid
from datetime import datetime, timezone
from typing import Any, TypedDict

from app.application.ports.application_repository import ApplicationRepositoryPort
from app.application.ports.audit import AuditPort
from app.application.ports.job_repository import JobRepositoryPort
from app.application.ports.resume_repository import ResumeRepositoryPort
from app.application.ports.score_repository import ScoreRepositoryPort
from app.application.ports.storage import FileStoragePort
from app.application.ports.user_repository import UserRepositoryPort
from app.application.services.agents.ats_analysis_agent import AtsAnalysisAgent
from app.application.services.agents.cover_letter_agent import CoverLetterAgent
from app.application.services.agents.email_generation_agent import EmailGenerationAgent
from app.application.services.agents.resume_tailoring_agent import ResumeTailoringAgent
from app.config import Settings
from app.domain.enums import (
    ApplicationStatus,
    AuditActor,
    DocumentType,
    JobStatus,
    StorageCategory,
    WorkflowType,
)
from app.infrastructure.db.models import (
    ApplicationDocument,
    JobApplication,
    JobPosting,
    MasterResume,
)
from app.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)

_DOC_STORAGE: dict[str, tuple[StorageCategory, str]] = {
    DocumentType.TAILORED_RESUME.value: (StorageCategory.RESUME_VERSION, "TailoredResume.json"),
    DocumentType.COVER_LETTER.value: (StorageCategory.COVER_LETTER, "CoverLetter.txt"),
    DocumentType.EMAIL.value: (StorageCategory.EMAIL, "Email.txt"),
    DocumentType.ATS_REPORT.value: (StorageCategory.REPORT, "ATSReport.json"),
}


class DocumentState(TypedDict, total=False):
    user_id: str
    job_id: str
    master_resume_id: str
    force: bool
    tailored: dict[str, Any]
    ats: dict[str, Any]
    cover_letter: dict[str, Any]
    email: dict[str, Any]
    errors: list[str]


class DocumentGenerationService:
    """Orchestrates Layer 6 document generation and artifact persistence."""

    def __init__(
        self,
        job_repo: JobRepositoryPort,
        user_repo: UserRepositoryPort,
        resume_repo: ResumeRepositoryPort,
        score_repo: ScoreRepositoryPort,
        application_repo: ApplicationRepositoryPort,
        storage: FileStoragePort,
        tailoring_agent: ResumeTailoringAgent,
        ats_agent: AtsAnalysisAgent,
        cover_letter_agent: CoverLetterAgent,
        email_agent: EmailGenerationAgent,
        settings: Settings,
        audit: AuditPort | None = None,
    ):
        self._jobs = job_repo
        self._users = user_repo
        self._resumes = resume_repo
        self._scores = score_repo
        self._applications = application_repo
        self._storage = storage
        self._tailoring = tailoring_agent
        self._ats = ats_agent
        self._cover_letter = cover_letter_agent
        self._email = email_agent
        self._settings = settings
        self._audit = audit
        self._graph = self._build_graph()

    def generate_documents(
        self,
        user_id: uuid.UUID,
        job_id: uuid.UUID,
        *,
        force: bool = False,
    ) -> JobApplication:
        if not self._settings.ai_enabled:
            raise ValueError("AI is disabled. Set AI_ENABLED=true and configure API keys.")

        job = self._jobs.get_posting_by_id(job_id, user_id)
        if not job:
            raise ValueError("Job not found")

        existing = self._applications.get_by_job(user_id, job_id)
        if existing and not force:
            return existing
        if existing and force and existing.status in (
            ApplicationStatus.APPROVED.value,
            ApplicationStatus.SUBMITTED.value,
        ):
            raise ValueError("Cannot regenerate approved or submitted applications")

        master = self._resolve_master_resume(user_id, job_id)
        state: DocumentState = {
            "user_id": str(user_id),
            "job_id": str(job_id),
            "master_resume_id": str(master.id),
            "force": force,
            "errors": [],
        }
        result = self._graph.invoke(state)
        return self._persist_from_state(user_id, job, master, result, existing)

    def get_application(self, user_id: uuid.UUID, job_id: uuid.UUID) -> JobApplication:
        application = self._applications.get_by_job(user_id, job_id)
        if not application:
            raise ValueError("Application documents not found")
        return application

    def get_document(
        self, user_id: uuid.UUID, job_id: uuid.UUID, document_type: str
    ) -> ApplicationDocument:
        application = self.get_application(user_id, job_id)
        document = self._applications.get_document(application.id, document_type)
        if not document:
            raise ValueError(f"Document '{document_type}' not found")
        return document

    def _resolve_master_resume(self, user_id: uuid.UUID, job_id: uuid.UUID) -> MasterResume:
        score = self._scores.get_by_job(user_id, job_id)
        if not score:
            raise ValueError("Job must be analyzed first (Layer 5 scores required)")
        if not score.selected_master_resume_id:
            raise ValueError("No resume selected — run intelligence pipeline first")
        master = self._resumes.get_master_by_id(score.selected_master_resume_id, user_id)
        if not master:
            raise ValueError("Selected master resume not found")
        return master

    def _build_graph(self):
        from langgraph.graph import END, StateGraph

        graph = StateGraph(DocumentState)
        graph.add_node("tailoring", self._node_tailoring)
        graph.add_node("ats", self._node_ats)
        graph.add_node("cover_letter", self._node_cover_letter)
        graph.add_node("email", self._node_email)
        graph.set_entry_point("tailoring")
        graph.add_edge("tailoring", "ats")
        graph.add_edge("ats", "cover_letter")
        graph.add_edge("cover_letter", "email")
        graph.add_edge("email", END)
        return graph.compile()

    def _node_tailoring(self, state: DocumentState) -> DocumentState:
        user_id = uuid.UUID(state["user_id"])
        job_id = uuid.UUID(state["job_id"])
        master_id = uuid.UUID(state["master_resume_id"])
        job = self._jobs.get_posting_by_id(job_id, user_id)
        master = self._resumes.get_master_by_id(master_id, user_id)
        if not job or not master:
            raise ValueError("Job or master resume not found")
        try:
            state["tailored"] = self._tailoring.tailor(user_id, job, master)
        except Exception as exc:
            state.setdefault("errors", []).append(f"tailoring: {exc}")
            raise
        return state

    def _node_ats(self, state: DocumentState) -> DocumentState:
        user_id = uuid.UUID(state["user_id"])
        job_id = uuid.UUID(state["job_id"])
        master_id = uuid.UUID(state["master_resume_id"])
        job = self._jobs.get_posting_by_id(job_id, user_id)
        master = self._resumes.get_master_by_id(master_id, user_id)
        tailored = state.get("tailored") or {}
        if not job or not master:
            raise ValueError("Job or master resume not found")
        try:
            state["ats"] = self._ats.analyze_post_tailor(user_id, job, master, tailored)
        except Exception as exc:
            state.setdefault("errors", []).append(f"ats: {exc}")
            state["ats"] = {}
        return state

    def _node_cover_letter(self, state: DocumentState) -> DocumentState:
        user_id = uuid.UUID(state["user_id"])
        job_id = uuid.UUID(state["job_id"])
        job = self._jobs.get_posting_by_id(job_id, user_id)
        profile = self._users.get_profile(user_id)
        tailored = state.get("tailored") or {}
        if not job or not profile:
            raise ValueError("Job or profile not found")
        try:
            state["cover_letter"] = self._cover_letter.generate(user_id, job, profile, tailored)
        except Exception as exc:
            state.setdefault("errors", []).append(f"cover_letter: {exc}")
            state["cover_letter"] = {}
        return state

    def _node_email(self, state: DocumentState) -> DocumentState:
        user_id = uuid.UUID(state["user_id"])
        job_id = uuid.UUID(state["job_id"])
        job = self._jobs.get_posting_by_id(job_id, user_id)
        profile = self._users.get_profile(user_id)
        tailored = state.get("tailored") or {}
        if not job or not profile:
            raise ValueError("Job or profile not found")
        try:
            state["email"] = self._email.generate(user_id, job, profile, tailored)
        except Exception as exc:
            state.setdefault("errors", []).append(f"email: {exc}")
            state["email"] = {}
        return state

    def _persist_from_state(
        self,
        user_id: uuid.UUID,
        job: JobPosting,
        master: MasterResume,
        state: DocumentState,
        existing: JobApplication | None,
    ) -> JobApplication:
        tailored = state.get("tailored") or {}
        ats = state.get("ats") or {}
        cover_letter = state.get("cover_letter") or {}
        email = state.get("email") or {}

        fact_check = ats.get("fact_check", {})
        fact_check_passed = fact_check.get("passed") if isinstance(fact_check, dict) else None
        if fact_check_passed is None:
            invented = ats.get("invented_entities", [])
            fact_check_passed = len(invented) == 0 if ats else None

        version = (existing.version + 1) if existing else 1
        application = JobApplication(
            id=existing.id if existing else uuid.uuid4(),
            user_id=user_id,
            job_id=job.id,
            master_resume_id=master.id,
            status=ApplicationStatus.GENERATED.value,
            version=version,
            ats_fact_check_passed=fact_check_passed,
            generation_metadata={
                "workflow_type": WorkflowType.DOCUMENT_GENERATION.value,
                "errors": state.get("errors", []),
                "ats_score": ats.get("ats_score"),
            },
            generated_at=datetime.now(timezone.utc),
            review_notes="",
            reviewed_at=None,
            approved_at=None,
            submitted_at=None,
            submission_url="",
            submission_method=None,
            submission_notes="",
        )
        application = self._applications.upsert(application)

        doc_payloads: dict[str, tuple[dict, str]] = {
            DocumentType.TAILORED_RESUME.value: (tailored, json.dumps(tailored, indent=2)),
            DocumentType.COVER_LETTER.value: (
                cover_letter,
                cover_letter.get("full_text", ""),
            ),
            DocumentType.EMAIL.value: (email, email.get("body_text", "")),
            DocumentType.ATS_REPORT.value: (ats, json.dumps(ats, indent=2)),
        }

        for doc_type, (content, file_body) in doc_payloads.items():
            if not content:
                continue
            category, filename = _DOC_STORAGE[doc_type]
            path = self._storage.save_text(
                category,
                filename,
                file_body,
                user_id=user_id,
                job_id=job.id,
            )
            self._applications.upsert_document(
                ApplicationDocument(
                    application_id=application.id,
                    document_type=doc_type,
                    file_path=str(path),
                    content=content,
                    version=version,
                )
            )

        job.status = JobStatus.DOCUMENTS_READY.value
        self._jobs.update_posting(job)

        if self._audit:
            self._audit.record_application_action(
                application.id,
                action="documents_generated",
                actor=AuditActor.AGENT,
                details={
                    "job_id": str(job.id),
                    "version": version,
                    "ats_fact_check_passed": fact_check_passed,
                    "errors": state.get("errors", []),
                },
            )

        logger.info(
            "document_generation_complete",
            job_id=str(job.id),
            application_id=str(application.id),
            version=version,
            fact_check_passed=fact_check_passed,
        )
        return self._applications.get_by_id(application.id, user_id) or application
