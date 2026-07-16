from urllib.parse import urlparse

from app.domain.enums import JobSourcePreset
from app.domain.job_source_presets import get_preset_definition
from app.infrastructure.browser.connectors.registry import SUPPORTED_CONNECTORS
from app.infrastructure.db.models import JobPosting, JobSource

# ATS platforms detectable from the posting URL alone (hosted-board domains)
_ATS_URL_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("workday", ("myworkdayjobs.com", "myworkdaysite.com")),
    ("greenhouse", ("boards.greenhouse.io", "job-boards.greenhouse.io", "greenhouse.io")),
)


def detect_ats_connector_key(url: str) -> str | None:
    """Detect a hosted-ATS connector from the posting URL hostname, or None."""
    if not url:
        return None
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return None
    for connector_key, domains in _ATS_URL_PATTERNS:
        for domain in domains:
            if host == domain or host.endswith("." + domain):
                return connector_key
    return None


def resolve_browser_connector_key(
    source: JobSource | None,
    job: JobPosting,
) -> str:
    """
    Map a job posting's source to a browser connector_key via job source presets.
    Business logic never hardcodes site URLs — only connector keys from presets,
    plus hostname-based detection of hosted ATS platforms (Workday, Greenhouse).
    """
    ats_key = detect_ats_connector_key(job.source_url or job.normalized_url or "")

    if source and source.preset_key:
        definition = get_preset_definition(source.preset_key)
        connector_key = definition.connector_key
        if source.preset_key == JobSourcePreset.MANUAL_URL_IMPORT.value:
            return ats_key or JobSourcePreset.COMPANY_CAREER_PAGES.value
        if connector_key in SUPPORTED_CONNECTORS:
            return connector_key

    if source and source.config.get("connector_key") in SUPPORTED_CONNECTORS:
        return source.config["connector_key"]

    if ats_key:
        return ats_key

    if job.source_url or job.normalized_url:
        return JobSourcePreset.COMPANY_CAREER_PAGES.value

    raise ValueError(
        "Cannot resolve browser connector for job — no supported source preset or application URL"
    )


def resolve_application_url(job: JobPosting, source: JobSource | None) -> str:
    if job.source_url:
        return job.source_url
    if source and source.config.get("base_url") and job.external_id:
        return f"{source.config['base_url'].rstrip('/')}/job/{job.external_id}"
    return ""
