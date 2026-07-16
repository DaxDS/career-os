"""Tests for live Job Bank Canada search adapter."""

from unittest.mock import patch

from app.infrastructure.db.models import JobSource
from app.infrastructure.jobs.search.live_adapters import (
    JobBankCanadaSearchAdapter,
    _is_blocked_page,
)

LISTING_HTML = """
<div id="ajaxupdateform:result_block" class="results-jobs">
<article id="article-12345" class="action-buttons">
  <a href="/jobsearch/jobposting/12345" class="resultJobItem">
    <h3 class="title">
      <span class="noctitle"> machine learning engineer </span>
    </h3>
    <ul class="list-unstyled">
      <li class="business">Acme AI Inc.</li>
      <li class="location"><span class="wb-inv">Location</span> Toronto (ON)</li>
      <li class="salary">$120,000 to $150,000 annually</li>
    </ul>
  </a>
</article>
</div>
"""

MAINTENANCE_HTML = """
<html xmlns:o="urn:schemas-microsoft-com:office:office">
<body>Job Bank / Guichet-Emplois unavailable due to system maintenance</body>
</html>
"""

DETAIL_HTML = """
<div class="job-posting-details-body col-md-9">
  <p>Build ML models for production systems.</p>
</div>
<div class="job-posting-details-sidebar">
"""


def _source(**config) -> JobSource:
    return JobSource(
        user_id="00000000-0000-0000-0000-000000000001",
        preset_key="job_bank_canada",
        name="Job Bank Canada",
        source_type="api",
        config={
            "search_keywords": ["machine learning"],
            "max_results": 5,
            **config,
        },
    )


def test_job_bank_parses_search_results():
    adapter = JobBankCanadaSearchAdapter()

    def fake_fetch(url: str) -> str:
        if "jobposting/12345" in url:
            return DETAIL_HTML
        return LISTING_HTML

    with patch("app.infrastructure.jobs.search.live_adapters._fetch", side_effect=fake_fetch):
        jobs = adapter.search(_source())

    assert len(jobs) == 1
    assert jobs[0]["external_id"] == "12345"
    assert jobs[0]["title"] == "machine learning engineer"
    assert jobs[0]["company"] == "Acme AI Inc."
    assert jobs[0]["location_province"] == "ON"
    assert "ML models" in jobs[0]["description"]


def test_job_bank_detects_maintenance_page():
    assert _is_blocked_page(MAINTENANCE_HTML) is True


def test_job_bank_uses_listing_snippet_when_detail_blocked():
    adapter = JobBankCanadaSearchAdapter()

    def fake_fetch(url: str) -> str:
        if "jobposting/12345" in url:
            return MAINTENANCE_HTML
        return LISTING_HTML

    with patch("app.infrastructure.jobs.search.live_adapters._fetch", side_effect=fake_fetch):
        jobs = adapter.search(_source())

    assert len(jobs) == 1
    assert "$120,000" in jobs[0]["description"]
