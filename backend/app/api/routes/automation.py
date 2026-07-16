import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas.automation import (
    AutomationActionLogResponse,
    AutomationRunResponse,
    BrowserSessionResponse,
    StartAutomationRequest,
    StartAutomationResponse,
)
from app.application.services.application_automation_service import ApplicationAutomationService
from app.dependencies import get_application_automation_service, get_current_user_id

router = APIRouter(tags=["automation"])


@router.post("/automation/jobs/{job_id}/submit", response_model=StartAutomationResponse)
async def start_browser_submission(
    job_id: uuid.UUID,
    body: StartAutomationRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    automation: ApplicationAutomationService = Depends(get_application_automation_service),
):
    try:
        result = await automation.start_submission(
            user_id,
            job_id,
            stop_before_submit=body.stop_before_submit,
        )
        return StartAutomationResponse(
            run_id=uuid.UUID(result["run_id"]),
            session_id=uuid.UUID(result["session_id"]) if result.get("session_id") else None,
            status=result["status"],
            submitted=result.get("submitted", False),
            connector_key=result.get("connector_key", ""),
            browser=result.get("browser", ""),
            paused_for_captcha=result.get("paused_for_captcha", False),
            failure_reason=result.get("failure_reason"),
            result=result.get("result", {}),
        )
    except ValueError as exc:
        status = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/automation/sessions/{session_id}/resume", response_model=StartAutomationResponse)
async def resume_after_captcha(
    session_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    automation: ApplicationAutomationService = Depends(get_application_automation_service),
):
    try:
        result = await automation.resume_after_captcha(user_id, session_id)
        return StartAutomationResponse(
            run_id=uuid.UUID(result["run_id"]),
            session_id=uuid.UUID(result["session_id"]) if result.get("session_id") else None,
            status=result["status"],
            submitted=result.get("submitted", False),
            connector_key=result.get("connector_key", ""),
            browser=result.get("browser", ""),
            paused_for_captcha=result.get("paused_for_captcha", False),
            failure_reason=result.get("failure_reason"),
            result=result.get("result", {}),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/automation/runs/{run_id}", response_model=AutomationRunResponse)
def get_automation_run(
    run_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    automation: ApplicationAutomationService = Depends(get_application_automation_service),
):
    try:
        return AutomationRunResponse.model_validate(automation.get_run(user_id, run_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/automation/jobs/{job_id}/runs", response_model=list[AutomationRunResponse])
def list_job_automation_runs(
    job_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    automation: ApplicationAutomationService = Depends(get_application_automation_service),
):
    runs = automation.list_runs(user_id, job_id)
    return [AutomationRunResponse.model_validate(r) for r in runs]


@router.get("/automation/runs/{run_id}/actions", response_model=list[AutomationActionLogResponse])
def list_automation_actions(
    run_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    automation: ApplicationAutomationService = Depends(get_application_automation_service),
):
    try:
        logs = automation.get_action_logs(user_id, run_id)
        return [AutomationActionLogResponse.model_validate(log) for log in logs]
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/automation/sessions", response_model=list[BrowserSessionResponse])
def list_browser_sessions(
    user_id: uuid.UUID = Depends(get_current_user_id),
    automation: ApplicationAutomationService = Depends(get_application_automation_service),
):
    return [BrowserSessionResponse.model_validate(s) for s in automation.list_sessions(user_id)]
