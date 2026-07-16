from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.domain.v1_constants import CURRENT_LAYER
from app.dependencies import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "layer": CURRENT_LAYER,
    }


@router.get("/ready")
def readiness(db: Session = Depends(get_db)) -> dict:
    db.execute(text("SELECT 1"))
    return {"status": "ready", "database": "connected"}
