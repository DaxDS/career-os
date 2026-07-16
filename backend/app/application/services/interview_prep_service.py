"""Interview prep — question generation and answer coaching for applied jobs (Pro feature)."""

import json
import re
import uuid

from app.application.ports.application_repository import ApplicationRepositoryPort
from app.application.ports.llm import LLMMessage, ModelRouterPort
from app.domain.enums import AICapability, ApplicationStatus, DocumentType
from app.infrastructure.db.models import JobApplication

_ELIGIBLE_STATUSES = {ApplicationStatus.APPROVED.value, ApplicationStatus.SUBMITTED.value}


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


class InterviewPrepService:
    def __init__(self, application_repo: ApplicationRepositoryPort, router: ModelRouterPort):
        self._applications = application_repo
        self._router = router

    def _get_eligible_application(self, user_id: uuid.UUID, job_id: uuid.UUID) -> JobApplication:
        application = self._applications.get_by_job(user_id, job_id)
        if not application or not application.job:
            raise ValueError("Application not found for this job")
        if application.status not in _ELIGIBLE_STATUSES:
            raise ValueError(
                "Interview prep is available once an application is approved or submitted "
                f"(current status: {application.status})"
            )
        return application

    @staticmethod
    def _resume_summary(application: JobApplication) -> str:
        # Same document lookup pattern as review_queue_service._document_previews
        for doc in application.documents or []:
            if doc.document_type == DocumentType.TAILORED_RESUME.value:
                return (doc.content or {}).get("summary", "")
        return ""

    def generate_questions(self, user_id: uuid.UUID, job_id: uuid.UUID) -> dict:
        application = self._get_eligible_application(user_id, job_id)
        job = application.job
        prompt = f"""You are an interview coach. Generate likely interview questions for this candidate.

Job: {job.title} at {job.company}
Job description:
{(job.description or "")[:6000]}

Candidate's tailored resume summary:
{self._resume_summary(application) or "(not available)"}

Generate 5-8 questions this candidate is likely to be asked, mixing behavioral and role-specific technical questions. Base them on the actual job description and the candidate's background.

Respond with JSON only:
{{
  "questions": [
    {{"question": "...", "focus": "behavioral|technical|role_fit", "why": "one sentence on why this is likely"}}
  ]
}}"""
        response = self._router.complete_for_capability(
            AICapability.INTERVIEW_COACHING,
            [LLMMessage(role="user", content=prompt)],
        )
        data = _parse_json(response.content)
        questions = [
            {
                "question": str(q.get("question") or ""),
                "focus": str(q.get("focus") or "role_fit"),
                "why": str(q.get("why") or ""),
            }
            for q in data.get("questions") or []
            if isinstance(q, dict) and q.get("question")
        ][:8]
        if not questions:
            raise ValueError("AI did not return any questions — try again")
        return {"job_title": job.title, "company": job.company, "questions": questions}

    def coach_answer(
        self, user_id: uuid.UUID, job_id: uuid.UUID, question: str, answer: str
    ) -> dict:
        application = self._get_eligible_application(user_id, job_id)
        job = application.job
        prompt = f"""You are an interview coach. The candidate is interviewing for {job.title} at {job.company}.

Question asked:
{question}

Candidate's practice answer:
{answer}

Job description (for context):
{(job.description or "")[:4000]}

Give honest, specific feedback. Score harshly enough to be useful.

Respond with JSON only:
{{
  "score": <0-100 integer>,
  "strengths": ["what worked", ...],
  "improvements": ["specific fix", ...],
  "suggested_answer": "a stronger version of their answer, keeping their real experience"
}}"""
        response = self._router.complete_for_capability(
            AICapability.INTERVIEW_COACHING,
            [LLMMessage(role="user", content=prompt)],
        )
        data = _parse_json(response.content)
        return {
            "score": max(0, min(100, int(data.get("score") or 0))),
            "strengths": [str(s) for s in data.get("strengths") or []][:5],
            "improvements": [str(s) for s in data.get("improvements") or []][:5],
            "suggested_answer": str(data.get("suggested_answer") or ""),
        }
