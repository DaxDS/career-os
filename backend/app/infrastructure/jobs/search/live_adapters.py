"""Live job search adapters — fetch listings from real websites."""

from __future__ import annotations

import html as html_lib
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from app.application.ports.job_search import JobSearchPort
from app.infrastructure.db.models import JobSource
from app.infrastructure.logging.setup import get_logger

logger = get_logger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 CareerOS/1.0"
)
_TIMEOUT = 30
_MIN_DESCRIPTION_CHARS = 80
_MIN_EXTRACTED_DETAIL_CHARS = 20


def _fetch(url: str) -> str:
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


def _is_blocked_page(html: str) -> bool:
    """Detect maintenance pages, bot blocks, or non-HTML responses."""
    lowered = html.lower()
    if "schemas-microsoft-com:office:office" in lowered and "maintenance" in lowered:
        return True
    if "system maintenance" in lowered and "job bank" in lowered:
        return True
    if "gichet-emplois" in lowered and "maintenance du" in lowered:
        return True
    if len(html) < 500 and "captcha" in lowered:
        return True
    return False


def _extract_description_from_html(html: str) -> str:
    if _is_blocked_page(html):
        return ""

    for pattern in (
        r'<div class="job-posting-details-body[^"]*">(.*?)</div>\s*<div class="job-posting-details-sidebar',
        r'<div class="job-posting-detail-apply[^"]*">(.*?)</div>\s*<div class="job-posting-action',
        r'<section[^>]*id="job-posting[^"]*"[^>]*>(.*?)</section>',
        r'<div[^>]*class="[^"]*job-posting-content[^"]*"[^>]*>(.*?)</div>',
    ):
        match = re.search(pattern, html, re.S | re.I)
        if match:
            text = _strip_tags(match.group(1))
            if len(text) >= _MIN_EXTRACTED_DETAIL_CHARS:
                return text[:8000]

    meta = re.search(
        r'<meta[^>]+(?:name|property)=["\'](?:description|og:description)["\'][^>]+content=["\']([^"\']+)["\']',
        html,
        re.I,
    )
    if meta:
        text = html_lib.unescape(meta.group(1)).strip()
        if len(text) >= _MIN_EXTRACTED_DETAIL_CHARS:
            return text[:8000]

    return ""


def _extract_listing_snippet(block: str) -> str:
    """Pull salary / summary text from a search-results card when detail pages fail."""
    parts: list[str] = []
    for pattern in (
        r'<li class="salary">(.*?)</li>',
        r'<span class="salary">(.*?)</span>',
        r'<li class="date">(.*?)</li>',
        r'<p class="[^"]*description[^"]*">(.*?)</p>',
    ):
        match = re.search(pattern, block, re.S | re.I)
        if match:
            text = _strip_tags(match.group(1))
            if text:
                parts.append(text)
    return " · ".join(parts)


def _strip_tags(text: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_province(location: str) -> tuple[str, str]:
    """Montréal (QC) -> (Montréal, QC)"""
    location = html_lib.unescape(location).strip()
    match = re.search(r"^(.*?)\s*\(([A-Z]{2})\)\s*$", location)
    if match:
        return match.group(1).strip(), match.group(2)
    return location, ""


class JobBankCanadaSearchAdapter(JobSearchPort):
    """Scrape Job Bank Canada search results (jobbank.gc.ca)."""

    BASE = "https://www.jobbank.gc.ca"

    def search(self, source: JobSource) -> list[dict[str, Any]]:
        keywords = _keywords(source, default="software developer")
        location = str(source.config.get("location_string", "") or "Canada")
        max_results = int(source.config.get("max_results", 25))
        all_jobs: list[dict[str, Any]] = []
        seen: set[str] = set()

        try:
            return self._search_all(keywords, location, max_results, str(source.id))
        except Exception as exc:
            logger.warning(
                "job_bank_search_failed",
                error=str(exc),
                source_id=str(source.id),
            )
            return all_jobs

    def _search_all(
        self, keywords: list[str], location: str, max_results: int, source_id: str = ""
    ) -> list[dict[str, Any]]:
        all_jobs: list[dict[str, Any]] = []
        seen: set[str] = set()

        for keyword in keywords:
            remaining = max_results - len(all_jobs)
            if remaining <= 0:
                break
            try:
                batch = self._search_keyword(keyword, location, remaining)
            except urllib.error.URLError as exc:
                logger.warning(
                    "job_bank_search_failed",
                    keyword=keyword,
                    error=str(exc),
                    source_id=str(source.id),
                )
                continue
            for job in batch:
                ext_id = job.get("external_id")
                if ext_id and ext_id not in seen:
                    seen.add(ext_id)
                    all_jobs.append(job)

        logger.info(
            "job_bank_search_complete",
            source_id=source_id,
            keywords=keywords,
            count=len(all_jobs),
        )
        return all_jobs

    def _search_keyword(self, keyword: str, location: str, max_results: int) -> list[dict[str, Any]]:
        params = {
            "searchterm": keyword,
            "searchstring": keyword,
            "locationstring": location or "Canada",
            "locationparam": "",
        }
        url = f"{self.BASE}/jobsearch/jobsearch?{urllib.parse.urlencode(params)}"
        page_html = _fetch(url)
        articles = re.findall(
            r'<article[^>]*id="article-(\d+)"[^>]*>(.*?)</article>',
            page_html,
            flags=re.S | re.I,
        )
        jobs: list[dict[str, Any]] = []
        for job_id, block in articles[:max_results]:
            job = self._parse_listing_block(job_id, block)
            if job:
                jobs.append(job)
        return jobs

    def _parse_listing_block(self, job_id: str, block: str) -> dict[str, Any] | None:
        title_match = re.search(r'<span class="noctitle">\s*(.*?)\s*</span>', block, re.S | re.I)
        company_match = re.search(r'<li class="business">(.*?)</li>', block, re.S | re.I)
        location_match = re.search(r'<li class="location">.*?<span class="wb-inv">Location</span>\s*(.*?)\s*</li>', block, re.S | re.I)
        if not title_match:
            return None

        title = _strip_tags(title_match.group(1))
        company = _strip_tags(company_match.group(1)) if company_match else "Unknown"
        location_raw = _strip_tags(location_match.group(1)) if location_match else ""
        city, province = _parse_province(location_raw)

        source_url = f"{self.BASE}/jobsearch/jobposting/{job_id}"
        listing_snippet = _extract_listing_snippet(block)
        description = self.fetch_description(job_id)
        if not description and listing_snippet:
            description = listing_snippet
            logger.info("job_bank_using_listing_snippet", job_id=job_id)

        return {
            "external_id": job_id,
            "source_url": source_url,
            "title": title,
            "company": company,
            "location_city": city,
            "location_province": province,
            "description": description,
            "raw_payload": {"source": "job_bank_canada", "job_id": job_id},
        }

    def fetch_description(self, job_id: str) -> str:
        """Fetch full posting text from Job Bank (public for re-enrichment)."""
        try:
            detail_html = _fetch(f"{self.BASE}/jobsearch/jobposting/{job_id}")
        except urllib.error.URLError as exc:
            logger.warning("job_bank_detail_fetch_failed", job_id=job_id, error=str(exc))
            return ""
        if _is_blocked_page(detail_html):
            logger.warning("job_bank_detail_blocked", job_id=job_id, reason="maintenance_or_block")
            return ""
        return _extract_description_from_html(detail_html)

    def _fetch_description(self, job_id: str) -> str:
        return self.fetch_description(job_id)


class IndeedCanadaSearchAdapter(JobSearchPort):
    """Scrape Indeed Canada search results (ca.indeed.com)."""

    BASE = "https://ca.indeed.com"

    def search(self, source: JobSource) -> list[dict[str, Any]]:
        keywords = _keywords(source, default="software developer")
        location = str(source.config.get("location_string", "Canada") or "Canada")
        max_results = int(source.config.get("max_results", 15))
        all_jobs: list[dict[str, Any]] = []
        seen: set[str] = set()

        for keyword in keywords:
            remaining = max_results - len(all_jobs)
            if remaining <= 0:
                break
            try:
                batch = self._search_keyword(keyword, location, remaining)
            except urllib.error.URLError as exc:
                logger.warning(
                    "indeed_search_failed",
                    keyword=keyword,
                    error=str(exc),
                    source_id=str(source.id),
                )
                continue
            for job in batch:
                ext_id = job.get("external_id")
                if ext_id and ext_id not in seen:
                    seen.add(ext_id)
                    all_jobs.append(job)

        logger.info(
            "indeed_search_complete",
            source_id=str(source.id),
            keywords=keywords,
            count=len(all_jobs),
        )
        return all_jobs

    def _search_keyword(self, keyword: str, location: str, max_results: int) -> list[dict[str, Any]]:
        params = {"q": keyword, "l": location}
        url = f"{self.BASE}/jobs?{urllib.parse.urlencode(params)}"
        page_html = _fetch(url)
        if "captcha" in page_html.lower() or "challenge" in page_html.lower():
            logger.warning("indeed_captcha_or_block", keyword=keyword)
            return []

        cards = re.findall(
            r'<div[^>]*data-jk="([a-f0-9]+)"[^>]*>(.*?)(?=<div[^>]*data-jk=|$)',
            page_html,
            flags=re.S | re.I,
        )
        jobs: list[dict[str, Any]] = []
        for jk, block in cards[:max_results]:
            job = self._parse_card(jk, block)
            if job:
                jobs.append(job)
        return jobs

    def _parse_card(self, jk: str, block: str) -> dict[str, Any] | None:
        title_match = re.search(r'aria-label="([^"]+)"[^>]*class="[^"]*jcs-JobTitle', block, re.I)
        if not title_match:
            title_match = re.search(r'<span[^>]*title="([^"]+)"', block, re.I)
        company_match = re.search(r'data-testid="company-name"[^>]*>(.*?)</', block, re.S | re.I)
        location_match = re.search(r'data-testid="text-location"[^>]*>(.*?)</', block, re.S | re.I)
        if not title_match:
            return None

        title = _strip_tags(title_match.group(1))
        company = _strip_tags(company_match.group(1)) if company_match else "Unknown"
        location_raw = _strip_tags(location_match.group(1)) if location_match else ""
        city, province = _parse_province(location_raw.replace(",", " (").rstrip(")") + ")" if "(" not in location_raw else location_raw)

        if not province and ", " in location_raw:
            parts = [p.strip() for p in location_raw.split(",")]
            city = parts[0]
            province = parts[1][:2].upper() if len(parts) > 1 else ""

        source_url = f"{self.BASE}/viewjob?jk={jk}"
        snippet_match = re.search(r'class="[^"]*job-snippet[^"]*"[^>]*>(.*?)</div>', block, re.S | re.I)
        description = _strip_tags(snippet_match.group(1)) if snippet_match else ""

        return {
            "external_id": jk,
            "source_url": source_url,
            "title": title,
            "company": company,
            "location_city": city,
            "location_province": province,
            "description": description,
            "raw_payload": {"source": "indeed", "jk": jk},
        }


class ManualUrlImportSearchAdapter(JobSearchPort):
    """Manual import — no automated search."""

    def search(self, source: JobSource) -> list[dict[str, Any]]:
        return []


class NotImplementedSearchAdapter(JobSearchPort):
    """Placeholder for sources without live search yet."""

    def search(self, source: JobSource) -> list[dict[str, Any]]:
        logger.info(
            "job_search_not_implemented",
            preset_key=source.preset_key,
            source_id=str(source.id),
        )
        return []


def _keywords(source: JobSource, default: str) -> list[str]:
    raw = source.config.get("search_keywords")
    if raw is None:
        raw = source.config.get("keywords")
    if raw is None:
        return [default]
    if isinstance(raw, str):
        return [k.strip() for k in raw.split(",") if k.strip()]
    if isinstance(raw, list):
        return [str(k).strip() for k in raw if str(k).strip()]
    return [default]
