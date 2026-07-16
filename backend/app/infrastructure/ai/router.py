from app.application.ports.llm import LLMMessage, LLMProviderPort, LLMResponse, ModelRouterPort
from app.config import Settings
from app.domain.enums import AICapability
from app.infrastructure.ai.capability_registry import CapabilityRegistry, ModelRoute
from app.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)


class ModelRouter(ModelRouterPort):
    def __init__(
        self,
        registry: CapabilityRegistry,
        providers: dict[str, LLMProviderPort],
        settings: Settings,
    ):
        self._registry = registry
        self._providers = providers
        self._settings = settings

    def complete_for_capability(
        self, capability: AICapability | str, messages: list[LLMMessage]
    ) -> LLMResponse:
        if not self._settings.ai_enabled:
            raise RuntimeError("AI is disabled (AI_ENABLED=false)")

        capability_key = capability.value if isinstance(capability, AICapability) else capability
        config = self._registry.get(capability_key)
        errors: list[str] = []

        for route in (config.primary, config.fallback):
            if route is None:
                continue
            try:
                return self._complete_route(route, messages)
            except Exception as exc:
                errors.append(f"{route.provider}/{route.model}: {exc}")
                logger.warning(
                    "llm_route_failed",
                    capability=capability_key,
                    provider=route.provider,
                    model=route.model,
                    error=str(exc),
                )

        raise RuntimeError(
            f"All routes failed for capability '{capability}': {'; '.join(errors)}"
        )

    def _complete_route(self, route: ModelRoute, messages: list[LLMMessage]) -> LLMResponse:
        provider = self._providers.get(route.provider)
        if provider is None:
            raise RuntimeError(f"Provider not registered: {route.provider}")
        if not provider.is_configured():
            raise RuntimeError(f"Provider not configured: {route.provider}")
        return provider.complete(route.model, messages, **route.params)

    def list_capabilities(self) -> list[str]:
        return self._registry.list_capabilities()

    def provider_status(self) -> dict[str, bool]:
        return {
            name: provider.is_configured() for name, provider in self._providers.items()
        }
