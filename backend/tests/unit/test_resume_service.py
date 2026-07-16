import uuid
from pathlib import Path

import pytest

from app.application.services.resume_classifier import ResumeClassifier
from app.application.services.resume_service import ResumeService
from app.config import Settings
from app.domain.enums import ResumeLabel
from app.infrastructure.audit.sqlalchemy_audit import SQLAlchemyAuditLog
from app.infrastructure.db import models  # noqa: F401
from app.infrastructure.db.base import Base
from app.infrastructure.parsers.resume_parser import ResumeParser
from app.infrastructure.repositories.resume_repository import SQLAlchemyResumeRepository
from app.infrastructure.storage.local_storage import LocalFileStorage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def resume_service(db_session, tmp_path):
    settings = Settings(storage_path=tmp_path / "storage")
    storage = LocalFileStorage(settings)
    repo = SQLAlchemyResumeRepository(db_session)
    return ResumeService(repo, storage, SQLAlchemyAuditLog(db_session))


@pytest.fixture
def user_id():
    return uuid.uuid4()


def test_parser_structures_resume_text():
    parser = ResumeParser()
    parsed = parser.parse_file(FIXTURES / "production_resume.txt")
    assert any("PLC" in s for s in parsed["skills"])
    assert len(parsed["experience"]) >= 1


def test_classifier_maps_label_to_category():
    parser = ResumeParser()
    classifier = ResumeClassifier()
    parsed = parser.parse_file(FIXTURES / "production_resume.txt")
    result = classifier.classify(ResumeLabel.PRODUCTION.value, parsed)
    assert result["role_family"] == "production"
    assert result["classification_method"] == "rule_based"


@pytest.mark.asyncio
async def test_upload_creates_master_resume(resume_service, user_id):
    content = (FIXTURES / "production_resume.txt").read_bytes()
    resume = await resume_service.upload_master_resume(
        user_id, ResumeLabel.PRODUCTION.value, content, "production_resume.txt"
    )
    assert resume.label == ResumeLabel.PRODUCTION.value
    assert resume.version == 1
    assert resume.is_active is True
    assert Path(resume.file_path).exists()


@pytest.mark.asyncio
async def test_reupload_creates_version(resume_service, user_id):
    content = (FIXTURES / "production_resume.txt").read_bytes()
    first = await resume_service.upload_master_resume(
        user_id, ResumeLabel.PRODUCTION.value, content, "v1.txt"
    )
    second = await resume_service.upload_master_resume(
        user_id, ResumeLabel.PRODUCTION.value, content + b"\n", "v2.txt"
    )
    assert second.id == first.id
    assert second.version == 2
    versions = resume_service.list_versions(user_id, first.id)
    assert len(versions) == 1
    assert versions[0].version_number == 1


@pytest.mark.asyncio
async def test_list_all_five_labels(resume_service, user_id):
    content = (FIXTURES / "production_resume.txt").read_bytes()
    for label in ResumeLabel:
        await resume_service.upload_master_resume(user_id, label.value, content, f"{label.name}.txt")
    resumes = resume_service.list_master_resumes(user_id)
    assert len(resumes) == 5


@pytest.mark.asyncio
async def test_invalid_label_rejected(resume_service, user_id):
    with pytest.raises(ValueError, match="Invalid label"):
        await resume_service.upload_master_resume(user_id, "Invalid Resume", b"data", "x.txt")


@pytest.mark.asyncio
async def test_deactivate_resume(resume_service, user_id):
    content = (FIXTURES / "production_resume.txt").read_bytes()
    resume = await resume_service.upload_master_resume(
        user_id, ResumeLabel.IT.value, content, "it.txt"
    )
    deactivated = resume_service.deactivate(user_id, resume.id)
    assert deactivated.is_active is False
    assert resume_service.list_master_resumes(user_id) == []
