from fastapi import APIRouter, Depends, HTTPException
import uuid

from app.api.schemas.user import ProfileResponse, ProfileUpdateRequest
from app.application.services.user_service import ProfileService
from app.dependencies import get_current_user_id, get_profile_service

router = APIRouter(tags=["profile"])


@router.get("/profile", response_model=ProfileResponse)
def get_profile(
    user_id: uuid.UUID = Depends(get_current_user_id),
    profile_svc: ProfileService = Depends(get_profile_service),
):
    try:
        return profile_svc.get_profile(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/profile", response_model=ProfileResponse)
def update_profile(
    req: ProfileUpdateRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    profile_svc: ProfileService = Depends(get_profile_service),
):
    data = req.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")
    return profile_svc.update_profile(user_id, data)
