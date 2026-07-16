import json
import uuid

from app.application.services.agent_context import format_location, format_profile
from app.application.services.llm_agent_base import LLMAgentBase
from app.domain.enums import AICapability, PromptName
from app.infrastructure.db.models import JobPosting, UserProfile


class JobScoringAgent(LLMAgentBase):
    def score(
        self,
        user_id: uuid.UUID,
        job: JobPosting,
        profile: UserProfile,
    ) -> dict:
        result, _ = self._invoke(
            user_id=user_id,
            job_id=job.id,
            agent_name="job_scoring",
            capability=AICapability.JOB_SCORING,
            prompt_name=PromptName.JOB_SCORING,
            variables={
                "job_title": job.title,
                "company": job.company,
                "location": format_location(job),
                "job_description": job.description,
                "job_classification": json.dumps(job.classification, indent=2),
                "user_profile": format_profile(profile),
                "immigration_goals": json.dumps(profile.immigration_goals, indent=2),
            },
        )
        return result
