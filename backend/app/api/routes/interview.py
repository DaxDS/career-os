import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.application.services.interview_prep_service import InterviewPrepService
from app.application.services.plan_limit_service import PlanLimitService
from app.dependencies import (
    get_current_user_id,
    get_interview_prep_service,
    get_plan_limit_service,
)

router = APIRouter(tags=["interview"])


class InterviewQuestion(BaseModel):
    question: str
    focus: str
    why: str


class InterviewQuestionsResponse(BaseModel):
    job_title: str
    company: str
    questions: list[InterviewQuestion]


class CoachAnswerRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    answer: str = Field(..., min_length=1, max_length=10_000)


class CoachAnswerResponse(BaseModel):
    score: int
    strengths: list[str]
    improvements: list[str]
    suggested_answer: str


@router.post("/interview/jobs/{job_id}/questions", response_model=InterviewQuestionsResponse)
def generate_interview_questions(
    job_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    prep: InterviewPrepService = Depends(get_interview_prep_service),
    limits: PlanLimitService = Depends(get_plan_limit_service),
):
    limits.ensure_pro_feature(user_id, "Interview prep")
    try:
        return InterviewQuestionsResponse(**prep.generate_questions(user_id, job_id))
    except ValueError as exc:
        status = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/interview/jobs/{job_id}/coach", response_model=CoachAnswerResponse)
def coach_interview_answer(
    job_id: uuid.UUID,
    body: CoachAnswerRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    prep: InterviewPrepService = Depends(get_interview_prep_service),
    limits: PlanLimitService = Depends(get_plan_limit_service),
):
    limits.ensure_pro_feature(user_id, "Interview prep")
    try:
        return CoachAnswerResponse(**prep.coach_answer(user_id, job_id, body.question, body.answer))
    except ValueError as exc:
        status = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
