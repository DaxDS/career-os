import hashlib
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from app.application.ports.prompts import PromptRegistryPort
from app.config import Settings
from app.domain.enums import PROMPT_TO_CAPABILITY, PromptName
from app.infrastructure.db.models import PromptVersion
from app.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)


class PromptRegistry(PromptRegistryPort):
    """Resolves prompts from configured /prompts directory with DB-backed versioning."""

    def __init__(self, settings: Settings, db: Session):
        self._settings = settings
        self._db = db
        self._manifest = self._load_manifest()

    def _load_manifest(self) -> dict[str, Any]:
        manifest_path = self._settings.prompts_path / "manifest.yaml"
        if not manifest_path.exists():
            logger.warning("prompt_manifest_missing", path=str(manifest_path))
            return {}
        with open(manifest_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data.get("prompts", {})

    def get_prompts_root(self) -> Path:
        return self._settings.prompts_path

    def get_prompt_path(self, name: PromptName | str) -> Path:
        key = name.value if isinstance(name, PromptName) else name
        entry = self._manifest.get(key)
        if not entry:
            raise FileNotFoundError(f"Prompt not registered in manifest: {key}")
        return self._settings.prompts_path / entry["file"]

    def list_registered_prompts(self) -> list[dict[str, Any]]:
        results = []
        for name, entry in self._manifest.items():
            filepath = self._settings.prompts_path / entry["file"]
            active = self.get_active_version(name)
            results.append({
                "name": name,
                "file": entry["file"],
                "capability": entry.get("capability", ""),
                "path": str(filepath),
                "file_exists": filepath.exists(),
                "active_version": active["version"] if active else None,
            })
        return results

    def get_active_version(self, name: PromptName | str) -> dict[str, Any] | None:
        key = name.value if isinstance(name, PromptName) else name
        try:
            row = (
                self._db.query(PromptVersion)
                .filter(PromptVersion.name == key, PromptVersion.is_active.is_(True))
                .first()
            )
        except Exception as exc:
            logger.warning("prompt_version_lookup_failed", name=key, error=str(exc))
            return None
        if not row:
            return None
        return {
            "id": row.id,
            "name": row.name,
            "version": row.version,
            "file_path": row.file_path,
            "content_hash": row.content_hash,
            "is_active": row.is_active,
            "created_at": row.created_at.isoformat(),
        }

    def register_version(
        self,
        name: PromptName | str,
        content: str,
        file_path: str,
        content_hash: str,
    ) -> dict[str, Any]:
        key = name.value if isinstance(name, PromptName) else name

        existing_active = (
            self._db.query(PromptVersion)
            .filter(PromptVersion.name == key, PromptVersion.is_active.is_(True))
            .first()
        )
        if existing_active and existing_active.content_hash == content_hash:
            return self.get_active_version(key)  # type: ignore[return-value]

        if existing_active:
            existing_active.is_active = False

        max_version = (
            self._db.query(PromptVersion).filter(PromptVersion.name == key).count()
        )
        row = PromptVersion(
            name=key,
            version=max_version + 1,
            file_path=file_path,
            content_hash=content_hash,
            content=content,
            is_active=True,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        logger.info("prompt_version_registered", name=key, version=row.version)
        return self.get_active_version(key)  # type: ignore[return-value]

    def get_active_content(self, name: PromptName | str) -> str:
        key = name.value if isinstance(name, PromptName) else name
        row = (
            self._db.query(PromptVersion)
            .filter(PromptVersion.name == key, PromptVersion.is_active.is_(True))
            .first()
        )
        if row and row.content:
            return row.content
        return self.get_prompt_path(key).read_text(encoding="utf-8")

    def get_capability_for_prompt(self, name: PromptName | str) -> str:
        key = name.value if isinstance(name, PromptName) else name
        expected = PROMPT_TO_CAPABILITY.get(PromptName(key))
        entry = self._manifest.get(key)
        if not entry:
            raise FileNotFoundError(f"Prompt not registered in manifest: {key}")
        capability = entry.get("capability", "")
        if expected and capability != expected.value:
            raise ValueError(
                f"Manifest capability mismatch for '{key}': "
                f"expected '{expected.value}', got '{capability}'"
            )
        return capability

    @staticmethod
    def compute_hash(content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()
