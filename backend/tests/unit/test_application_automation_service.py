import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.application.services.application_automation_service import ApplicationAutomationService
from app.domain.enums import ApplicationStatus, JobSourcePreset
from app.infrastructure.browser.automation_engine import PlaywrightBrowserAutomation
from app.infrastructure.browser.connectors.registry import BrowserConnectorRegistry
from app.infrastructure.browser.playwright_runner import MockBrowserRunner
from app.infrastructure.browser.session_manager import BrowserSessionManager
from app.infrastructure.browser.settings import AutomationSettings
from app.infrastructure.db import automation_models  # noqa: F401
from app.infrastructure.db import models  # noqa: F401
from app.infrastructure.db.base import Base
from app.infrastructure.db.models import (
    ApplicationDocument,
    JobApplication,
    JobPosting,
    JobSource,
)
from app.infrastructure.repositories.application_repository import SQLAlchemyApplicationRepository
from app.infrastructure.repositories.automation_repository import SQLAlchemyAutomationRepository
from app.infrastructure.repositories.job_repository import SQLAlchemyJobRepository
from app.config import Settings
from app.infrastructure.storage.local_storage import LocalFileStorage


class MagicMockUserRepo:
    def get_profile(self, user_id):
        from app.infrastructure.db.models import UserProfile

        return UserProfile(user_id=user_id, legal_name="Jane Doe", phone="555-0100")


class MagicMockResumeRepo:
    def __init__(self, master_id: uuid.UUID, file_path: str):
        self._master_id = master_id
        self._file_path = file_path

    def get_master_by_id(self, resume_id, user_id):
        from app.infrastructure.db.models import MasterResume

        if resume_id != self._master_id:
            return None
        return MasterResume(
            id=resume_id,
            user_id=user_id,
            label="AI Resume",
            category="ai",
            file_path=self._file_path,
            original_filename="resume.pdf",
            content_hash="h",
        )


@pytest.fixture
def automation_env(tmp_path):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    settings = AutomationSettings(
        browser_profiles_path=tmp_path / "profiles",
        browser_screenshots_path=tmp_path / "screenshots",
        browser_headless=True,
        browser_stop_before_submit=True,
    )
    app_repo = SQLAlchemyApplicationRepository(session)
    job_repo = SQLAlchemyJobRepository(session)
    auto_repo = SQLAlchemyAutomationRepository(session)
    storage = LocalFileStorage(Settings(storage_path=tmp_path / "storage"))

    user_id = uuid.uuid4()
    source = JobSource(
        user_id=user_id,
        preset_key=JobSourcePreset.JOB_BANK_CANADA.value,
        name="Job Bank Canada",
        source_type="api",
        config={"base_url": "https://www.jobbank.gc.ca"},
        is_builtin=True,
    )
    session.add(source)
    session.flush()
    job = JobPosting(
        id=uuid.uuid4(),
        user_id=user_id,
        source_id=source.id,
        title="Developer",
        company="Acme",
        description="Role",
        description_hash="h",
        dedup_key="k",
        source_url="https://www.jobbank.gc.ca/jobposting/123",
    )
    application = JobApplication(
        user_id=user_id,
        job_id=job.id,
        master_resume_id=uuid.uuid4(),
        status=ApplicationStatus.APPROVED.value,
        generated_at=datetime.now(timezone.utc),
    )
    session.add(job)
    session.add(application)
    session.flush()

    resume_file = tmp_path / "resume.json"
    resume_file.write_text('{"summary": "test"}')
    master_pdf = tmp_path / "master.pdf"
    master_pdf.write_bytes(b"%PDF-1.4 test")
    cover_file = tmp_path / "cover.txt"
    cover_file.write_text("Dear Hiring Manager")

    session.add(
        ApplicationDocument(
            application_id=application.id,
            document_type="tailored_resume",
            file_path=str(resume_file),
            content={"summary": "test"},
        )
    )
    session.add(
        ApplicationDocument(
            application_id=application.id,
            document_type="cover_letter",
            file_path=str(cover_file),
            content={"full_text": "Dear Hiring Manager"},
        )
    )
    session.commit()

    session_manager = BrowserSessionManager(auto_repo, settings)
    engine_svc = PlaywrightBrowserAutomation(
        app_repo,
        job_repo,
        MagicMockUserRepo(),
        MagicMockResumeRepo(application.master_resume_id, str(master_pdf)),
        auto_repo,
        BrowserConnectorRegistry(),
        session_manager,
        MockBrowserRunner(),
        storage,
        settings,
    )
    service = ApplicationAutomationService(engine_svc, auto_repo)
    yield service, user_id, job, session
    session.close()


@pytest.mark.asyncio
async def test_automation_stops_before_submit(automation_env):
    service, user_id, job, _ = automation_env
    result = await service.start_submission(user_id, job.id, stop_before_submit=True)
    assert result["status"] == "stopped_before_submit"
    assert result["submitted"] is False

    run = service.get_run(user_id, uuid.UUID(result["run_id"]))
    assert run.connector_key == "job_bank_canada"
    logs = service.get_action_logs(user_id, run.id)
    assert any(log.action == "stop_before_submit" for log in logs)


@pytest.mark.asyncio
async def test_automation_requires_approved_status(automation_env):
    service, user_id, job, session = automation_env
    application = session.query(JobApplication).first()
    application.status = ApplicationStatus.GENERATED.value
    session.commit()
    with pytest.raises(ValueError, match="approved"):
        await service.start_submission(user_id, job.id)
