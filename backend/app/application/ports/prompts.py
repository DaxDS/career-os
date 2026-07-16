"""Prompt registry port — externalized prompts with version tracking."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from app.domain.enums import PromptName


class PromptRegistryPort(ABC):
    @abstractmethod
    def get_prompts_root(self) -> Path:
        """Return the configured prompts directory."""

    @abstractmethod
    def get_prompt_path(self, name: PromptName | str) -> Path:
        """Resolve logical prompt name to file path."""

    @abstractmethod
    def list_registered_prompts(self) -> list[dict[str, Any]]:
        """List all registered prompts with file path and availability status."""

    @abstractmethod
    def get_active_version(self, name: PromptName | str) -> dict[str, Any] | None:
        """Return active version metadata from DB, or None if not yet synced."""

    @abstractmethod
    def register_version(
        self,
        name: PromptName | str,
        content: str,
        file_path: str,
        content_hash: str,
    ) -> dict[str, Any]:
        """Register a new prompt version (immutable). Called during sync."""

    @abstractmethod
    def get_active_content(self, name: PromptName | str) -> str:
        """Return active prompt text from DB, falling back to file on disk."""

    @abstractmethod
    def get_capability_for_prompt(self, name: PromptName | str) -> str:
        """Return capability key from manifest for a prompt name."""
