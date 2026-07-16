"""Discovery pipeline — find, dedupe, parse, classify, filter, match, persist."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from graphs.matching import enrich_wage_median, score_match
from graphs.noc_classify import classify_posting
from graphs.pathways import evaluate_pathways
from lib.activity_log import SOURCE_LABELS, format_filter_summary, log_activity
from lib.dedup import compute_dedupe_hash
from lib.supabase_client import get_supabase
from parsers.eligibility import is_eligible
from parsers.jd_parser import parse_jd
from scrapers import search_all_sources


def _load_user_context(user_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    sb = get_supabase()
    profile = sb.table("profiles").select("*").eq("id", user_id).single().execute().data
    work_history = (
        sb.table("work_history").select("*").eq("user_id", user_id).order("sort_order").execute().data
        or []
    )
    return profile, work_history


def _existing_dedupe_hashes() -> set[str]:
    sb = get_supabase()
    rows = sb.table("jobs").select("dedupe_hash").execute().data or []
    return {r["dedupe_hash"] for r in rows if r.get("dedupe_hash")}


def _annual_to_hourly(wage: float | None, period: str | None) -> float | None:
    if wage is None:
        return None
    if period == "annual":
        return round(wage / 2080, 2)
    return wage


def run_discovery(user_id: str) -> dict[str, Any]:
    profile, work_history = _load_user_context(user_id)
    keywords = profile.get("target_titles") or ["software developer"]
    location = profile.get("province") or "Canada"
    threshold = float(profile.get("match_score_threshold") or 65)

    log_activity(
        user_id,
        "discovery_started",
        f"Started job discovery in {location} for {', '.join(keywords[:3])}",
        {"keywords": keywords, "location": location},
    )

    listings = search_all_sources(keywords, location)
    source_counts = Counter(listing.source for listing in listings)
    for source, count in sorted(source_counts.items()):
        label = SOURCE_LABELS.get(source, source.replace("_", " ").title())
        log_activity(
            user_id,
            "source_searched",
            f"Searched {label}: {count} results",
            {"source": source, "count": count},
        )

    seen_hashes = _existing_dedupe_hashes()
    sb = get_supabase()
    filter_reasons: Counter[str] = Counter()

    stats = {
        "found": len(listings),
        "inserted_jobs": 0,
        "matches_created": 0,
        "filtered_ineligible": 0,
        "skipped_dedup": 0,
        "below_threshold": 0,
    }

    for listing in listings:
        dedupe = compute_dedupe_hash(listing.company, listing.title, listing.province, listing.city)
        if dedupe in seen_hashes:
            stats["skipped_dedup"] += 1
            continue

        parsed = parse_jd(listing.title, listing.description, listing.company)
        noc = classify_posting(listing.title, listing.description, listing.noc_code)

        parsed_dict = parsed.model_dump()
        wage_hourly = _annual_to_hourly(parsed.wage_offered, parsed.wage_period)

        job_row = {
            "source": listing.source,
            "external_id": listing.external_id,
            "url": listing.url,
            "company": listing.company,
            "title": listing.title,
            "province": listing.province or None,
            "city": listing.city or None,
            "remote": parsed.remote,
            "posted_at": listing.posted_at or datetime.now(timezone.utc).isoformat(),
            "raw_jd": listing.description,
            "parsed_requirements": parsed_dict,
            "noc_code": noc.noc_code,
            "teer_level": noc.teer_level,
            "noc_confidence": float(noc.confidence),
            "wage_offered": wage_hourly,
            "wage_currency": "CAD",
            "bilingual_required": parsed.bilingual_required or parsed.french_required,
            "work_auth_required": parsed.work_auth_required,
            "lmia_flag": parsed.lmia_flag,
            "clearance_required": parsed.clearance_required,
            "dedupe_hash": dedupe,
        }
        job_row["wage_median_region"] = enrich_wage_median(job_row)

        eligible, reason = is_eligible(profile, parsed_dict, job_row)
        if not eligible:
            stats["filtered_ineligible"] += 1
            filter_reasons[reason or "Ineligible"] += 1
            continue

        try:
            inserted = sb.table("jobs").insert(job_row).execute().data
        except Exception:
            stats["skipped_dedup"] += 1
            continue

        if not inserted:
            continue
        job = inserted[0]
        seen_hashes.add(dedupe)
        stats["inserted_jobs"] += 1

        if noc.noc_code:
            log_activity(
                user_id,
                "noc_classified",
                f"Classified NOC {noc.noc_code} (confidence {float(noc.confidence):.2f})",
                {
                    "job_id": job["id"],
                    "job_title": job.get("title"),
                    "noc_code": noc.noc_code,
                    "teer_level": noc.teer_level,
                    "confidence": float(noc.confidence),
                },
                entity_type="job",
                entity_id=job["id"],
            )

        match_score, breakdown = score_match(profile, work_history, job, parsed_dict)
        pathway_flags = evaluate_pathways(job.get("noc_code"), job.get("teer_level"), job.get("province"))

        if match_score < threshold:
            stats["below_threshold"] += 1
            continue

        sb.table("matches").upsert(
            {
                "user_id": user_id,
                "job_id": job["id"],
                "match_score": match_score,
                "score_breakdown": breakdown,
                "pathway_flags": pathway_flags,
                "status": "new",
            },
            on_conflict="user_id,job_id",
        ).execute()
        stats["matches_created"] += 1

    filter_summary = format_filter_summary(filter_reasons)
    if filter_summary:
        log_activity(
            user_id,
            "jobs_filtered",
            filter_summary,
            {"reasons": dict(filter_reasons), "total": sum(filter_reasons.values())},
        )

    if stats["below_threshold"] > 0:
        log_activity(
            user_id,
            "matches_below_threshold",
            f"{stats['below_threshold']} jobs below your match threshold ({threshold:.0f})",
            {"below_threshold": stats["below_threshold"], "threshold": threshold},
        )

    if stats["skipped_dedup"] > 0:
        log_activity(
            user_id,
            "jobs_skipped_dedup",
            f"Skipped {stats['skipped_dedup']} duplicate listings already in the database",
            {"skipped_dedup": stats["skipped_dedup"]},
        )

    completion_summary = (
        f"Discovery finished: {stats['matches_created']} new matches from "
        f"{stats['found']} listings ({stats['inserted_jobs']} new jobs saved)"
    )
    log_activity(user_id, "discovery_completed", completion_summary, stats)
    return stats
