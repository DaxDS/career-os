"""JSearch via RapidAPI — supplement source for Canadian jobs."""

from __future__ import annotations

import time
from typing import Any

import httpx

from config import settings
from scrapers.jobbank import RawJobListing, _parse_province, _rate_limit

_HOST = "jsearch.p.rapidapi.com"
_BASE = f"https://{_HOST}/search"


def search_jsearch(keywords: list[str], location: str = "Canada", max_results: int | None = None) -> list[RawJobListing]:
    if not settings.jsearch_rapidapi_key:
        return []

    limit = max_results or settings.max_jobs_per_source
    jobs: list[RawJobListing] = []
    seen: set[str] = set()

    with httpx.Client(timeout=30) as client:
        for keyword in keywords:
            if len(jobs) >= limit:
                break
            query = f"{keyword} in {location or 'Canada'}"
            _rate_limit()
            response = client.get(
                _BASE,
                params={"query": query, "page": "1", "num_pages": "1", "country": "ca"},
                headers={
                    "X-RapidAPI-Key": settings.jsearch_rapidapi_key,
                    "X-RapidAPI-Host": _HOST,
                },
            )
            if response.status_code != 200:
                continue
            data = response.json()
            for item in data.get("data", []):
                if len(jobs) >= limit:
                    break
                ext_id = str(item.get("job_id") or item.get("job_link", ""))
                if not ext_id or ext_id in seen:
                    continue
                seen.add(ext_id)
                loc = item.get("job_city") or item.get("job_country") or ""
                city, province = _parse_province(loc) if "(" in loc else (loc, item.get("job_state", "") or "")
                jobs.append(
                    RawJobListing(
                        source="jsearch",
                        external_id=ext_id[:128],
                        url=item.get("job_apply_link") or item.get("job_link") or "",
                        title=item.get("job_title") or "Unknown",
                        company=item.get("employer_name") or "Unknown",
                        city=city,
                        province=province[:2].upper() if province else "",
                        description=(item.get("job_description") or "")[:8000],
                        posted_at=item.get("job_posted_at_datetime_utc"),
                        raw_payload={"source": "jsearch", "raw": _slim(item)},
                    )
                )
    return jobs


def _slim(item: dict[str, Any]) -> dict[str, Any]:
    return {k: item[k] for k in ("job_title", "employer_name", "job_city", "job_state") if k in item}
