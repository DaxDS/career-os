import json
import uuid

from app.application.services.agent_context import (
    format_location,
    format_master_resumes,
    format_profile,
)
from app.application.services.llm_agent_base import LLMAgentBase
from app.domain.enums import AICapability, PromptName
from app.infrastructure.db.models import JobPosting, MasterResume, UserProfile


class ResumeSelectionAgent(LLMAgentBase):
    def select(
        self,
        user_id: uuid.UUID,
        job: JobPosting,
        profile: UserProfile,
        resumes: list[MasterResume],
    ) -> dict:
        if not resumes:
            raise ValueError("No master resumes available for selection")

        result, _ = self._invoke(
            user_id=user_id,
            job_id=job.id,
            agent_name="resume_selection",
            capability=AICapability.RESUME_SELECTION,
            prompt_name=PromptName.RESUME_SELECTION,
            variables={
                "job_title": job.title,
                "company": job.company,
                "location": format_location(job),
                "job_description": job.description,
                "job_classification": json.dumps(job.classification, indent=2),
                "master_resumes": format_master_resumes(resumes),
                "user_profile": format_profile(profile),
            },
        )

        selected_id = result.get("selected_resume_id")
        if selected_id and self._audit:
            self._audit.record_resume_selection(
                job_id=job.id,
                selected_resume_id=selected_id,
                confidence=float(result.get("confidence", 0)),
                rationale=result.get("rationale", ""),
                details={"agent": "resume_selection", "capability": AICapability.RESUME_SELECTION.value},
            )
        return result
