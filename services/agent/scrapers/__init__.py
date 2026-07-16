"""Scrape result normalization."""

from scrapers.adzuna import search_adzuna
from scrapers.jobbank import RawJobListing, search_job_bank
from scrapers.jsearch import search_jsearch


def search_all_sources(keywords: list[str], location: str) -> list[RawJobListing]:
    if not keywords:
        keywords = ["software developer"]
    per_source = max(10, 25 // 3)
    listings: list[RawJobListing] = []
    listings.extend(search_job_bank(keywords, location, per_source))
    listings.extend(search_jsearch(keywords, location, per_source))
    listings.extend(search_adzuna(keywords, location, per_source))
    return listings
