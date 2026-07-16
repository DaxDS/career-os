import json
import uuid
from typing import Any

from app.application.ports.llm import LLMMessage, ModelRouterPort
from app.application.ports.prompts import PromptRegistryPort
from app.application.ports.user_repository import UserRepositoryPort
from app.config import Settings
from app.domain.enums import AICapability, PromptName
from app.infrastructure.ai.json_parser import extract_json_object
from app.infrastructure.db.models import JobPosting, UserProfile
from app.infrastructure.logging.setup import get_logger
from app.infrastructure.prompts.renderer import PromptRenderer

logger = get_logger(__name__)


class JobScoringService:
    """LLM job scoring — scores are returned but not persisted until Layer 5+."""

    def __init__(
        self,
        router: ModelRouterPort,
        prompt_registry: PromptRegistryPort,
        user_repo: UserRepositoryPort,
        settings: Settings,
        renderer: PromptRenderer | None = None,
    ):
        self._router = router
        self._prompts = prompt_registry
        self._user_repo = user_repo
        self._settings = settings
        self._renderer = renderer or PromptRenderer()

    def score_job(self, user_id: uuid.UUID, job: JobPosting) -> dict[str, Any]:
        if not self._settings.ai_enabled:
            raise ValueError("AI is disabled. Set AI_ENABLED=true and configure API keys.")

        profile = self._user_repo.get_profile(user_id)
        if not profile:
            raise ValueError("User profile not found")

        template = self._prompts.get_active_content(PromptName.JOB_SCORING)
        rendered = self._renderer.render(
            template,
            {
                "job_title": job.title,
                "company": job.company,
                "location": self._format_location(job),
                "job_description": job.description,
                "job_classification": json.dumps(job.classification, indent=2),
                "user_profile": self._format_profile(profile),
                "immigration_goals": json.dumps(profile.immigration_goals, indent=2),
            },
        )
        response = self._router.complete_for_capability(
            AICapability.JOB_SCORING,
            [LLMMessage(role="user", content=rendered)],
        )
        scores = extract_json_object(response.content)
        scores["scoring_method"] = "llm"
        scores["llm_provider"] = response.provider
        scores["llm_model"] = response.model
        logger.info("job_scored", job_id=str(job.id), user_id=str(user_id))
        return scores

    @staticmethod
    def _format_location(job: JobPosting) -> str:
        parts = [p for p in (job.location_city, job.location_province) if p]
        return ", ".join(parts)

    @staticmethod
    def _format_profile(profile: UserProfile) -> str:
        return json.dumps(
            {
                "legal_name": profile.legal_name,
                "location_city": profile.location_city,
                "location_province": profile.location_province,
                "work_authorization": profile.work_authorization,
                "preferred_provinces": profile.preferred_provinces,
                "preferred_job_categories": profile.preferred_job_categories,
                "skills": profile.skills,
                "salary_min_cad": profile.salary_min_cad,
                "salary_max_cad": profile.salary_max_cad,
                "remote_preference": profile.remote_preference,
            },
            indent=2,
        )
