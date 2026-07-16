from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.domain.enums import CORE_AI_CAPABILITIES
CAPABILITIES_PATH = Path(__file__).parent / "capabilities.yaml"


@dataclass(frozen=True)
class ModelRoute:
    provider: str
    model: str
    params: dict[str, Any]


@dataclass(frozen=True)
class CapabilityConfig:
    name: str
    primary: ModelRoute
    fallback: ModelRoute | None


class CapabilityRegistry:
    def __init__(self, path: Path | None = None):
        self._path = path or CAPABILITIES_PATH
        self._capabilities = self._load()

    def _load(self) -> dict[str, CapabilityConfig]:
        with open(self._path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        raw = data.get("capabilities", {})
        result: dict[str, CapabilityConfig] = {}
        for name, entry in raw.items():
            primary = self._parse_route(entry["primary"], entry.get("params", {}))
            fallback = None
            if "fallback" in entry:
                fallback = self._parse_route(entry["fallback"], entry.get("params", {}))
            result[name] = CapabilityConfig(name=name, primary=primary, fallback=fallback)
        return result

    @staticmethod
    def _parse_route(route: dict[str, Any], params: dict[str, Any]) -> ModelRoute:
        return ModelRoute(
            provider=route["provider"],
            model=route["model"],
            params=dict(params),
        )

    def get(self, capability: str) -> CapabilityConfig:
        if capability not in self._capabilities:
            valid = sorted(self._capabilities)
            raise KeyError(f"Unknown capability '{capability}'. Valid: {valid}")
        return self._capabilities[capability]

    def list_capabilities(self) -> list[str]:
        return sorted(self._capabilities)

    def validate_core_capabilities(self) -> list[str]:
        """Return core capability keys missing from the registry."""
        missing = [
            cap.value
            for cap in CORE_AI_CAPABILITIES
            if cap.value not in self._capabilities
        ]
        return missing
