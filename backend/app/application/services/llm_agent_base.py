import uuid
from typing import Any

from app.application.ports.audit import AuditPort
from app.application.ports.llm import LLMMessage, LLMResponse, ModelRouterPort
from app.application.ports.prompts import PromptRegistryPort
from app.application.ports.score_repository import AgentRunRepositoryPort
from app.config import Settings
from app.domain.enums import AICapability, AgentRunStatus, PromptName, WorkflowType
from app.infrastructure.ai.json_parser import extract_json_object
from app.infrastructure.db.models import AgentRun
from app.infrastructure.logging.setup import get_logger
from app.infrastructure.prompts.renderer import PromptRenderer

logger = get_logger(__name__)


class LLMAgentBase:
    """Base class for Layer 5 intelligence agents — capability routing only."""

    def __init__(
        self,
        router: ModelRouterPort,
        prompts: PromptRegistryPort,
        settings: Settings,
        agent_runs: AgentRunRepositoryPort | None = None,
        audit: AuditPort | None = None,
        renderer: PromptRenderer | None = None,
    ):
        self._router = router
        self._prompts = prompts
        self._settings = settings
        self._agent_runs = agent_runs
        self._audit = audit
        self._renderer = renderer or PromptRenderer()

    def _require_ai(self) -> None:
        if not self._settings.ai_enabled:
            raise ValueError("AI is disabled. Set AI_ENABLED=true and configure API keys.")

    def _invoke(
        self,
        *,
        user_id: uuid.UUID,
        job_id: uuid.UUID,
        agent_name: str,
        capability: AICapability,
        prompt_name: PromptName,
        variables: dict[str, Any],
        workflow_type: WorkflowType = WorkflowType.SINGLE_JOB,
    ) -> tuple[dict[str, Any], LLMResponse]:
        self._require_ai()
        run: AgentRun | None = None
        if self._agent_runs:
            run = self._agent_runs.create(
                AgentRun(
                    user_id=user_id,
                    job_id=job_id,
                    workflow_type=workflow_type.value,
                    agent_name=agent_name,
                    capability=capability.value,
                    status=AgentRunStatus.RUNNING.value,
                    input_snapshot={"prompt": prompt_name.value, "variables_keys": list(variables)},
                )
            )

        try:
            template = self._prompts.get_active_content(prompt_name)
            rendered = self._renderer.render(template, variables)
            response = self._router.complete_for_capability(
                capability,
                [LLMMessage(role="user", content=rendered)],
            )
            parsed = extract_json_object(response.content)
            parsed["agent"] = agent_name
            parsed["capability"] = capability.value
            parsed["llm_provider"] = response.provider
            parsed["llm_model"] = response.model

            if self._agent_runs and run:
                self._agent_runs.complete(
                    run.id,
                    status=AgentRunStatus.COMPLETED.value,
                    output=parsed,
                    llm_provider=response.provider,
                    llm_model=response.model,
                )
            if self._audit:
                self._audit.record_agent_decision(
                    agent_name=agent_name,
                    entity_type="job",
                    entity_id=job_id,
                    decision=parsed,
                )
            return parsed, response
        except Exception as exc:
            logger.warning("agent_invoke_failed", agent=agent_name, error=str(exc))
            if self._agent_runs and run:
                self._agent_runs.complete(
                    run.id,
                    status=AgentRunStatus.FAILED.value,
                    output={},
                    error_message=str(exc),
                )
            raise
