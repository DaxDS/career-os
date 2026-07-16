from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.application.services.plan_limit_service import PlanLimitExceeded

from app.api.routes.billing import router as billing_router
from app.api.routes.automation import router as automation_router
from app.api.routes.scheduler import router as scheduler_router
from app.api.routes.review import router as review_router
from app.api.routes.tracking import router as tracking_router
from app.api.routes.documents import router as documents_router
from app.api.routes.agents import router as agents_router
from app.api.routes.ai import router as ai_router
from app.api.routes.auth import router as auth_router
from app.api.routes.foundation import router as foundation_router
from app.api.routes.health import router as health_router
from app.api.routes.interview import router as interview_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.linkedin import router as linkedin_router
from app.api.routes.profile import router as profile_router
from app.api.routes.resumes import router as resumes_router
from app.config import get_settings, resolve_paths
from app.infrastructure.audit.sqlalchemy_audit import SQLAlchemyAuditLog
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.logging.setup import get_logger, setup_logging
from app.infrastructure.repositories.job_repository import SQLAlchemyJobRepository
from app.infrastructure.ai.capability_registry import CapabilityRegistry
from app.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from app.application.services.job_service import JobService
from app.infrastructure.prompts.registry import PromptRegistry
from app.infrastructure.prompts.sync import PromptSyncService
from app.application.services.user_service import AuthService
from app.infrastructure.db.models import User

logger = get_logger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_DIST = PROJECT_ROOT / "web" / "dist"


def _validate_capability_registry() -> None:
    try:
        registry = CapabilityRegistry()
        missing = registry.validate_core_capabilities()
        if missing:
            logger.error("core_ai_capabilities_missing", capabilities=missing)
        else:
            from app.domain.enums import CORE_AI_CAPABILITIES

            logger.info(
                "capability_registry_validated",
                core_count=len(CORE_AI_CAPABILITIES),
            )
    except Exception as exc:
        logger.warning("capability_registry_validation_skipped", error=str(exc))


def _bootstrap_prompt_sync() -> None:
    db = SessionLocal()
    try:
        settings = resolve_paths(get_settings(), PROJECT_ROOT)
        registry = PromptRegistry(settings, db)
        result = PromptSyncService(registry).sync_all()
        logger.info("prompt_sync_bootstrap", **{k: result[k] for k in ("synced", "unchanged")})
    except Exception as exc:
        logger.warning("prompt_sync_bootstrap_skipped", error=str(exc))
    finally:
        db.close()


def _bootstrap_single_user(settings) -> None:
    db = SessionLocal()
    try:
        user_repo = SQLAlchemyUserRepository(db)
        audit = SQLAlchemyAuditLog(db)
        auth_svc = AuthService(user_repo, settings, audit)
        auth_svc.bootstrap_single_user()
    except Exception as exc:
        logger.warning("single_user_bootstrap_skipped", error=str(exc))
    finally:
        db.close()


def _bootstrap_job_source_presets() -> None:
    db = SessionLocal()
    try:
        user_ids = [row[0] for row in db.query(User.id).all()]
        if not user_ids:
            return
        job_repo = SQLAlchemyJobRepository(db)
        job_svc = JobService(job_repo)
        for user_id in user_ids:
            job_svc.seed_builtin_sources(user_id)
    except Exception as exc:
        logger.warning("job_source_preset_bootstrap_skipped", error=str(exc))
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = resolve_paths(get_settings(), PROJECT_ROOT)
    from app.infrastructure.config.production import validate_production_settings

    validate_production_settings(settings)
    setup_logging(settings.log_level, settings.log_json)

    for path in (
        settings.storage_path,
        settings.resumes_path,
        settings.applications_path,
        settings.templates_path,
    ):
        path.mkdir(parents=True, exist_ok=True)

    from app.infrastructure.browser.settings import get_automation_settings, resolve_automation_paths

    automation_settings = resolve_automation_paths(get_automation_settings(), PROJECT_ROOT)
    for path in (
        automation_settings.browser_profiles_path,
        automation_settings.browser_screenshots_path,
    ):
        path.mkdir(parents=True, exist_ok=True)

    _bootstrap_single_user(settings)
    _bootstrap_job_source_presets()
    _bootstrap_prompt_sync()
    _validate_capability_registry()

    from app.dependencies import (
        _build_scheduler_pipeline_service,
        init_scheduler_runner,
        shutdown_scheduler_runner,
    )
    from app.application.services.scheduler_service import SchedulerService
    from app.infrastructure.db.session import SessionLocal
    from app.infrastructure.repositories.scheduler_repository import SQLAlchemyPipelineRunRepository

    def _morning_pipeline_run() -> None:
        db = SessionLocal()
        try:
            user_row = db.query(User.id).first()
            if not user_row:
                logger.warning("scheduled_pipeline_skipped", reason="no_user")
                return
            pipeline = _build_scheduler_pipeline_service(db)
            scheduler_repo = SQLAlchemyPipelineRunRepository(db)
            service = SchedulerService(pipeline, scheduler_repo)
            service.run_scheduled(user_row[0])
        except Exception as exc:
            logger.exception("scheduled_pipeline_failed", error=str(exc))
        finally:
            db.close()

    init_scheduler_runner(_morning_pipeline_run)

    logger.info(
        "app_started",
        layer="11-desktop",
        version=settings.app_version,
        single_user=settings.single_user_mode,
    )
    yield
    shutdown_scheduler_runner()


def create_app() -> FastAPI:
    settings = resolve_paths(get_settings(), PROJECT_ROOT)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Personal AI Career Operating System — V1 production API",
        lifespan=lifespan,
        openapi_tags=[
            {"name": "health", "description": "Liveness and readiness probes"},
            {"name": "foundation", "description": "Audit, storage, and prompt registry status"},
            {"name": "auth", "description": "Authentication"},
            {"name": "profile", "description": "User profile and preferences"},
            {"name": "resumes", "description": "Master resume management"},
            {"name": "jobs", "description": "Job sources, import, and deduplication"},
            {"name": "ai", "description": "AI status, classification, and prompt sync"},
            {"name": "agents", "description": "Layer 5 intelligence pipeline"},
            {"name": "documents", "description": "Layer 6 document generation"},
            {"name": "tracking", "description": "Layer 7 application tracking"},
            {"name": "review", "description": "Layer 8 review queue"},
            {"name": "automation", "description": "Layer 9 browser automation"},
            {"name": "scheduler", "description": "Layer 10 morning pipeline"},
            {"name": "billing", "description": "Plans, usage, and subscription"},
            {"name": "linkedin", "description": "LinkedIn profile optimizer"},
            {"name": "interview", "description": "Interview prep and answer coaching"},
        ],
    )

    @app.exception_handler(PlanLimitExceeded)
    async def plan_limit_handler(request: Request, exc: PlanLimitExceeded):
        return JSONResponse(status_code=402, content={"detail": str(exc)})

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        started = perf_counter()
        response = await call_next(request)
        duration_ms = round((perf_counter() - started) * 1000, 2)
        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix=settings.api_prefix)
    app.include_router(foundation_router, prefix=settings.api_prefix)
    app.include_router(auth_router, prefix=settings.api_prefix)
    app.include_router(profile_router, prefix=settings.api_prefix)
    app.include_router(resumes_router, prefix=settings.api_prefix)
    app.include_router(jobs_router, prefix=settings.api_prefix)
    app.include_router(ai_router, prefix=settings.api_prefix)
    app.include_router(agents_router, prefix=settings.api_prefix)
    app.include_router(documents_router, prefix=settings.api_prefix)
    app.include_router(tracking_router, prefix=settings.api_prefix)
    app.include_router(review_router, prefix=settings.api_prefix)
    app.include_router(automation_router, prefix=settings.api_prefix)
    app.include_router(scheduler_router, prefix=settings.api_prefix)
    app.include_router(billing_router, prefix=settings.api_prefix)
    app.include_router(linkedin_router, prefix=settings.api_prefix)
    app.include_router(interview_router, prefix=settings.api_prefix)
    _register_product_ui(app)
    return app


def _register_product_ui(app: FastAPI) -> None:
    """Serve the Career OS product web app at / when web/dist exists."""
    if not WEB_DIST.is_dir():
        logger.info("web_ui_skipped", reason="web/dist not built — run: cd web && npm install && npm run build")
        return

    index = WEB_DIST / "index.html"
    if not index.is_file():
        return

    assets_dir = WEB_DIST / "assets"
    if assets_dir.is_dir():
        from fastapi.staticfiles import StaticFiles

        app.mount("/assets", StaticFiles(directory=assets_dir), name="web-assets")

    @app.get("/", include_in_schema=False)
    async def product_home():
        return FileResponse(index)

    @app.get("/register", include_in_schema=False)
    async def product_register_page():
        return FileResponse(index)

    @app.get("/login", include_in_schema=False)
    @app.get("/pricing", include_in_schema=False)
    async def product_auth_pages():
        return FileResponse(index)

    @app.get("/app", include_in_schema=False)
    @app.get("/app/{full_path:path}", include_in_schema=False)
    async def product_app_spa(full_path: str = ""):
        return FileResponse(index)

    logger.info("web_ui_enabled", path=str(WEB_DIST))


app = create_app()
