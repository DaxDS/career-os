from functools import lru_cache

import uuid
from collections.abc import Generator
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.application.ports.application_repository import ApplicationRepositoryPort
from app.application.ports.audit import AuditPort
from app.application.ports.classifier import JobClassifierPort
from app.application.ports.llm import ModelRouterPort
from app.application.ports.prompts import PromptRegistryPort
from app.application.ports.job_repository import JobRepositoryPort
from app.application.ports.resume_repository import ResumeRepositoryPort
from app.application.ports.score_repository import AgentRunRepositoryPort, ScoreRepositoryPort
from app.application.ports.storage import FileStoragePort
from app.application.ports.user_repository import UserRepositoryPort
from app.application.services.hybrid_job_classifier import HybridJobClassifier
from app.application.services.review_queue_service import ReviewQueueService
from app.application.services.application_tracking_service import ApplicationTrackingService
from app.application.services.document_generation_service import DocumentGenerationService
from app.application.services.job_intelligence_service import JobIntelligenceService
from app.application.services.agents.ats_analysis_agent import AtsAnalysisAgent
from app.application.services.agents.cover_letter_agent import CoverLetterAgent
from app.application.services.agents.email_generation_agent import EmailGenerationAgent
from app.application.services.agents.immigration_scoring_agent import ImmigrationScoringAgent
from app.application.services.agents.job_scoring_agent import JobScoringAgent
from app.application.services.agents.resume_selection_agent import ResumeSelectionAgent
from app.application.services.agents.resume_tailoring_agent import ResumeTailoringAgent
from app.application.services.job_scoring_service import JobScoringService
from app.application.services.job_service import JobService
from app.application.services.interview_prep_service import InterviewPrepService
from app.application.services.job_url_parser_service import JobUrlParserService
from app.application.services.linkedin_optimizer_service import LinkedInOptimizerService
from app.application.services.plan_limit_service import PlanLimitService
from app.application.services.resume_service import ResumeService
from app.application.services.user_service import AuthService, ProfileService
from app.config import Settings, get_settings
from app.infrastructure.ai.capability_registry import CapabilityRegistry
from app.infrastructure.ai.providers.anthropic_provider import AnthropicProvider
from app.infrastructure.ai.providers.openai_provider import OpenAIProvider
from app.infrastructure.ai.router import ModelRouter
from app.infrastructure.audit.sqlalchemy_audit import SQLAlchemyAuditLog
from app.infrastructure.auth.jwt import decode_access_token
from app.infrastructure.db.models import User
from app.infrastructure.db.session import get_db_session
from app.infrastructure.prompts.registry import PromptRegistry
from app.infrastructure.repositories.application_repository import SQLAlchemyApplicationRepository
from app.infrastructure.repositories.job_repository import SQLAlchemyJobRepository
from app.infrastructure.repositories.resume_repository import SQLAlchemyResumeRepository
from app.infrastructure.repositories.score_repository import (
    SQLAlchemyAgentRunRepository,
    SQLAlchemyScoreRepository,
)
from app.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from app.infrastructure.storage.local_storage import LocalFileStorage

if TYPE_CHECKING:
    from app.application.services.scheduler_pipeline_service import SchedulerPipelineService

security = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    yield from get_db_session()


def get_user_repository(db: Session = Depends(get_db)) -> UserRepositoryPort:
    return SQLAlchemyUserRepository(db)


def get_audit_log(db: Session = Depends(get_db)) -> AuditPort:
    return SQLAlchemyAuditLog(db)


def get_file_storage(settings: Settings = Depends(get_settings)) -> FileStoragePort:
    return LocalFileStorage(settings)


def get_prompt_registry(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> PromptRegistryPort:
    return PromptRegistry(settings, db)


@lru_cache
def get_capability_registry() -> CapabilityRegistry:
    return CapabilityRegistry()


def get_model_router(settings: Settings = Depends(get_settings)) -> ModelRouterPort:
    providers = {
        "openai": OpenAIProvider(settings),
        "anthropic": AnthropicProvider(settings),
    }
    return ModelRouter(get_capability_registry(), providers, settings)


def get_hybrid_job_classifier(
    router: ModelRouterPort = Depends(get_model_router),
    prompts: PromptRegistryPort = Depends(get_prompt_registry),
    settings: Settings = Depends(get_settings),
) -> JobClassifierPort:
    return HybridJobClassifier(router, prompts, settings)


def get_job_scoring_service(
    router: ModelRouterPort = Depends(get_model_router),
    prompts: PromptRegistryPort = Depends(get_prompt_registry),
    user_repo: UserRepositoryPort = Depends(get_user_repository),
    settings: Settings = Depends(get_settings),
) -> JobScoringService:
    return JobScoringService(router, prompts, user_repo, settings)


def get_auth_service(
    user_repo: UserRepositoryPort = Depends(get_user_repository),
    settings: Settings = Depends(get_settings),
    audit: AuditPort = Depends(get_audit_log),
) -> AuthService:
    return AuthService(user_repo, settings, audit)


def get_profile_service(
    user_repo: UserRepositoryPort = Depends(get_user_repository),
    audit: AuditPort = Depends(get_audit_log),
) -> ProfileService:
    return ProfileService(user_repo, audit)


def get_job_repository(db: Session = Depends(get_db)) -> JobRepositoryPort:
    return SQLAlchemyJobRepository(db)


def get_job_service(
    job_repo: JobRepositoryPort = Depends(get_job_repository),
    audit: AuditPort = Depends(get_audit_log),
    classifier: JobClassifierPort = Depends(get_hybrid_job_classifier),
) -> JobService:
    return JobService(job_repo, audit, classifier)


def get_job_url_parser(
    router: ModelRouterPort = Depends(get_model_router),
) -> JobUrlParserService:
    return JobUrlParserService(router)


def get_plan_limit_service(db: Session = Depends(get_db)) -> PlanLimitService:
    return PlanLimitService(db)


def get_linkedin_optimizer(
    router: ModelRouterPort = Depends(get_model_router),
) -> LinkedInOptimizerService:
    return LinkedInOptimizerService(router)


def get_resume_repository(db: Session = Depends(get_db)) -> ResumeRepositoryPort:
    return SQLAlchemyResumeRepository(db)


def get_resume_service(
    resume_repo: ResumeRepositoryPort = Depends(get_resume_repository),
    storage: FileStoragePort = Depends(get_file_storage),
    audit: AuditPort = Depends(get_audit_log),
) -> ResumeService:
    return ResumeService(resume_repo, storage, audit)


def get_score_repository(db: Session = Depends(get_db)) -> ScoreRepositoryPort:
    return SQLAlchemyScoreRepository(db)


def get_agent_run_repository(db: Session = Depends(get_db)) -> AgentRunRepositoryPort:
    return SQLAlchemyAgentRunRepository(db)


def get_application_repository(db: Session = Depends(get_db)) -> ApplicationRepositoryPort:
    return SQLAlchemyApplicationRepository(db)


def get_interview_prep_service(
    application_repo: ApplicationRepositoryPort = Depends(get_application_repository),
    router: ModelRouterPort = Depends(get_model_router),
) -> InterviewPrepService:
    return InterviewPrepService(application_repo, router)


def _build_agents(
    router: ModelRouterPort,
    prompts: PromptRegistryPort,
    settings: Settings,
    agent_runs: AgentRunRepositoryPort,
    audit: AuditPort,
):
    return (
        ImmigrationScoringAgent(router, prompts, settings, agent_runs, audit),
        JobScoringAgent(router, prompts, settings, agent_runs, audit),
        AtsAnalysisAgent(router, prompts, settings, agent_runs, audit),
        ResumeSelectionAgent(router, prompts, settings, agent_runs, audit),
    )


def get_job_intelligence_service(
    job_repo: JobRepositoryPort = Depends(get_job_repository),
    user_repo: UserRepositoryPort = Depends(get_user_repository),
    resume_repo: ResumeRepositoryPort = Depends(get_resume_repository),
    score_repo: ScoreRepositoryPort = Depends(get_score_repository),
    agent_runs: AgentRunRepositoryPort = Depends(get_agent_run_repository),
    router: ModelRouterPort = Depends(get_model_router),
    prompts: PromptRegistryPort = Depends(get_prompt_registry),
    settings: Settings = Depends(get_settings),
    audit: AuditPort = Depends(get_audit_log),
) -> JobIntelligenceService:
    immigration, scoring, ats, selection = _build_agents(
        router, prompts, settings, agent_runs, audit
    )
    return JobIntelligenceService(
        job_repo,
        user_repo,
        resume_repo,
        score_repo,
        immigration,
        scoring,
        ats,
        selection,
        settings,
        audit,
    )


def _build_doc_agents(
    router: ModelRouterPort,
    prompts: PromptRegistryPort,
    settings: Settings,
    agent_runs: AgentRunRepositoryPort,
    audit: AuditPort,
):
    return (
        ResumeTailoringAgent(router, prompts, settings, agent_runs, audit),
        AtsAnalysisAgent(router, prompts, settings, agent_runs, audit),
        CoverLetterAgent(router, prompts, settings, agent_runs, audit),
        EmailGenerationAgent(router, prompts, settings, agent_runs, audit),
    )


def get_document_generation_service(
    job_repo: JobRepositoryPort = Depends(get_job_repository),
    user_repo: UserRepositoryPort = Depends(get_user_repository),
    resume_repo: ResumeRepositoryPort = Depends(get_resume_repository),
    score_repo: ScoreRepositoryPort = Depends(get_score_repository),
    application_repo: ApplicationRepositoryPort = Depends(get_application_repository),
    storage: FileStoragePort = Depends(get_file_storage),
    agent_runs: AgentRunRepositoryPort = Depends(get_agent_run_repository),
    router: ModelRouterPort = Depends(get_model_router),
    prompts: PromptRegistryPort = Depends(get_prompt_registry),
    settings: Settings = Depends(get_settings),
    audit: AuditPort = Depends(get_audit_log),
) -> DocumentGenerationService:
    tailoring, ats, cover_letter, email = _build_doc_agents(
        router, prompts, settings, agent_runs, audit
    )
    return DocumentGenerationService(
        job_repo,
        user_repo,
        resume_repo,
        score_repo,
        application_repo,
        storage,
        tailoring,
        ats,
        cover_letter,
        email,
        settings,
        audit,
    )


def get_application_tracking_service(
    application_repo: ApplicationRepositoryPort = Depends(get_application_repository),
    job_repo: JobRepositoryPort = Depends(get_job_repository),
    storage: FileStoragePort = Depends(get_file_storage),
    audit: AuditPort = Depends(get_audit_log),
) -> ApplicationTrackingService:
    return ApplicationTrackingService(application_repo, job_repo, storage, audit)


def get_review_queue_service(
    application_repo: ApplicationRepositoryPort = Depends(get_application_repository),
    score_repo: ScoreRepositoryPort = Depends(get_score_repository),
    tracking: ApplicationTrackingService = Depends(get_application_tracking_service),
    audit: AuditPort = Depends(get_audit_log),
) -> ReviewQueueService:
    return ReviewQueueService(application_repo, score_repo, tracking, audit)


def get_automation_repository(db: Session = Depends(get_db)):
    from app.infrastructure.repositories.automation_repository import SQLAlchemyAutomationRepository

    return SQLAlchemyAutomationRepository(db)


@lru_cache
def get_browser_connector_registry():
    from app.infrastructure.browser.connectors.registry import BrowserConnectorRegistry

    return BrowserConnectorRegistry()


def get_automation_settings_resolved():
    from pathlib import Path

    from app.infrastructure.browser.settings import get_automation_settings, resolve_automation_paths

    project_root = Path(__file__).resolve().parents[2]
    return resolve_automation_paths(get_automation_settings(), project_root)


def get_browser_runner():
    from app.infrastructure.browser.playwright_runner import PlaywrightRunner

    return PlaywrightRunner()


def get_browser_automation(
    application_repo: ApplicationRepositoryPort = Depends(get_application_repository),
    job_repo: JobRepositoryPort = Depends(get_job_repository),
    user_repo: UserRepositoryPort = Depends(get_user_repository),
    resume_repo: ResumeRepositoryPort = Depends(get_resume_repository),
    automation_repo=Depends(get_automation_repository),
    storage: FileStoragePort = Depends(get_file_storage),
    tracking: ApplicationTrackingService = Depends(get_application_tracking_service),
    audit: AuditPort = Depends(get_audit_log),
    connector_registry=Depends(get_browser_connector_registry),
    runner=Depends(get_browser_runner),
):
    from app.infrastructure.browser.automation_engine import PlaywrightBrowserAutomation
    from app.infrastructure.browser.session_manager import BrowserSessionManager

    settings = get_automation_settings_resolved()
    session_manager = BrowserSessionManager(automation_repo, settings)
    return PlaywrightBrowserAutomation(
        application_repo,
        job_repo,
        user_repo,
        resume_repo,
        automation_repo,
        connector_registry,
        session_manager,
        runner,
        storage,
        settings,
        tracking,
        audit,
    )


def get_application_automation_service(
    automation=Depends(get_browser_automation),
    automation_repo=Depends(get_automation_repository),
):
    from app.application.services.application_automation_service import ApplicationAutomationService

    return ApplicationAutomationService(automation, automation_repo)


_scheduler_runner = None


def _build_scheduler_pipeline_service(db: Session) -> SchedulerPipelineService:
    from app.application.services.scheduler_pipeline_service import SchedulerPipelineService
    from app.infrastructure.notifications.pipeline_notifier import PipelineNotifier
    from app.infrastructure.repositories.scheduler_repository import SQLAlchemyPipelineRunRepository

    settings = get_settings()
    scheduler_repo = SQLAlchemyPipelineRunRepository(db)
    job_repo = SQLAlchemyJobRepository(db)
    audit = SQLAlchemyAuditLog(db)
    agent_runs = SQLAlchemyAgentRunRepository(db)
    router = ModelRouter(
        get_capability_registry(),
        {
            "openai": OpenAIProvider(settings),
            "anthropic": AnthropicProvider(settings),
        },
        settings,
    )
    prompts = PromptRegistry(settings, db)
    classifier = HybridJobClassifier(router, prompts, settings)
    storage = LocalFileStorage(settings)
    job_svc = JobService(job_repo, audit, classifier)
    intelligence = get_job_intelligence_service(
        job_repo=job_repo,
        user_repo=SQLAlchemyUserRepository(db),
        resume_repo=SQLAlchemyResumeRepository(db),
        score_repo=SQLAlchemyScoreRepository(db),
        agent_runs=agent_runs,
        router=router,
        prompts=prompts,
        settings=settings,
        audit=audit,
    )
    documents = get_document_generation_service(
        job_repo=job_repo,
        user_repo=SQLAlchemyUserRepository(db),
        resume_repo=SQLAlchemyResumeRepository(db),
        score_repo=SQLAlchemyScoreRepository(db),
        application_repo=SQLAlchemyApplicationRepository(db),
        storage=storage,
        agent_runs=agent_runs,
        router=router,
        prompts=prompts,
        settings=settings,
        audit=audit,
    )
    notifier = PipelineNotifier(scheduler_repo, audit)
    return SchedulerPipelineService(
        job_svc,
        job_repo,
        get_job_search_registry(),
        intelligence,
        documents,
        SQLAlchemyApplicationRepository(db),
        SQLAlchemyScoreRepository(db),
        scheduler_repo,
        notifier,
    )


@lru_cache
def get_job_search_registry():
    from app.infrastructure.jobs.search.live_adapters import (
        IndeedCanadaSearchAdapter,
        JobBankCanadaSearchAdapter,
        ManualUrlImportSearchAdapter,
        NotImplementedSearchAdapter,
    )
    from app.infrastructure.jobs.search.registry import JobSearchRegistry

    registry = JobSearchRegistry()
    registry.register("job_bank_canada", JobBankCanadaSearchAdapter())
    registry.register("indeed", IndeedCanadaSearchAdapter())
    registry.register("manual_url_import", ManualUrlImportSearchAdapter())
    registry.register("workpei", NotImplementedSearchAdapter())
    registry.register("company_career_pages", NotImplementedSearchAdapter())
    return registry


def get_scheduler_repository(db: Session = Depends(get_db)):
    from app.infrastructure.repositories.scheduler_repository import SQLAlchemyPipelineRunRepository

    return SQLAlchemyPipelineRunRepository(db)


def get_scheduler_pipeline_service(
    db: Session = Depends(get_db),
    job_svc: JobService = Depends(get_job_service),
    job_repo: JobRepositoryPort = Depends(get_job_repository),
    intelligence: JobIntelligenceService = Depends(get_job_intelligence_service),
    documents: DocumentGenerationService = Depends(get_document_generation_service),
    application_repo: ApplicationRepositoryPort = Depends(get_application_repository),
    score_repo: ScoreRepositoryPort = Depends(get_score_repository),
    scheduler_repo=Depends(get_scheduler_repository),
    audit: AuditPort = Depends(get_audit_log),
    job_search=Depends(get_job_search_registry),
):
    from app.application.services.scheduler_pipeline_service import SchedulerPipelineService
    from app.infrastructure.notifications.pipeline_notifier import PipelineNotifier

    notifier = PipelineNotifier(scheduler_repo, audit)
    return SchedulerPipelineService(
        job_svc,
        job_repo,
        job_search,
        intelligence,
        documents,
        application_repo,
        score_repo,
        scheduler_repo,
        notifier,
    )


def get_scheduler_service(
    pipeline=Depends(get_scheduler_pipeline_service),
    scheduler_repo=Depends(get_scheduler_repository),
):
    from app.application.services.scheduler_service import SchedulerService

    global _scheduler_runner
    return SchedulerService(pipeline, scheduler_repo, runner=_scheduler_runner)


def init_scheduler_runner(morning_run_callback) -> None:
    from app.infrastructure.scheduler.apscheduler_runner import SchedulerRunner
    from app.infrastructure.scheduler.settings import get_scheduler_settings

    global _scheduler_runner
    settings = get_scheduler_settings()
    _scheduler_runner = SchedulerRunner(settings, morning_run_callback)
    _scheduler_runner.start()


def shutdown_scheduler_runner() -> None:
    global _scheduler_runner
    if _scheduler_runner:
        _scheduler_runner.shutdown()
        _scheduler_runner = None


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    settings: Settings = Depends(get_settings),
    user_repo: UserRepositoryPort = Depends(get_user_repository),
) -> uuid.UUID:
    if credentials:
        try:
            user_id = decode_access_token(credentials.credentials, settings)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

        user = user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user_id

    if settings.dev_auth_bypass:
        user = user_repo.get_by_email(settings.default_user_email)
        if user and user.is_active:
            return user.id

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


async def get_current_user(
    user_id: uuid.UUID = Depends(get_current_user_id),
    user_repo: UserRepositoryPort = Depends(get_user_repository),
) -> User:
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
