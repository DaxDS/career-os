import uuid

from app.application.services.agent_context import (
    format_location,
    format_profile,
    key_qualifications_from_tailored,
    tailored_resume_summary,
)
from app.application.services.llm_agent_base import LLMAgentBase
from app.domain.enums import AICapability, PromptName, WorkflowType
from app.infrastructure.db.models import JobPosting, UserProfile


class CoverLetterAgent(LLMAgentBase):
    def generate(
        self,
        user_id: uuid.UUID,
        job: JobPosting,
        profile: UserProfile,
        tailored: dict,
    ) -> dict:
        result, _ = self._invoke(
            user_id=user_id,
            job_id=job.id,
            agent_name="cover_letter",
            capability=AICapability.COVER_LETTER_GENERATION,
            prompt_name=PromptName.COVER_LETTER,
            workflow_type=WorkflowType.DOCUMENT_GENERATION,
            variables={
                "candidate_name": profile.legal_name or "Candidate",
                "job_title": job.title,
                "company": job.company,
                "location": format_location(job),
                "job_description": job.description,
                "resume_summary": tailored_resume_summary(tailored),
                "key_qualifications": key_qualifications_from_tailored(tailored),
                "user_profile": format_profile(profile),
            },
        )
        return result
