import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.schemas.review import (
    BatchReviewItemResponse,
    BatchReviewRequest,
    BatchReviewResponse,
    ReviewDecisionRequest,
    ReviewDecisionResponse,
    ReviewDetailResponse,
    ReviewQueueItemResponse,
    ReviewStatsResponse,
)
from app.application.services.review_queue_service import ReviewQueueService
from app.dependencies import get_current_user_id, get_review_queue_service
from app.domain.enums import ReviewDecision

router = APIRouter(tags=["review"])


def _parse_decision(value: str) -> ReviewDecision:
    try:
        return ReviewDecision(value)
    except ValueError as exc:
        valid = ", ".join(d.value for d in ReviewDecision)
        raise ValueError(f"Invalid decision '{value}'. Must be one of: {valid}") from exc


@router.get("/review/queue", response_model=list[ReviewQueueItemResponse])
def get_review_queue(
    user_id: uuid.UUID = Depends(get_current_user_id),
    review: ReviewQueueService = Depends(get_review_queue_service),
    min_overall_score: int | None = Query(None, ge=0, le=100),
    limit: int = Query(50, ge=1, le=200),
):
    items = review.get_queue(user_id, min_overall_score=min_overall_score, limit=limit)
    return [ReviewQueueItemResponse.model_validate(item.__dict__) for item in items]


@router.get("/review/stats", response_model=ReviewStatsResponse)
def get_review_stats(
    user_id: uuid.UUID = Depends(get_current_user_id),
    review: ReviewQueueService = Depends(get_review_queue_service),
):
    return ReviewStatsResponse(**review.get_stats(user_id))


@router.get("/review/jobs/{job_id}", response_model=ReviewDetailResponse)
def get_review_detail(
    job_id: uuid.UUID,
    user_id: uuid.UUID = Depends(get_current_user_id),
    review: ReviewQueueService = Depends(get_review_queue_service),
):
    try:
        detail = review.get_review_detail(user_id, job_id)
        app = detail.application
        return ReviewDetailResponse(
            application_id=app.id,
            job_id=job_id,
            status=app.status,
            version=app.version,
            ats_fact_check_passed=app.ats_fact_check_passed,
            review_notes=app.review_notes,
            generated_at=app.generated_at,
            title=detail.job.title,
            company=detail.job.company,
            location_province=detail.job.location_province,
            overall_score=detail.score.overall_score if detail.score else None,
            match_score=detail.score.match_score if detail.score else None,
            ats_score=detail.score.ats_score if detail.score else None,
            immigration_score=detail.score.immigration_score if detail.score else None,
            document_previews=detail.document_previews,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/review/jobs/{job_id}/decide", response_model=ReviewDecisionResponse)
def decide_review(
    job_id: uuid.UUID,
    body: ReviewDecisionRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    review: ReviewQueueService = Depends(get_review_queue_service),
):
    try:
        decision = _parse_decision(body.decision)
        application = review.decide(user_id, job_id, decision, notes=body.notes)
        return ReviewDecisionResponse(
            job_id=job_id,
            status=application.status,
            review_notes=application.review_notes,
            reviewed_at=application.reviewed_at,
        )
    except ValueError as exc:
        status = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@router.post("/review/batch", response_model=BatchReviewResponse)
def batch_review_decide(
    body: BatchReviewRequest,
    user_id: uuid.UUID = Depends(get_current_user_id),
    review: ReviewQueueService = Depends(get_review_queue_service),
):
    try:
        decision = _parse_decision(body.decision)
        results = review.batch_decide(user_id, body.job_ids, decision, notes=body.notes)
        response_items = [
            BatchReviewItemResponse(
                job_id=r.job_id,
                success=r.success,
                status=r.status,
                error=r.error,
            )
            for r in results
        ]
        succeeded = sum(1 for r in response_items if r.success)
        return BatchReviewResponse(
            results=response_items,
            succeeded=succeeded,
            failed=len(response_items) - succeeded,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
