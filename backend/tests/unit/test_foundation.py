import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import Settings
from app.domain.enums import AuditAction, AuditActor, StorageCategory
from app.infrastructure.audit.sqlalchemy_audit import SQLAlchemyAuditLog
from app.infrastructure.db.base import Base
from app.infrastructure.storage.local_storage import LocalFileStorage


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def audit(db_session):
    return SQLAlchemyAuditLog(db_session)


@pytest.fixture
def storage(tmp_path):
    settings = Settings(storage_path=tmp_path / "storage")
    return LocalFileStorage(settings)


def test_record_agent_decision(audit):
    audit_id = audit.record_agent_decision(
        agent_name="resume_selector",
        entity_type="job",
        entity_id="job-123",
        decision={"selected": "resume-1", "confidence": 0.92},
    )
    assert audit_id == 1
    entries = audit.query(action=AuditAction.AGENT_DECISION)
    assert len(entries) == 1
    assert entries[0]["actor"] == "agent:resume_selector"
    assert entries[0]["details"]["decision"]["confidence"] == 0.92


def test_record_resume_selection(audit):
    audit.record_resume_selection(
        job_id=uuid.uuid4(),
        selected_resume_id=uuid.uuid4(),
        confidence=0.88,
        rationale="Best skills match",
    )
    entries = audit.query(action=AuditAction.RESUME_SELECTION)
    assert len(entries) == 1
    assert entries[0]["details"]["confidence"] == 0.88


def test_record_user_approval(audit):
    app_id = uuid.uuid4()
    audit.record_user_approval(application_id=app_id, approved=True, details={"notes": "looks good"})
    entries = audit.query(entity_type="application", entity_id=str(app_id))
    assert len(entries) == 1
    assert entries[0]["action"] == AuditAction.USER_APPROVAL.value
    assert entries[0]["details"]["approved"] is True


def test_record_application_action(audit):
    audit.record_application_action(
        application_id="app-1",
        action="regenerate_cover_letter",
        actor=AuditActor.USER,
    )
    entries = audit.query(action=AuditAction.APPLICATION_ACTION)
    assert entries[0]["details"]["sub_action"] == "regenerate_cover_letter"


def test_audit_query_filters(audit):
    audit.record(action=AuditAction.SYSTEM_EVENT, entity_type="system", entity_id="1", actor=AuditActor.SYSTEM)
    audit.record(action=AuditAction.USER_APPROVAL, entity_type="application", entity_id="2", actor=AuditActor.USER)
    assert len(audit.query(action=AuditAction.SYSTEM_EVENT)) == 1
    assert len(audit.query(entity_type="application")) == 1


def test_storage_master_resume_path(storage, tmp_path):
    user_id = uuid.uuid4()
    path = storage.resolve_directory(StorageCategory.MASTER_RESUME, user_id=user_id)
    assert path.exists()
    assert str(user_id) in str(path)
    assert "resumes" in str(path)


def test_storage_save_and_read(storage):
    user_id = uuid.uuid4()
    saved = storage.save(
        StorageCategory.MASTER_RESUME,
        "resume.pdf",
        b"%PDF-1.4 test",
        user_id=user_id,
    )
    assert saved.exists()
    assert storage.read(saved) == b"%PDF-1.4 test"


def test_storage_application_artifacts(storage):
    user_id = uuid.uuid4()
    job_id = uuid.uuid4()
    resume = storage.save(
        StorageCategory.RESUME_VERSION,
        "Resume.pdf",
        b"resume content",
        user_id=user_id,
        job_id=job_id,
    )
    cover = storage.save_text(
        StorageCategory.COVER_LETTER,
        "CoverLetter.pdf",
        "cover content",
        user_id=user_id,
        job_id=job_id,
    )
    email = storage.save_text(
        StorageCategory.EMAIL,
        "Email.txt",
        "email body",
        user_id=user_id,
        job_id=job_id,
    )
    report = storage.save_text(
        StorageCategory.REPORT,
        "ATSReport.json",
        "{}",
        user_id=user_id,
        job_id=job_id,
    )
    assert all(p.exists() for p in [resume, cover, email, report])
    assert str(job_id) in str(resume)


def test_storage_paths_not_hardcoded(storage, tmp_path):
    assert str(tmp_path) in str(storage.resolve_directory(
        StorageCategory.TEMPLATE,
        user_id=uuid.uuid4(),
    )) or "templates" in str(storage.resolve_directory(StorageCategory.TEMPLATE))
