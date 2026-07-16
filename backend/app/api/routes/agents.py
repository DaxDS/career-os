import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.schemas.agents import (
    AgentRunResponse,
    BatchAnalyzeResponse,
    JobScoreResponse,
    PipelineRunRequest,
    RankedJobResponse,
)
from app.application.services.job_intelligence_service import JobIntelligenceService
from app.application.ports.score_repository import AgentRunRepositoryPort
from app.dependencies import (
    get_agent_run_repository,
    get_current_user_id,
    get_job_intelligence_service,
)

router = APIRouter(tags=["agents"])


@router.post("/agents/jobs/{job_id}/analyze", response_model=JobScoreResponse)
def analyze_job(
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


@router.post("/agents/pipeline/run", response_model=BatchAnalyzeResponse)
def run_intelligence_pipeline(
    body: PipelineRunRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    intelligence: JobIntelligenceService = Depends(get_job_intelligence_service),
):
    try:
        scores = intelligence.batch_analyze(user_id, limit=body.limit)
        return BatchAnalyzeResponse(
            analyzed=len(scores),
            job_score_ids=[s.id for s in scores],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/agents/jobs/{job_id}/scores", response_model=JobScoreResponse)
def get_job_scores(
    job_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    intelligence: JobIntelligenceService = Depends(get_job_intelligence_service),
):
    try:
        return JobScoreResponse.model_validate(intelligence.get_scores(user_id, job_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/agents/jobs/ranked", response_model=list[RankedJobResponse])
def list_ranked_jobs(
    user_id: uuid.UUID = Depends(get_current_user_id),
    intelligence: JobIntelligenceService = Depends(get_job_intelligence_service),
    min_overall_score: int | None = Query(None, ge=0, le=100),
    province: str | None = Query(None),
    role_family: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    ranked = intelligence.list_ranked(
        user_id,
        min_overall_score=min_overall_score,
        province=province,
        role_family=role_family,
        limit=limit,
    )
    return [
        RankedJobResponse(
            job_id=job.id,
            title=job.title,
            company=job.company,
            location_province=job.location_province,
            role_family=job.role_family,
            overall_score=score.overall_score,
            selected_master_resume_id=score.selected_master_resume_id,
            scored_at=score.scored_at,
        )
        for score, job in ranked
    ]


@router.get("/agents/jobs/{job_id}/runs", response_model=list[AgentRunResponse])
def list_agent_runs(
    job_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    agent_runs: AgentRunRepositoryPort = Depends(get_agent_run_repository),
):
    runs = agent_runs.list_for_job(user_id, job_id)
    return [AgentRunResponse.model_validate(r) for r in runs]
