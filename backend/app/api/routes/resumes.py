import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.api.schemas.resume import MasterResumeResponse, ResumeLabelsResponse, ResumeVersionResponse
from app.application.services.plan_limit_service import PlanLimitService
from app.application.services.resume_service import ResumeService
from app.dependencies import get_current_user_id, get_plan_limit_service, get_resume_service

router = APIRouter(tags=["resumes"])


def _to_response(resume) -> MasterResumeResponse:
    parsed = resume.parsed_content or {}
    return MasterResumeResponse(
        id=resume.id,
        label=resume.label,
        category=resume.category,
        original_filename=resume.original_filename,
        is_active=resume.is_active,
        version=resume.version,
        role_families=resume.role_families,
        classification=resume.classification,
        content_hash=resume.content_hash,
        uploaded_at=resume.uploaded_at,
        parsed_preview={
            "summary": parsed.get("summary", "")[:200],
            "skills": parsed.get("skills", [])[:15],
            "experience_count": len(parsed.get("experience", [])),
            "education_count": len(parsed.get("education", [])),
        },
    )


@router.get("/resumes/labels", response_model=ResumeLabelsResponse)
def list_resume_labels(resume_svc: ResumeService = Depends(get_resume_service)):
    return ResumeLabelsResponse(labels=resume_svc.list_labels())


@router.get("/resumes/master", response_model=list[MasterResumeResponse])
def list_master_resumes(
    user_id: uuid.UUID = Depends(get_current_user_id),
    resume_svc: ResumeService = Depends(get_resume_service),
):
    return [_to_response(r) for r in resume_svc.list_master_resumes(user_id)]


@router.post("/resumes/master", response_model=MasterResumeResponse, status_code=201)
async def upload_master_resume(
    label: str = Form(...),
    file: UploadFile = File(...),
    user_id: uuid.UUID = Depends(get_current_user_id),
    resume_svc: ResumeService = Depends(get_resume_service),
    limits: PlanLimitService = Depends(get_plan_limit_service),
):
    limits.ensure_can_upload_resume(user_id, label)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    try:
        resume = await resume_svc.upload_master_resume(
            user_id, label, content, file.filename or "resume.txt"
        )
        return _to_response(resume)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/resumes/master/{resume_id}", response_model=MasterResumeResponse)
def get_master_resume(
    resume_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    resume_svc: ResumeService = Depends(get_resume_service),
):
    try:
        return _to_response(resume_svc.get_master_resume(user_id, resume_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/resumes/master/{resume_id}/versions", response_model=list[ResumeVersionResponse])
def list_resume_versions(
    resume_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    resume_svc: ResumeService = Depends(get_resume_service),
):
    try:
        versions = resume_svc.list_versions(user_id, resume_id)
        return [ResumeVersionResponse.model_validate(v) for v in versions]
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/resumes/master/{resume_id}/download")
def download_master_resume(
    resume_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    resume_svc: ResumeService = Depends(get_resume_service),
):
    try:
        resume = resume_svc.get_master_resume(user_id, resume_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    path = Path(resume.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(str(path), filename=resume.original_filename)


@router.delete("/resumes/master/{resume_id}")
def deactivate_master_resume(
    resume_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    resume_svc: ResumeService = Depends(get_resume_service),
):
    try:
        resume_svc.deactivate(user_id, resume_id)
        return {"status": "deactivated"}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
