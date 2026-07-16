from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.domain.enums import AICapability


@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str


@dataclass(frozen=True)
class LLMResponse:
    content: str
    provider: str
    model: str
    usage: dict[str, Any] = field(default_factory=dict)


class LLMProviderPort(ABC):
    """Provider adapter for a single LLM vendor."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    def is_configured(self) -> bool: ...

    @abstractmethod
    def complete(self, model: str, messages: list[LLMMessage], **params: Any) -> LLMResponse: ...


class ModelRouterPort(ABC):
    """Routes capability requests to the configured provider and model.

    Business logic must call complete_for_capability() with an AICapability value.
    Provider selection (OpenAI, Anthropic, etc.) is internal to the router.
    """

    @abstractmethod
    def complete_for_capability(
        self, capability: AICapability | str, messages: list[LLMMessage]
    ) -> LLMResponse: ...

    @abstractmethod
    def list_capabilities(self) -> list[str]: ...

    @abstractmethod
    def provider_status(self) -> dict[str, bool]: ...
