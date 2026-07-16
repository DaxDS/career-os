"""Agent transparency — standardized activity_log writes."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from lib.supabase_client import get_supabase


def format_filter_summary(filter_reasons: Mapping[str, int]) -> str:
    """Build plain-language summary for eligibility filter skips."""
    total = sum(filter_reasons.values())
    if total == 0:
        return ""
    parts = [
        f"{count} {reason.lower()}"
        for reason, count in sorted(filter_reasons.items(), key=lambda item: -item[1])
    ]
    return f"{total} jobs filtered out: {', '.join(parts)}"


SOURCE_LABELS: dict[str, str] = {
    "job_bank": "Job Bank",
    "jsearch": "JSearch",
    "adzuna": "Adzuna",
}


def log_activity(
    user_id: str,
    action: str,
    summary: str,
    metadata: dict[str, Any] | None = None,
    *,
    entity_type: str | None = None,
    entity_id: str | None = None,
) -> None:
    row: dict[str, Any] = {
        "user_id": user_id,
        "action": action,
        "summary": summary,
        "metadata": metadata or {},
    }
    if entity_type is not None:
        row["entity_type"] = entity_type
    if entity_id is not None:
        row["entity_id"] = entity_id
    get_supabase().table("activity_log").insert(row).execute()
