from app.application.ports.classifier import JobClassifierPort
from app.application.ports.llm import LLMMessage, ModelRouterPort
from app.application.ports.prompts import PromptRegistryPort
from app.application.services.job_classifier import RuleBasedJobClassifier
from app.config import Settings
from app.domain.enums import AICapability, PromptName
from app.infrastructure.ai.json_parser import extract_json_object
from app.infrastructure.logging.setup import get_logger
from app.infrastructure.prompts.renderer import PromptRenderer

logger = get_logger(__name__)


class HybridJobClassifier(JobClassifierPort):
    """LLM classification with rule-based fallback."""

    def __init__(
        self,
        router: ModelRouterPort,
        prompt_registry: PromptRegistryPort,
        settings: Settings,
        rule_classifier: RuleBasedJobClassifier | None = None,
        renderer: PromptRenderer | None = None,
    ):
        self._router = router
        self._prompts = prompt_registry
        self._settings = settings
        self._rules = rule_classifier or RuleBasedJobClassifier()
        self._renderer = renderer or PromptRenderer()

    def classify(
        self,
        title: str,
        description: str,
        remote_type: str | None = None,
        *,
        company: str = "",
        location: str = "",
    ) -> dict:
        if not self._settings.ai_enabled:
            return self._rules.classify(
                title, description, remote_type, company=company, location=location
            )

        try:
            template = self._prompts.get_active_content(PromptName.JOB_CLASSIFICATION)
            rendered = self._renderer.render(
                template,
                {
                    "job_title": title,
                    "company": company,
                    "location": location,
                    "job_description": description,
                },
            )
            response = self._router.complete_for_capability(
                AICapability.JOB_CLASSIFICATION,
                [LLMMessage(role="user", content=rendered)],
            )
            parsed = extract_json_object(response.content)
            parsed["classification_method"] = "llm"
            parsed["llm_provider"] = response.provider
            parsed["llm_model"] = response.model
            if remote_type and not parsed.get("remote_type"):
                parsed["remote_type"] = remote_type
            return parsed
        except Exception as exc:
            logger.warning("llm_classification_failed", error=str(exc), title=title)
            result = self._rules.classify(
                title, description, remote_type, company=company, location=location
            )
            result["classification_method"] = "rule_based_fallback"
            result["fallback_reason"] = str(exc)
            return result
