from typing import Any

from app.application.ports.prompts import PromptRegistryPort
from app.infrastructure.logging.setup import get_logger
from app.infrastructure.prompts.registry import PromptRegistry

logger = get_logger(__name__)


class PromptSyncService:
    def __init__(self, registry: PromptRegistryPort):
        self._registry = registry

    def sync_all(self) -> dict[str, Any]:
        synced = 0
        unchanged = 0
        errors: list[dict[str, str]] = []

        for entry in self._registry.list_registered_prompts():
            name = entry["name"]
            if not entry["file_exists"]:
                errors.append({"name": name, "error": "file missing"})
                continue
            try:
                path = self._registry.get_prompt_path(name)
                content = path.read_text(encoding="utf-8")
                content_hash = PromptRegistry.compute_hash(content)
                before = self._registry.get_active_version(name)
                self._registry.register_version(name, content, str(path), content_hash)
                if before and before.get("content_hash") == content_hash:
                    unchanged += 1
                else:
                    synced += 1
            except Exception as exc:
                errors.append({"name": name, "error": str(exc)})
                logger.warning("prompt_sync_failed", name=name, error=str(exc))

        logger.info("prompts_synced", synced=synced, unchanged=unchanged, errors=len(errors))
        return {"synced": synced, "unchanged": unchanged, "errors": errors}
