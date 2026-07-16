import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.schemas.job import (
    JobImportRequest,
    JobImportResponse,
    JobImportResultItem,
    JobPostingResponse,
    JobSourceCreateRequest,
    JobSourcePresetResponse,
    JobSourceResponse,
    JobSourceUpdateRequest,
    JobUpdateRequest,
)
from app.api.schemas.job_parse import ParseJobUrlRequest, ParseJobUrlResponse
from app.application.ports.score_repository import ScoreRepositoryPort
from app.application.services.job_service import JobService
from app.application.services.job_url_parser_service import JobUrlParserService
from app.application.services.plan_limit_service import PlanLimitService
from app.dependencies import (
    get_current_user_id,
    get_job_service,
    get_job_url_parser,
    get_plan_limit_service,
    get_score_repository,
)

router = APIRouter(tags=["jobs"])


def _to_job_response(job, score=None) -> JobPostingResponse:
    description = job.description or ""
    return JobPostingResponse(
        overall_score=score.overall_score if score else None,
        immigration_score=score.immigration_score if score else None,
        id=job.id,
        source_id=job.source_id,
        external_id=job.external_id,
        source_url=job.source_url,
        title=job.title,
        company=job.company,
        location_city=job.location_city,
        location_province=job.location_province,
        remote_type=job.remote_type,
        description_preview=description[:300],
        role_family=job.role_family,
        classification=job.classification,
        status=job.status,
        date_found=job.date_found,
        date_posted=job.date_posted,
        salary_min_cad=job.salary_min_cad,
        salary_max_cad=job.salary_max_cad,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/jobs/sources/presets", response_model=list[JobSourcePresetResponse])
def list_job_source_presets(
    job_svc: JobService = Depends(get_job_service),
):
    return [JobSourcePresetResponse(**preset) for preset in job_svc.list_preset_definitions()]


@router.get("/jobs/sources", response_model=list[JobSourceResponse])
def list_job_sources(
    user_id: uuid.UUID = Depends(get_current_user_id),
    job_svc: JobService = Depends(get_job_service),
):
    return [JobSourceResponse.model_validate(s) for s in job_svc.list_sources(user_id)]


@router.post("/jobs/sources", response_model=JobSourceResponse, status_code=201)
def create_job_source(
    body: JobSourceCreateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    job_svc: JobService = Depends(get_job_service),
):
    try:
        source = job_svc.create_source(user_id, body.name, body.source_type, body.config)
        return JobSourceResponse.model_validate(source)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/jobs/sources/{source_id}", response_model=JobSourceResponse)
def update_job_source(
    source_id: uuid.UUID,
    body: JobSourceUpdateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    job_svc: JobService = Depends(get_job_service),
):
    try:
        source = job_svc.update_source(
            user_id,
            source_id,
            name=body.name,
            config=body.config,
            is_active=body.is_active,
        )
        return JobSourceResponse.model_validate(source)
    except ValueError as exc:
        status = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.get("/jobs", response_model=list[JobPostingResponse])
def list_jobs(
    user_id: uuid.UUID = Depends(get_current_user_id),
    job_svc: JobService = Depends(get_job_service),
    score_repo: ScoreRepositoryPort = Depends(get_score_repository),
    province: str | None = Query(None),
    role_family: str | None = Query(None),
    status: str | None = Query(None),
    source_id: uuid.UUID | None = Query(None),
):
    jobs = job_svc.list_jobs(
        user_id,
        province=province,
        role_family=role_family,
        status=status,
        source_id=source_id,
    )
    # Scores are user-scoped (same pattern as review_queue_service): the query
    # filters on JobScore.user_id, so other users' scores can never leak in.
    scores = score_repo.list_for_jobs(user_id, [j.id for j in jobs])
    score_by_job = {s.job_id: s for s in scores}
    return [_to_job_response(j, score_by_job.get(j.id)) for j in jobs]


@router.post("/jobs/parse-url", response_model=ParseJobUrlResponse)
def parse_job_url(
    body: ParseJobUrlRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    parser: JobUrlParserService = Depends(get_job_url_parser),
):
    del user_id
    try:
        return ParseJobUrlResponse(**parser.parse(str(body.url)))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/jobs/import", response_model=JobImportResponse, status_code=201)
def import_jobs(
    body: JobImportRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    job_svc: JobService = Depends(get_job_service),
    limits: PlanLimitService = Depends(get_plan_limit_service),
):
    limits.ensure_can_import_jobs(user_id, len(body.jobs))
    try:
        payloads = [job.model_dump() for job in body.jobs]
        results = job_svc.import_jobs(
            user_id, payloads, body.source_id, body.source_preset_key
        )
        items = [
            JobImportResultItem(
                import_status=r["import_status"],
                match_reason=r.get("match_reason"),
                job=_to_job_response(r["job"]),
            )
            for r in results
        ]
        return JobImportResponse(
            results=items,
            created=sum(1 for i in items if i.import_status == "created"),
            duplicates=sum(1 for i in items if i.import_status == "duplicate"),
        )
    except ValueError as exc:
        status = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.get("/jobs/{job_id}", response_model=JobPostingResponse)
def get_job(
    job_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    job_svc: JobService = Depends(get_job_service),
):
    try:
        return _to_job_response(job_svc.get_job(user_id, job_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/jobs/{job_id}", response_model=JobPostingResponse)
def update_job(
    job_id: uuid.UUID,
    body: JobUpdateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    job_svc: JobService = Depends(get_job_service),
):
    try:
        job = job_svc.update_job(user_id, job_id, status=body.status, role_family=body.role_family)
        return _to_job_response(job)
    except ValueError as exc:
        status = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.delete("/jobs/{job_id}")
def archive_job(
    job_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    job_svc: JobService = Depends(get_job_service),
):
    try:
        job_svc.archive_job(user_id, job_id)
        return {"status": "archived"}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
