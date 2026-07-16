from unittest.mock import MagicMock

from app.infrastructure.scheduler.apscheduler_runner import SchedulerRunner
from app.infrastructure.scheduler.settings import SchedulerSettings


def test_scheduler_runner_status_when_disabled():
    callback = MagicMock()
    settings = SchedulerSettings(scheduler_enabled=False)
    runner = SchedulerRunner(settings, callback)
    runner.start()
    status = runner.status()
    assert status["enabled"] is False
    assert status["running"] is False
    callback.assert_not_called()


def test_scheduler_runner_registers_job_when_enabled():
    callback = MagicMock()
    settings = SchedulerSettings(
        scheduler_enabled=True,
        scheduler_hour=8,
        scheduler_minute=30,
        scheduler_timezone="UTC",
    )
    runner = SchedulerRunner(settings, callback)
    runner.start()
    try:
        status = runner.status()
        assert status["enabled"] is True
        assert status["running"] is True
        assert status["schedule_hour"] == 8
        assert status["schedule_minute"] == 30
    finally:
        runner.shutdown()
