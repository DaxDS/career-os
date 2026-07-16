"""Adzuna Canada API — supplement job source."""

from __future__ import annotations

import httpx

from config import settings
from scrapers.jobbank import RawJobListing, _rate_limit


def search_adzuna(keywords: list[str], location: str = "Canada", max_results: int | None = None) -> list[RawJobListing]:
    if not settings.adzuna_app_id or not settings.adzuna_app_key:
        return []

    limit = max_results or settings.max_jobs_per_source
    jobs: list[RawJobListing] = []
    seen: set[str] = set()

    with httpx.Client(timeout=30) as client:
        for keyword in keywords:
            if len(jobs) >= limit:
                break
            _rate_limit()
            response = client.get(
                "https://api.adzuna.com/v1/api/jobs/ca/search/1",
                params={
                    "app_id": settings.adzuna_app_id,
                    "app_key": settings.adzuna_app_key,
                    "what": keyword,
                    "where": location or "Canada",
                    "results_per_page": min(limit, 50),
                },
            )
            if response.status_code != 200:
                continue
            for item in response.json().get("results", []):
                if len(jobs) >= limit:
                    break
                ext_id = str(item.get("id", ""))
                if not ext_id or ext_id in seen:
                    continue
                seen.add(ext_id)
                area = item.get("location", {}).get("area", [])
                province = area[-1][:2].upper() if area and len(area[-1]) == 2 else ""
                city = area[0] if area else ""
                jobs.append(
                    RawJobListing(
                        source="adzuna",
                        external_id=ext_id,
                        url=item.get("redirect_url") or "",
                        title=item.get("title") or "Unknown",
                        company=item.get("company", {}).get("display_name") or "Unknown",
                        city=city,
                        province=province,
                        description=(item.get("description") or "")[:8000],
                        raw_payload={"source": "adzuna", "category": item.get("category", {})},
                    )
                )
    return jobs
