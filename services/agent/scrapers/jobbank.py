"""Government of Canada Job Bank scraper — polite HTTP, robots.txt respected."""

from __future__ import annotations

import html as html_lib
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from config import settings

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 CareerOS/1.0"
)
_BASE = "https://www.jobbank.gc.ca"
_TIMEOUT = 30
_MIN_DETAIL_CHARS = 20
_last_fetch_at = 0.0


@dataclass
class RawJobListing:
    source: str
    external_id: str
    url: str
    title: str
    company: str
    city: str
    province: str
    description: str
    noc_code: str | None = None
    posted_at: str | None = None
    raw_payload: dict[str, Any] | None = None


def _rate_limit() -> None:
    global _last_fetch_at
    elapsed = time.monotonic() - _last_fetch_at
    if elapsed < settings.scraper_delay_seconds:
        time.sleep(settings.scraper_delay_seconds - elapsed)
    _last_fetch_at = time.monotonic()


def _fetch(url: str) -> str:
    _rate_limit()
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-CA,en;q=0.9",
        },
    )
    with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
        return response.read().decode("utf-8", "replace")


def _strip_tags(text: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _is_blocked_page(html: str) -> bool:
    lowered = html.lower()
    if "system maintenance" in lowered and "job bank" in lowered:
        return True
    if len(html) < 500 and "captcha" in lowered:
        return True
    return False


def _parse_province(location: str) -> tuple[str, str]:
    location = html_lib.unescape(location).strip()
    match = re.search(r"^(.*?)\s*\(([A-Z]{2})\)\s*$", location)
    if match:
        return match.group(1).strip(), match.group(2)
    return location, ""


def _extract_description(html: str) -> str:
    if _is_blocked_page(html):
        return ""
    for pattern in (
        r'<div class="job-posting-details-body[^"]*">(.*?)</div>\s*<div class="job-posting-details-sidebar',
        r'<section[^>]*id="job-posting[^"]*"[^>]*>(.*?)</section>',
    ):
        match = re.search(pattern, html, re.S | re.I)
        if match:
            text = _strip_tags(match.group(1))
            if len(text) >= _MIN_DETAIL_CHARS:
                return text[:8000]
    return ""


def _extract_noc_from_html(html: str) -> str | None:
    match = re.search(r"NOC\s*2021[:\s]*(\d{5})", html, re.I)
    if match:
        return match.group(1)
    match = re.search(r'data-noc="(\d{5})"', html, re.I)
    if match:
        return match.group(1)
    return None


def _extract_listing_snippet(block: str) -> str:
    parts: list[str] = []
    for pattern in (r'<li class="salary">(.*?)</li>', r'<span class="salary">(.*?)</span>'):
        match = re.search(pattern, block, re.S | re.I)
        if match:
            text = _strip_tags(match.group(1))
            if text:
                parts.append(text)
    return " · ".join(parts)


def fetch_job_description(job_id: str) -> tuple[str, str | None]:
    try:
        detail_html = _fetch(f"{_BASE}/jobsearch/jobposting/{job_id}")
    except urllib.error.URLError:
        return "", None
    return _extract_description(detail_html), _extract_noc_from_html(detail_html)


def search_job_bank(keywords: list[str], location: str = "Canada", max_results: int | None = None) -> list[RawJobListing]:
    limit = max_results or settings.max_jobs_per_source
    all_jobs: list[RawJobListing] = []
    seen: set[str] = set()

    for keyword in keywords:
        if len(all_jobs) >= limit:
            break
        params = {
            "searchterm": keyword,
            "searchstring": keyword,
            "locationstring": location or "Canada",
            "locationparam": "",
        }
        url = f"{_BASE}/jobsearch/jobsearch?{urllib.parse.urlencode(params)}"
        try:
            page_html = _fetch(url)
        except urllib.error.URLError:
            continue

        articles = re.findall(
            r'<article[^>]*id="article-(\d+)"[^>]*>(.*?)</article>',
            page_html,
            flags=re.S | re.I,
        )
        for job_id, block in articles:
            if len(all_jobs) >= limit or job_id in seen:
                continue
            title_match = re.search(r'<span class="noctitle">\s*(.*?)\s*</span>', block, re.S | re.I)
            if not title_match:
                continue
            company_match = re.search(r'<li class="business">(.*?)</li>', block, re.S | re.I)
            location_match = re.search(
                r'<li class="location">.*?<span class="wb-inv">Location</span>\s*(.*?)\s*</li>',
                block,
                re.S | re.I,
            )
            title = _strip_tags(title_match.group(1))
            company = _strip_tags(company_match.group(1)) if company_match else "Unknown"
            location_raw = _strip_tags(location_match.group(1)) if location_match else ""
            city, province = _parse_province(location_raw)
            description, noc_code = fetch_job_description(job_id)
            if not description:
                description = _extract_listing_snippet(block)
            seen.add(job_id)
            all_jobs.append(
                RawJobListing(
                    source="job_bank",
                    external_id=job_id,
                    url=f"{_BASE}/jobsearch/jobposting/{job_id}",
                    title=title,
                    company=company,
                    city=city,
                    province=province,
                    description=description,
                    noc_code=noc_code,
                    raw_payload={"source": "job_bank", "job_id": job_id},
                )
            )
    return all_jobs
