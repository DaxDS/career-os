import pytest

from app.application.ports.llm import LLMMessage, LLMProviderPort, LLMResponse, ModelRouterPort
from app.application.services.hybrid_job_classifier import HybridJobClassifier
from app.config import Settings
from app.infrastructure.prompts.renderer import PromptRenderer


class StubRouter(ModelRouterPort):
    def __init__(self, content: str):
        self._content = content

    def complete_for_capability(self, capability, messages):
        return LLMResponse(content=self._content, provider="openai", model="gpt-4o-mini")

    def list_capabilities(self):
        return []

    def provider_status(self):
        return {"openai": True}


class StubPrompts:
    def get_active_content(self, name):
        return "Title: {{job_title}}\n{{job_description}}"


def test_uses_rules_when_ai_disabled():
    classifier = HybridJobClassifier(
        StubRouter('{"role_family": "ai"}'),
        StubPrompts(),
        Settings(ai_enabled=False),
    )
    result = classifier.classify(
        "Manufacturing Production Operator",
        "PLC and quality control in food processing",
    )
    assert result["classification_method"] == "rule_based"
    assert result["role_family"] == "production"


def test_uses_llm_when_ai_enabled():
    llm_json = '{"role_family": "ai", "seniority": "senior", "classification_confidence": 0.95}'
    classifier = HybridJobClassifier(
        StubRouter(llm_json),
        StubPrompts(),
        Settings(ai_enabled=True, openai_api_key="test-key"),
        renderer=PromptRenderer(),
    )
    result = classifier.classify("ML Engineer", "deep learning and NLP")
    assert result["classification_method"] == "llm"
    assert result["role_family"] == "ai"


def test_falls_back_on_llm_failure():
    class FailingRouter(StubRouter):
        def complete_for_capability(self, capability, messages):
            raise RuntimeError("API down")

    classifier = HybridJobClassifier(
        FailingRouter(""),
        StubPrompts(),
        Settings(ai_enabled=True, openai_api_key="test-key"),
    )
    result = classifier.classify(
        "Manufacturing Production Operator",
        "PLC monitoring in plant",
    )
    assert result["classification_method"] == "rule_based_fallback"
    assert result["role_family"] == "production"
