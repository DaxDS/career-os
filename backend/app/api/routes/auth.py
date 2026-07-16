
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.schemas.user import (
    AuthConfigResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.application.services.user_service import AuthService
from app.config import Settings, get_settings
from app.dependencies import get_auth_service, get_current_user, get_job_service
from app.application.services.job_service import JobService
from app.infrastructure.db.models import User

router = APIRouter(tags=["auth"])


@router.get("/auth/config", response_model=AuthConfigResponse)
def auth_config(settings: Settings = Depends(get_settings)) -> AuthConfigResponse:
    return AuthConfigResponse(
        skip_auth=settings.dev_auth_bypass,
        default_email=settings.default_user_email,
    )


@router.post("/auth/auto", response_model=TokenResponse)
def auto_login(
    auth_svc: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
):
    if not settings.dev_auth_bypass:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Auto sign-in disabled")
    try:
        _, token = auth_svc.login(settings.default_user_email, settings.default_user_password)
        return TokenResponse(access_token=token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    req: RegisterRequest,
    auth_svc: AuthService = Depends(get_auth_service),
    job_svc: JobService = Depends(get_job_service),
):
    try:
        user, token = auth_svc.register(req.email, req.password)
        job_svc.seed_builtin_sources(user.id)
        return TokenResponse(access_token=token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/auth/login", response_model=TokenResponse)
def login(req: LoginRequest, auth_svc: AuthService = Depends(get_auth_service)):
    try:
        _, token = auth_svc.login(req.email, req.password)
        return TokenResponse(access_token=token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("/auth/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    return user
