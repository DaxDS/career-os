import json
import uuid

from app.application.services.agent_context import format_master_resume_full
from app.application.services.llm_agent_base import LLMAgentBase
from app.domain.enums import AICapability, PromptName, WorkflowType
from app.infrastructure.db.models import JobPosting, MasterResume


class ResumeTailoringAgent(LLMAgentBase):
    def tailor(
        self,
        user_id: uuid.UUID,
        job: JobPosting,
        master_resume: MasterResume,
    ) -> dict:
        keywords = job.classification.get("required_skills", []) if job.classification else []
        result, _ = self._invoke(
            user_id=user_id,
            job_id=job.id,
            agent_name="resume_tailoring",
            capability=AICapability.RESUME_TAILORING,
            prompt_name=PromptName.RESUME_TAILORING,
            workflow_type=WorkflowType.DOCUMENT_GENERATION,
            variables={
                "master_resume": format_master_resume_full(master_resume),
                "job_title": job.title,
                "company": job.company,
                "job_description": job.description,
                "ats_keywords": json.dumps(keywords, indent=2),
                "job_classification": json.dumps(job.classification or {}, indent=2),
            },
        )
        return result
