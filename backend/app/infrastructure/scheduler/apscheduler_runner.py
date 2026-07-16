from collections.abc import Callable
from datetime import datetime
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.infrastructure.logging.setup import get_logger
from app.infrastructure.scheduler.settings import SchedulerSettings

logger = get_logger(__name__)


class SchedulerRunner:
    """APScheduler wrapper for the daily morning pipeline."""

    def __init__(
        self,
        settings: SchedulerSettings,
        on_morning_run: Callable[[], None],
    ):
        self._settings = settings
        self._on_morning_run = on_morning_run
        self._scheduler = BackgroundScheduler(timezone=settings.scheduler_timezone)

    @property
    def enabled(self) -> bool:
        return self._settings.scheduler_enabled

    def start(self) -> None:
        if not self._settings.scheduler_enabled:
            logger.info("scheduler_disabled")
            return

        self._scheduler.add_job(
            self._on_morning_run,
            CronTrigger(
                hour=self._settings.scheduler_hour,
                minute=self._settings.scheduler_minute,
                timezone=self._settings.scheduler_timezone,
            ),
            id="daily_morning_pipeline",
            replace_existing=True,
        )
        self._scheduler.start()
        logger.info(
            "scheduler_started",
            hour=self._settings.scheduler_hour,
            minute=self._settings.scheduler_minute,
            timezone=self._settings.scheduler_timezone,
        )

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("scheduler_stopped")

    def status(self) -> dict[str, Any]:
        job = self._scheduler.get_job("daily_morning_pipeline") if self._scheduler.running else None
        next_run: datetime | None = job.next_run_time if job else None
        return {
            "enabled": self._settings.scheduler_enabled,
            "running": self._scheduler.running,
            "schedule_hour": self._settings.scheduler_hour,
            "schedule_minute": self._settings.scheduler_minute,
            "timezone": self._settings.scheduler_timezone,
            "next_run_at": next_run.isoformat() if next_run else None,
        }
