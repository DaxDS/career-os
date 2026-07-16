import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas.agents import JobScoreResponse
from app.api.schemas.ai import (
    AIStatusResponse,
    JobClassifyRequest,
    JobClassifyResponse,
    PromptSyncResponse,
)
from app.application.ports.classifier import JobClassifierPort
from app.application.ports.llm import ModelRouterPort
from app.application.ports.prompts import PromptRegistryPort
from app.application.services.job_intelligence_service import JobIntelligenceService
from app.config import Settings, get_settings
from app.dependencies import (
    get_current_user_id,
    get_hybrid_job_classifier,
    get_job_intelligence_service,
    get_model_router,
    get_prompt_registry,
)
from app.infrastructure.prompts.sync import PromptSyncService

router = APIRouter(tags=["ai"])


@router.get("/ai/status", response_model=AIStatusResponse)
def ai_status(
    settings: Settings = Depends(get_settings),
    router_svc: ModelRouterPort = Depends(get_model_router),
    prompts: PromptRegistryPort = Depends(get_prompt_registry),
):
    registered = prompts.list_registered_prompts()
    synced = sum(1 for p in registered if p.get("active_version") is not None)
    return AIStatusResponse(
        ai_enabled=settings.ai_enabled,
        providers=router_svc.provider_status(),
        capabilities=router_svc.list_capabilities(),
        prompts_synced=synced,
        prompts_total=len(registered),
    )


@router.post("/foundation/prompts/sync", response_model=PromptSyncResponse)
def sync_prompts(
    user_id: uuid.UUID = Depends(get_current_user_id),
    prompts: PromptRegistryPort = Depends(get_prompt_registry),
):
    result = PromptSyncService(prompts).sync_all()
    return PromptSyncResponse(**result)


@router.post("/ai/jobs/classify", response_model=JobClassifyResponse)
def classify_job_posting(
    body: JobClassifyRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    classifier: JobClassifierPort = Depends(get_hybrid_job_classifier),
):
    classification = classifier.classify(
        body.title,
        body.description,
        body.remote_type,
        company=body.company,
        location=body.location,
    )
    return JobClassifyResponse(classification=classification)


@router.post("/ai/jobs/{job_id}/score", response_model=JobScoreResponse)
def score_job(
    job_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    intelligence: JobIntelligenceService = Depends(get_job_intelligence_service),
):
    try:
        score = intelligence.analyze_job(user_id, job_id)
        return JobScoreResponse.model_validate(score)
    except ValueError as exc:
        status = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

