import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.schemas.scheduler import (
    CompanyPipelineRequest,
    PipelineNotificationResponse,
    PipelineRunResponse,
    SchedulerStatusResponse,
)
from app.application.services.plan_limit_service import PlanLimitService
from app.application.services.scheduler_service import SchedulerService
from app.dependencies import get_current_user_id, get_plan_limit_service, get_scheduler_service

router = APIRouter(tags=["scheduler"])


@router.post("/scheduler/run", response_model=PipelineRunResponse)
def run_manual_pipeline(
    user_id: uuid.UUID = Depends(get_current_user_id),
    scheduler: SchedulerService = Depends(get_scheduler_service),
    limits: PlanLimitService = Depends(get_plan_limit_service),
):
    limits.ensure_can_run_pipeline(user_id)
    try:
        return PipelineRunResponse.model_validate(scheduler.run_manual(user_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/scheduler/run/source/{source_id}", response_model=PipelineRunResponse)
def run_source_pipeline(
    source_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    scheduler: SchedulerService = Depends(get_scheduler_service),
    limits: PlanLimitService = Depends(get_plan_limit_service),
):
    limits.ensure_can_run_pipeline(user_id)
    try:
        return PipelineRunResponse.model_validate(scheduler.run_for_source(user_id, source_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/scheduler/run/company", response_model=PipelineRunResponse)
def run_company_pipeline(
    body: CompanyPipelineRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    scheduler: SchedulerService = Depends(get_scheduler_service),
    limits: PlanLimitService = Depends(get_plan_limit_service),
):
    limits.ensure_can_run_pipeline(user_id)
    try:
        run = scheduler.run_for_company(user_id, body.company, source_id=body.source_id)
        return PipelineRunResponse.model_validate(run)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/scheduler/run/job/{job_id}", response_model=PipelineRunResponse)
def run_job_pipeline(
    job_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    scheduler: SchedulerService = Depends(get_scheduler_service),
    limits: PlanLimitService = Depends(get_plan_limit_service),
):
    limits.ensure_can_run_pipeline(user_id)
    try:
        return PipelineRunResponse.model_validate(scheduler.run_for_job(user_id, job_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/scheduler/status", response_model=SchedulerStatusResponse)
def get_scheduler_status(
    scheduler: SchedulerService = Depends(get_scheduler_service),
):
    return SchedulerStatusResponse(**scheduler.scheduler_status())


@router.get("/scheduler/runs", response_model=list[PipelineRunResponse])
def list_pipeline_runs(
    limit: int = Query(default=20, ge=1, le=100),
    user_id: uuid.UUID = Depends(get_current_user_id),
    scheduler: SchedulerService = Depends(get_scheduler_service),
):
    return [PipelineRunResponse.model_validate(r) for r in scheduler.list_runs(user_id, limit=limit)]


@router.get("/scheduler/runs/{run_id}", response_model=PipelineRunResponse)
def get_pipeline_run(
    run_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    scheduler: SchedulerService = Depends(get_scheduler_service),
):
    run = scheduler.get_run(user_id, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return PipelineRunResponse.model_validate(run)


@router.get("/scheduler/notifications", response_model=list[PipelineNotificationResponse])
def list_pipeline_notifications(
    limit: int = Query(default=10, ge=1, le=50),
    unread_only: bool = Query(default=False),
    user_id: uuid.UUID = Depends(get_current_user_id),
    scheduler: SchedulerService = Depends(get_scheduler_service),
):
    notifications = scheduler.list_notifications(user_id, limit=limit, unread_only=unread_only)
    return [PipelineNotificationResponse.model_validate(n) for n in notifications]


@router.post("/scheduler/notifications/{notification_id}/read", response_model=PipelineNotificationResponse)
def mark_notification_read(
    notification_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    scheduler: SchedulerService = Depends(get_scheduler_service),
):
    notification = scheduler.mark_notification_read(user_id, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return PipelineNotificationResponse.model_validate(notification)
