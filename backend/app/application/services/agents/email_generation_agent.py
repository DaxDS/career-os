import uuid

from app.application.services.agent_context import (
    format_profile,
    tailored_resume_highlights,
)
from app.application.services.llm_agent_base import LLMAgentBase
from app.domain.enums import AICapability, PromptName, WorkflowType
from app.infrastructure.db.models import JobPosting, UserProfile


class EmailGenerationAgent(LLMAgentBase):
    def generate(
        self,
        user_id: uuid.UUID,
        job: JobPosting,
        profile: UserProfile,
        tailored: dict,
    ) -> dict:
        job_summary = job.description[:800] if job.description else job.title
        result, _ = self._invoke(
            user_id=user_id,
            job_id=job.id,
            agent_name="email_generation",
            capability=AICapability.EMAIL_GENERATION,
            prompt_name=PromptName.EMAIL_GENERATION,
            workflow_type=WorkflowType.DOCUMENT_GENERATION,
            variables={
                "candidate_name": profile.legal_name or "Candidate",
                "job_title": job.title,
                "company": job.company,
                "job_summary": job_summary,
                "resume_highlights": tailored_resume_highlights(tailored),
                "user_profile": format_profile(profile),
            },
        )
        return result
