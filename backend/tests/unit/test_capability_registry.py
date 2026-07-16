from pathlib import Path

import pytest

from app.infrastructure.ai.capability_registry import CapabilityRegistry


def test_loads_all_capabilities():
    registry = CapabilityRegistry()
    capabilities = registry.list_capabilities()
    assert "job_classification" in capabilities
    assert "job_scoring" in capabilities
    assert "immigration_scoring" in capabilities
    assert len(capabilities) >= 10


def test_get_capability_config():
    registry = CapabilityRegistry()
    config = registry.get("job_classification")
    assert config.primary.provider == "openai"
    assert config.primary.model == "gpt-4o-mini"
    assert config.primary.params["temperature"] == 0.0


def test_core_capabilities_registered():
    registry = CapabilityRegistry()
    assert registry.validate_core_capabilities() == []


def test_unknown_capability_raises():
    registry = CapabilityRegistry()
    with pytest.raises(KeyError, match="Unknown capability"):
        registry.get("nonexistent")
