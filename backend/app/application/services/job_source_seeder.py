import uuid

from app.application.ports.job_repository import JobRepositoryPort
from app.domain.enums import JobSourcePreset
from app.domain.job_source_presets import JOB_SOURCE_PRESET_DEFINITIONS
from app.infrastructure.db.models import JobSource
from app.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)

_LEGACY_MANUAL_SOURCE_NAME = "Manual"


class JobSourceSeeder:
    """Seeds canonical built-in job source presets for a user."""

    def __init__(self, job_repo: JobRepositoryPort):
        self._repo = job_repo

    def seed_builtin_sources(self, user_id: uuid.UUID) -> list[JobSource]:
        self._migrate_legacy_manual_source(user_id)

        seeded: list[JobSource] = []
        for preset, definition in JOB_SOURCE_PRESET_DEFINITIONS.items():
            existing = self._repo.get_source_by_preset_key(user_id, preset.value)
            if existing:
                merged_config = {
                    **existing.config,
                    **definition.config,
                    "connector_key": definition.connector_key,
                    "preset_key": preset.value,
                }
                if merged_config != existing.config:
                    existing.config = merged_config
                    existing = self._repo.update_source(existing)
                seeded.append(existing)
                continue

            source = JobSource(
                user_id=user_id,
                preset_key=preset.value,
                name=definition.name,
                source_type=definition.source_type.value,
                config={
                    **definition.config,
                    "connector_key": definition.connector_key,
                    "preset_key": preset.value,
                },
                is_builtin=True,
            )
            source = self._repo.create_source(source)
            seeded.append(source)
            logger.info(
                "job_source_preset_seeded",
                user_id=str(user_id),
                preset_key=preset.value,
                source_id=str(source.id),
            )

        return seeded

    def _migrate_legacy_manual_source(self, user_id: uuid.UUID) -> None:
        manual_preset = self._repo.get_source_by_preset_key(
            user_id, JobSourcePreset.MANUAL_URL_IMPORT.value
        )
        if manual_preset:
            return

        legacy = self._repo.get_source_by_name(user_id, _LEGACY_MANUAL_SOURCE_NAME)
        if not legacy:
            return

        definition = JOB_SOURCE_PRESET_DEFINITIONS[JobSourcePreset.MANUAL_URL_IMPORT]
        legacy.preset_key = JobSourcePreset.MANUAL_URL_IMPORT.value
        legacy.name = definition.name
        legacy.source_type = definition.source_type.value
        legacy.is_builtin = True
        legacy.config = {
            **definition.config,
            "connector_key": definition.connector_key,
            "preset_key": JobSourcePreset.MANUAL_URL_IMPORT.value,
        }
        self._repo.update_source(legacy)
        logger.info(
            "job_source_legacy_manual_migrated",
            user_id=str(user_id),
            source_id=str(legacy.id),
        )
