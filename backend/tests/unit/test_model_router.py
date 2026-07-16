import pytest

from app.application.ports.llm import LLMMessage, LLMProviderPort, LLMResponse
from app.config import Settings
from app.infrastructure.ai.capability_registry import CapabilityRegistry
from app.infrastructure.ai.router import ModelRouter


class MockProvider(LLMProviderPort):
    def __init__(self, name: str, content: str, configured: bool = True):
        self._name = name
        self._content = content
        self._configured = configured

    @property
    def provider_name(self) -> str:
        return self._name

    def is_configured(self) -> bool:
        return self._configured

    def complete(self, model: str, messages: list[LLMMessage], **params) -> LLMResponse:
        return LLMResponse(content=self._content, provider=self._name, model=model)


def test_complete_for_capability_uses_primary():
    settings = Settings(ai_enabled=True)
    router = ModelRouter(
        CapabilityRegistry(),
        {"openai": MockProvider("openai", '{"role_family": "it"}')},
        settings,
    )
    response = router.complete_for_capability(
        "job_classification",
        [LLMMessage(role="user", content="classify")],
    )
    assert response.provider == "openai"
    assert "it" in response.content


def test_falls_back_when_primary_fails():
    settings = Settings(ai_enabled=True)

    class FailingAnthropic(MockProvider):
        def complete(self, model, messages, **params):
            raise RuntimeError("anthropic down")

    router = ModelRouter(
        CapabilityRegistry(),
        {
            "anthropic": FailingAnthropic("anthropic", ""),
            "openai": MockProvider("openai", '{"role_family": "ai"}'),
        },
        settings,
    )
    response = router.complete_for_capability(
        "resume_tailoring",
        [LLMMessage(role="user", content="tailor")],
    )
    assert response.provider == "openai"


def test_raises_when_all_routes_fail():
    settings = Settings(ai_enabled=True)

    class FailingProvider(MockProvider):
        def complete(self, model, messages, **params):
            raise RuntimeError("provider down")

    router = ModelRouter(
        CapabilityRegistry(),
        {"openai": FailingProvider("openai", "")},
        settings,
    )
    with pytest.raises(RuntimeError, match="All routes failed"):
        router.complete_for_capability(
            "job_classification",
            [LLMMessage(role="user", content="classify")],
        )


def test_ai_disabled_raises():
    settings = Settings(ai_enabled=False)
    router = ModelRouter(
        CapabilityRegistry(),
        {"openai": MockProvider("openai", "{}")},
        settings,
    )
    with pytest.raises(RuntimeError, match="AI is disabled"):
        router.complete_for_capability("job_classification", [])
