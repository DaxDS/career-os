import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.schemas.documents import (
    ApplicationDocumentResponse,
    GenerateDocumentsResponse,
    JobApplicationResponse,
)
from app.application.services.document_generation_service import DocumentGenerationService
from app.dependencies import get_current_user_id, get_document_generation_service

router = APIRouter(tags=["documents"])


@router.post("/documents/jobs/{job_id}/generate", response_model=GenerateDocumentsResponse)
def generate_documents(
    job_id: uuid.UUID,
    force: bool = Query(False, description="Regenerate even if documents already exist"),
    user_id: uuid.UUID = Depends(get_current_user_id),
    doc_service: DocumentGenerationService = Depends(get_document_generation_service),
):
    try:
        application = doc_service.generate_documents(user_id, job_id, force=force)
        return GenerateDocumentsResponse(
            application=JobApplicationResponse.model_validate(application),
            regenerated=force,
        )
    except ValueError as exc:
        status = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/documents/jobs/{job_id}", response_model=JobApplicationResponse)
def get_application_documents(
    job_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    doc_service: DocumentGenerationService = Depends(get_document_generation_service),
):
    try:
        application = doc_service.get_application(user_id, job_id)
        return JobApplicationResponse.model_validate(application)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/documents/jobs/{job_id}/artifacts/{document_type}",
    response_model=ApplicationDocumentResponse,
)
def get_document_artifact(
    job_id: uuid.UUID,
    document_type: str,
    user_id: uuid.UUID = Depends(get_current_user_id),
    doc_service: DocumentGenerationService = Depends(get_document_generation_service),
):
    try:
        document = doc_service.get_document(user_id, job_id, document_type)
        return ApplicationDocumentResponse.model_validate(document)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
