import ast
from pathlib import Path

import pytest

from app.domain.enums import AICapability, CORE_AI_CAPABILITIES, PROMPT_TO_CAPABILITY, PromptName
from app.infrastructure.ai.capability_registry import CapabilityRegistry

SERVICES_DIR = Path(__file__).resolve().parents[2] / "app" / "application" / "services"


def test_core_capabilities_match_user_contract():
    expected = {
        "resume_tailoring",
        "cover_letter_generation",
        "email_generation",
        "job_classification",
        "ats_analysis",
        "resume_selection",
        "immigration_scoring",
        "job_scoring",
    }
    assert {c.value for c in CORE_AI_CAPABILITIES} == expected


def test_all_core_capabilities_in_registry():
    registry = CapabilityRegistry()
    assert registry.validate_core_capabilities() == []


def test_prompt_manifest_aligns_with_capabilities():
    registry = CapabilityRegistry()
    for _prompt, capability in PROMPT_TO_CAPABILITY.items():
        assert capability.value in registry.list_capabilities()


@pytest.mark.parametrize("capability", list(CORE_AI_CAPABILITIES))
def test_each_core_capability_has_routing(capability: AICapability):
    config = CapabilityRegistry().get(capability.value)
    assert config.primary.provider in {"openai", "anthropic"}
    assert config.primary.model


def test_application_services_do_not_import_llm_providers():
    """Business logic must use ModelRouterPort, not vendor SDKs."""
    violations: list[str] = []
    for path in SERVICES_DIR.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in ("openai", "anthropic"):
                        violations.append(f"{path.name}: import {alias.name}")
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] in ("openai", "anthropic"):
                    violations.append(f"{path.name}: from {node.module}")
    assert violations == []
