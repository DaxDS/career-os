import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.application.services.linkedin_optimizer_service import LinkedInOptimizerService
from app.dependencies import get_current_user_id, get_linkedin_optimizer

router = APIRouter(tags=["linkedin"])


class LinkedInOptimizeRequest(BaseModel):
    headline: str = Field("", max_length=500)
    about: str = Field("", max_length=10_000)
    target_role_family: str = Field(..., min_length=1, max_length=50)


class LinkedInSuggestion(BaseModel):
    section: str
    issue: str
    fix: str


class LinkedInOptimizeResponse(BaseModel):
    keyword_score: int
    missing_keywords: list[str]
    headline_rewrite: str
    about_rewrite: str
    suggestions: list[LinkedInSuggestion]


@router.post("/linkedin/optimize", response_model=LinkedInOptimizeResponse)
def optimize_linkedin_profile(
    body: LinkedInOptimizeRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    optimizer: LinkedInOptimizerService = Depends(get_linkedin_optimizer),
):
    del user_id
    if not body.headline.strip() and not body.about.strip():
        raise HTTPException(status_code=400, detail="Paste your headline or About section first")
    try:
        result = optimizer.optimize(body.headline, body.about, body.target_role_family)
        return LinkedInOptimizeResponse(**result)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=502, detail=f"AI response could not be parsed: {exc}") from exc
