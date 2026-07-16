import json
import uuid

from app.application.services.agent_context import (
    format_profile,
    pick_resume_for_ats,
    resume_text_for_ats,
)
from app.application.services.llm_agent_base import LLMAgentBase
from app.domain.enums import AICapability, PromptName, WorkflowType
from app.infrastructure.db.models import JobPosting, MasterResume, UserProfile


class AtsAnalysisAgent(LLMAgentBase):
    """Pre-tailoring ATS analysis using master resume as proxy (Layer 5)."""

    def analyze(
        self,
        user_id: uuid.UUID,
        job: JobPosting,
        profile: UserProfile,
        resumes: list[MasterResume],
    ) -> dict:
        master = pick_resume_for_ats(resumes, job.role_family)
        master_text = resume_text_for_ats(master) if master else format_profile(profile)
        keywords = job.classification.get("required_skills", []) if job.classification else []

        result, _ = self._invoke(
            user_id=user_id,
            job_id=job.id,
            agent_name="ats_analysis",
            capability=AICapability.ATS_ANALYSIS,
            prompt_name=PromptName.ATS_ANALYSIS,
            variables={
                "master_resume": master_text,
                "tailored_resume": (
                    "[Pre-tailoring analysis] No tailored resume yet. "
                    "Evaluating master resume keyword alignment only."
                ),
                "job_description": job.description,
                "ats_keywords": json.dumps(keywords, indent=2),
            },
        )
        result["analysis_mode"] = "pre_tailoring"
        return result

    def analyze_post_tailor(
        self,
        user_id: uuid.UUID,
        job: JobPosting,
        master: MasterResume,
        tailored: dict,
    ) -> dict:
        from app.application.services.agent_context import format_tailored_resume_text

        keywords = job.classification.get("required_skills", []) if job.classification else []
        result, _ = self._invoke(
            user_id=user_id,
            job_id=job.id,
            agent_name="ats_analysis",
            capability=AICapability.ATS_ANALYSIS,
            prompt_name=PromptName.ATS_ANALYSIS,
            workflow_type=WorkflowType.DOCUMENT_GENERATION,
            variables={
                "master_resume": resume_text_for_ats(master),
                "tailored_resume": format_tailored_resume_text(tailored),
                "job_description": job.description,
                "ats_keywords": json.dumps(keywords, indent=2),
            },
        )
        result["analysis_mode"] = "post_tailoring"
        return result
