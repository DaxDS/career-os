from typing import Any

from app.application.ports.job_search import JobSearchPort
from app.infrastructure.db.models import JobSource
from app.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)


class ConfigJobSearchAdapter(JobSearchPort):
    """Reads job payloads from source config until live scrapers are implemented."""

    def search(self, source: JobSource) -> list[dict[str, Any]]:
        jobs = source.config.get("scheduled_search_jobs", [])
        if not isinstance(jobs, list):
            return []

        connector_status = source.config.get("connector_status", "unknown")
        if not jobs and connector_status == "not_implemented":
            logger.info(
                "job_search_skipped",
                source_id=str(source.id),
                preset_key=source.preset_key,
                reason="connector_not_implemented",
            )
        elif jobs:
            logger.info(
                "job_search_config_results",
                source_id=str(source.id),
                preset_key=source.preset_key,
                count=len(jobs),
            )
        return [job for job in jobs if isinstance(job, dict)]
