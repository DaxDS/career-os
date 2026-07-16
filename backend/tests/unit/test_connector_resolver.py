from app.application.services.connector_resolver import (
    detect_ats_connector_key,
    resolve_browser_connector_key,
)
from app.domain.enums import JobSourcePreset
from app.infrastructure.db.models import JobPosting, JobSource


def _job(source_url: str) -> JobPosting:
    return JobPosting(
        title="Role",
        company="Co",
        description="d",
        description_hash="h",
        dedup_key="k",
        source_url=source_url,
    )


def _manual_source() -> JobSource:
    return JobSource(
        preset_key=JobSourcePreset.MANUAL_URL_IMPORT.value,
        name="Manual URL Import",
        source_type="manual",
        config={},
    )


def test_manual_import_resolves_to_company_career_pages():
    source = JobSource(
        preset_key=JobSourcePreset.MANUAL_URL_IMPORT.value,
        name="Manual URL Import",
        source_type="manual",
        config={},
    )
    job = JobPosting(
        title="Role",
        company="Co",
        description="d",
        description_hash="h",
        dedup_key="k",
        source_url="https://careers.example.com/jobs/1",
    )
    assert resolve_browser_connector_key(source, job) == "company_career_pages"


def test_job_bank_preset_resolves_connector():
    source = JobSource(
        preset_key=JobSourcePreset.JOB_BANK_CANADA.value,
        name="Job Bank Canada",
        source_type="api",
        config={"base_url": "https://www.jobbank.gc.ca"},
    )
    job = JobPosting(
        title="Role",
        company="Co",
        description="d",
        description_hash="h",
        dedup_key="k",
        source_url="https://www.jobbank.gc.ca/job/1",
    )
    assert resolve_browser_connector_key(source, job) == "job_bank_canada"


def test_indeed_preset_resolves_connector():
    source = JobSource(
        preset_key=JobSourcePreset.INDEED.value,
        name="Indeed",
        source_type="scraper",
        config={},
    )
    job = JobPosting(
        title="Role",
        company="Co",
        description="d",
        description_hash="h",
        dedup_key="k",
        source_url="https://ca.indeed.com/viewjob?jk=abc",
    )
    assert resolve_browser_connector_key(source, job) == "indeed"


def test_manual_import_of_workday_url_resolves_to_workday():
    job = _job("https://acme.wd5.myworkdayjobs.com/en-US/careers/job/Toronto/AI-Engineer_R123")
    assert resolve_browser_connector_key(_manual_source(), job) == "workday"


def test_manual_import_of_greenhouse_url_resolves_to_greenhouse():
    job = _job("https://boards.greenhouse.io/acme/jobs/4567890")
    assert resolve_browser_connector_key(_manual_source(), job) == "greenhouse"


def test_manual_import_of_new_greenhouse_board_resolves_to_greenhouse():
    job = _job("https://job-boards.greenhouse.io/acme/jobs/4567890")
    assert resolve_browser_connector_key(_manual_source(), job) == "greenhouse"


def test_no_preset_falls_back_to_ats_detection():
    job = _job("https://acme.wd1.myworkdayjobs.com/careers/job/R999")
    assert resolve_browser_connector_key(None, job) == "workday"


def test_unknown_url_still_resolves_to_company_career_pages():
    job = _job("https://careers.example.com/jobs/1")
    assert resolve_browser_connector_key(_manual_source(), job) == "company_career_pages"


def test_ats_detection_matches_hostname_not_substring():
    # Look-alike domains must not match
    assert detect_ats_connector_key("https://myworkdayjobs.com.evil.example/job/1") is None
    assert detect_ats_connector_key("https://notgreenhouse.io/jobs/1") is None
    assert detect_ats_connector_key("") is None
