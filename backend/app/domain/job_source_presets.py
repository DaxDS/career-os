from dataclasses import dataclass
from typing import Any

from app.domain.enums import JobSourcePreset, JobSourceType


@dataclass(frozen=True)
class JobSourcePresetDefinition:
    """Static definition for a built-in job source preset."""

    preset_key: JobSourcePreset
    name: str
    source_type: JobSourceType
    connector_key: str
    config: dict[str, Any]


JOB_SOURCE_PRESET_DEFINITIONS: dict[JobSourcePreset, JobSourcePresetDefinition] = {
    JobSourcePreset.JOB_BANK_CANADA: JobSourcePresetDefinition(
        preset_key=JobSourcePreset.JOB_BANK_CANADA,
        name="Job Bank Canada",
        source_type=JobSourceType.API,
        connector_key="job_bank_canada",
        config={
            "base_url": "https://www.jobbank.gc.ca",
            "country": "CA",
            "connector_status": "active",
            "search_keywords": ["AI engineer", "machine learning engineer", "data scientist"],
            "location_string": "",
            "max_results": 25,
        },
    ),
    JobSourcePreset.WORKPEI: JobSourcePresetDefinition(
        preset_key=JobSourcePreset.WORKPEI,
        name="WorkPEI",
        source_type=JobSourceType.API,
        connector_key="workpei",
        config={
            "base_url": "https://www.workpei.ca",
            "region": "PE",
            "connector_status": "not_implemented",
        },
    ),
    JobSourcePreset.INDEED: JobSourcePresetDefinition(
        preset_key=JobSourcePreset.INDEED,
        name="Indeed",
        source_type=JobSourceType.SCRAPER,
        connector_key="indeed",
        config={
            "base_url": "https://ca.indeed.com",
            "country": "CA",
            "connector_status": "active",
            "search_keywords": ["AI engineer", "machine learning"],
            "location_string": "Canada",
            "max_results": 15,
        },
    ),
    JobSourcePreset.COMPANY_CAREER_PAGES: JobSourcePresetDefinition(
        preset_key=JobSourcePreset.COMPANY_CAREER_PAGES,
        name="Company Career Pages",
        source_type=JobSourceType.SCRAPER,
        connector_key="company_career_pages",
        config={
            "connector_status": "not_implemented",
        },
    ),
    JobSourcePreset.MANUAL_URL_IMPORT: JobSourcePresetDefinition(
        preset_key=JobSourcePreset.MANUAL_URL_IMPORT,
        name="Manual URL Import",
        source_type=JobSourceType.MANUAL,
        connector_key="manual_url_import",
        config={
            "connector_status": "not_implemented",
        },
    ),
}


def get_preset_definition(preset_key: str) -> JobSourcePresetDefinition:
    try:
        preset = JobSourcePreset(preset_key)
    except ValueError as exc:
        valid = sorted(p.value for p in JobSourcePreset)
        raise ValueError(f"Invalid preset_key. Must be one of: {valid}") from exc
    return JOB_SOURCE_PRESET_DEFINITIONS[preset]


def is_reserved_source_name(name: str) -> bool:
    return name in {definition.name for definition in JOB_SOURCE_PRESET_DEFINITIONS.values()}
