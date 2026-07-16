import json
import uuid
from pathlib import Path

import pytest

from app.application.services.job_classifier import JobClassifier
from app.application.services.job_service import JobService
from app.domain.enums import JobSourcePreset, JobSourceType
from app.infrastructure.audit.sqlalchemy_audit import SQLAlchemyAuditLog
from app.infrastructure.db import models  # noqa: F401
from app.infrastructure.db.base import Base
from app.infrastructure.db.models import JobSource
from app.infrastructure.jobs.dedup import compute_dedup_key, compute_description_hash, normalize_url
from app.infrastructure.repositories.job_repository import SQLAlchemyJobRepository
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
def job_service(db_session):
    repo = SQLAlchemyJobRepository(db_session)
    return JobService(repo, SQLAlchemyAuditLog(db_session))


@pytest.fixture
def user_id():
    return uuid.uuid4()


@pytest.fixture
def sample_job():
    return json.loads((FIXTURES / "sample_job.json").read_text())


def test_normalize_url_strips_tracking_params():
    url = "https://Example.com/jobs/1?utm_source=email&id=99"
    assert normalize_url(url) == "https://example.com/jobs/1?id=99"


def test_dedup_key_is_stable():
    key1 = compute_dedup_key("Acme Corp", "Software Developer", "ON", "Toronto")
    key2 = compute_dedup_key("acme corp", "software developer", "on", "toronto")
    assert key1 == key2


def test_classifier_detects_production_role():
    classifier = JobClassifier()
    result = classifier.classify(
        "Manufacturing Production Operator",
        "PLC monitoring and quality control in food processing plant",
    )
    assert result["role_family"] == "production"
    assert result["classification_method"] == "rule_based"


def test_import_creates_job(job_service, user_id, sample_job):
    results = job_service.import_jobs(user_id, [sample_job])
    assert len(results) == 1
    assert results[0]["import_status"] == "created"
    job = results[0]["job"]
    assert job.title == sample_job["title"]
    assert job.role_family == "production"
    assert job.location_province == "PE"


def test_reimport_same_external_id_is_duplicate(job_service, user_id, sample_job):
    job_service.seed_builtin_sources(user_id)
    source = job_service.get_source_by_preset(user_id, JobSourcePreset.JOB_BANK_CANADA.value)
    first = job_service.import_jobs(user_id, [sample_job], source_id=source.id)
    second = job_service.import_jobs(user_id, [sample_job], source_id=source.id)
    assert first[0]["import_status"] == "created"
    assert second[0]["import_status"] == "duplicate"
    assert second[0]["match_reason"] == "external_id"
    assert first[0]["job"].id == second[0]["job"].id


def test_cross_source_dedup_by_dedup_key(job_service, user_id, sample_job):
    job_service.import_jobs(user_id, [sample_job])
    duplicate_payload = {**sample_job, "external_id": "different-id", "source_url": "https://other.com/job"}
    results = job_service.import_jobs(user_id, [duplicate_payload])
    assert results[0]["import_status"] == "duplicate"
    assert results[0]["match_reason"] == "dedup_key"


def test_description_hash_dedup(job_service, user_id, sample_job):
    job_service.import_jobs(user_id, [sample_job])
    variant = {
        **sample_job,
        "external_id": None,
        "title": "Different Title",
        "company": "Different Company",
        "location_city": "Halifax",
        "location_province": "NS",
        "source_url": "",
    }
    results = job_service.import_jobs(user_id, [variant])
    assert results[0]["import_status"] == "duplicate"
    assert results[0]["match_reason"] == "description_hash"


def test_list_jobs_filters_by_province(job_service, user_id, sample_job):
    job_service.import_jobs(user_id, [sample_job])
    pe_jobs = job_service.list_jobs(user_id, province="PE")
    on_jobs = job_service.list_jobs(user_id, province="ON")
    assert len(pe_jobs) == 1
    assert len(on_jobs) == 0


def test_archive_job(job_service, user_id, sample_job):
    results = job_service.import_jobs(user_id, [sample_job])
    job_id = results[0]["job"].id
    job_service.archive_job(user_id, job_id)
    assert job_service.list_jobs(user_id) == []


def test_source_crud(job_service, user_id):
    job_service.seed_builtin_sources(user_id)
    source = job_service.create_source(
        user_id, "Custom Feed", JobSourceType.API.value, {"search_url": "https://example.com"}
    )
    assert source.name == "Custom Feed"
    updated = job_service.update_source(user_id, source.id, is_active=False)
    assert updated.is_active is False
    assert len(job_service.list_sources(user_id)) == 6


def test_invalid_source_type_rejected(job_service, user_id):
    with pytest.raises(ValueError, match="Invalid source_type"):
        job_service.create_source(user_id, "Bad", "invalid")


def test_auto_uses_manual_url_import_preset(job_service, user_id, sample_job):
    job_service.import_jobs(user_id, [sample_job])
    source = job_service.get_source_by_preset(user_id, JobSourcePreset.MANUAL_URL_IMPORT.value)
    assert source.name == "Manual URL Import"
    assert source.is_builtin is True


def test_seed_builtin_sources_creates_all_presets(job_service, user_id):
    sources = job_service.seed_builtin_sources(user_id)
    assert len(sources) == 5
    preset_keys = {s.preset_key for s in sources}
    assert preset_keys == {p.value for p in JobSourcePreset}
    second_seed = job_service.seed_builtin_sources(user_id)
    assert len(second_seed) == 5


def test_reserved_source_name_blocked(job_service, user_id):
    job_service.seed_builtin_sources(user_id)
    with pytest.raises(ValueError, match="reserved"):
        job_service.create_source(user_id, "Indeed", JobSourceType.SCRAPER.value)


def test_builtin_source_name_cannot_change(job_service, user_id):
    job_service.seed_builtin_sources(user_id)
    source = job_service.get_source_by_preset(user_id, JobSourcePreset.INDEED.value)
    with pytest.raises(ValueError, match="cannot be changed"):
        job_service.update_source(user_id, source.id, name="Renamed Indeed")


def test_import_by_preset_key(job_service, user_id, sample_job):
    results = job_service.import_jobs(
        user_id,
        [sample_job],
        source_preset_key=JobSourcePreset.JOB_BANK_CANADA.value,
    )
    assert results[0]["import_status"] == "created"
    source = job_service.get_source_by_preset(user_id, JobSourcePreset.JOB_BANK_CANADA.value)
    assert results[0]["job"].source_id == source.id


def test_legacy_manual_source_migrated(job_service, user_id, db_session):
    from app.infrastructure.db.models import JobSource

    legacy = JobSource(
        user_id=user_id,
        name="Manual",
        source_type=JobSourceType.MANUAL.value,
        config={},
    )
    db_session.add(legacy)
    db_session.commit()

    job_service.seed_builtin_sources(user_id)
    source = job_service.get_source_by_preset(user_id, JobSourcePreset.MANUAL_URL_IMPORT.value)
    assert source.id == legacy.id
    assert source.name == "Manual URL Import"
