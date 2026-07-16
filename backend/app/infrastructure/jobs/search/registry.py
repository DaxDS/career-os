from typing import Any

from app.application.ports.job_search import JobSearchPort
from app.infrastructure.db.models import JobSource
from app.infrastructure.jobs.search.config_adapter import ConfigJobSearchAdapter


class JobSearchRegistry:
    """Resolves job search adapters by connector key."""

    def __init__(self, default_adapter: JobSearchPort | None = None):
        self._default = default_adapter or ConfigJobSearchAdapter()
        self._adapters: dict[str, JobSearchPort] = {}

    def register(self, connector_key: str, adapter: JobSearchPort) -> None:
        self._adapters[connector_key] = adapter

    def search_source(self, source: JobSource) -> list[dict[str, Any]]:
        connector_key = self._connector_key(source)
        adapter = self._adapters.get(connector_key, self._default)
        return adapter.search(source)

    @staticmethod
    def _connector_key(source: JobSource) -> str:
        if source.preset_key:
            from app.domain.job_source_presets import get_preset_definition

            return get_preset_definition(source.preset_key).connector_key
        return str(source.config.get("connector_key", "manual"))
