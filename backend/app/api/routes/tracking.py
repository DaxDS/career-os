import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from app.api.schemas.tracking import (
    ApplicationScreenshotResponse,
    ApplicationTrackingResponse,
    ApproveApplicationRequest,
    RecordSubmissionRequest,
    TrackedApplicationSummary,
    UploadScreenshotResponse,
    WithdrawApplicationRequest,
)
from app.application.services.application_tracking_service import ApplicationTrackingService
from app.dependencies import get_application_tracking_service, get_current_user_id

router = APIRouter(tags=["tracking"])


@router.get("/tracking/applications", response_model=list[TrackedApplicationSummary])
def list_tracked_applications(
    user_id: uuid.UUID = Depends(get_current_user_id),
    tracking: ApplicationTrackingService = Depends(get_application_tracking_service),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    try:
        rows = tracking.list_applications(user_id, status=status, limit=limit)
        return [
            TrackedApplicationSummary(
                application=ApplicationTrackingResponse.model_validate(app),
                job_title=job.title,
                company=job.company,
                location_province=job.location_province,
                job_status=job.status,
            )
            for app, job in rows
        ]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/tracking/jobs/{job_id}", response_model=ApplicationTrackingResponse)
def get_application_tracking(
    job_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    tracking: ApplicationTrackingService = Depends(get_application_tracking_service),
):
    try:
        return ApplicationTrackingResponse.model_validate(tracking.get_tracking(user_id, job_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/tracking/jobs/{job_id}/approve", response_model=ApplicationTrackingResponse)
def approve_application(
    job_id: uuid.UUID,
    body: ApproveApplicationRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    tracking: ApplicationTrackingService = Depends(get_application_tracking_service),
):
    try:
        application = tracking.approve(
            user_id, job_id, approved=body.approved, notes=body.notes
        )
        return ApplicationTrackingResponse.model_validate(application)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tracking/jobs/{job_id}/submit", response_model=ApplicationTrackingResponse)
def record_submission(
    job_id: uuid.UUID,
    body: RecordSubmissionRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    tracking: ApplicationTrackingService = Depends(get_application_tracking_service),
):
    try:
        application = tracking.record_submission(
            user_id,
            job_id,
            submission_url=body.submission_url,
            submission_method=body.submission_method,
            notes=body.notes,
            success=body.success,
        )
        return ApplicationTrackingResponse.model_validate(application)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tracking/jobs/{job_id}/withdraw", response_model=ApplicationTrackingResponse)
def withdraw_application(
    job_id: uuid.UUID,
    body: WithdrawApplicationRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    tracking: ApplicationTrackingService = Depends(get_application_tracking_service),
):
    try:
        application = tracking.withdraw(user_id, job_id, notes=body.notes)
        return ApplicationTrackingResponse.model_validate(application)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tracking/jobs/{job_id}/screenshots", response_model=UploadScreenshotResponse)
async def upload_screenshot(
    job_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    tracking: ApplicationTrackingService = Depends(get_application_tracking_service),
    file: UploadFile = File(...),
    caption: str = Form(""),
):
    try:
        content = await file.read()
        if not content:
            raise ValueError("Screenshot file is empty")
        screenshot = tracking.upload_screenshot(
            user_id,
            job_id,
            filename=file.filename or "screenshot.png",
            content=content,
            caption=caption,
        )
        return UploadScreenshotResponse(
            screenshot=ApplicationScreenshotResponse.model_validate(screenshot)
        )
    except ValueError as exc:
        status = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc
