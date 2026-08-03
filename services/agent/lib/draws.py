"""Express Entry round-of-invitation history: loading and summary statistics.

Cut-offs describe rounds that already happened. Nothing here predicts future rounds,
and callers must not present these numbers as thresholds a candidate is guaranteed
to clear.
"""

from __future__ import annotations

import statistics
from datetime import date, datetime
from typing import Any

from lib.data_loaders import load_json

#: Rounds open to any eligible candidate regardless of occupation.
PROGRAM_ROUNDS = {"general", "cec", "fsw", "fst", "pnp"}


def _parse(d: str) -> date:
    return date.fromisoformat(d[:10])


def load_draws() -> list[dict[str, Any]]:
    data = load_json("draws.json")
    draws = data.get("draws", [])
    return sorted(draws, key=lambda d: d["date"], reverse=True)


def draws_metadata() -> dict[str, Any]:
    data = load_json("draws.json")
    return {
        "last_verified": data.get("last_verified"),
        "source_url": data.get("source_url"),
        "seed_provenance": data.get("seed_provenance"),
        "disclaimer": data.get("disclaimer"),
    }


def recent_draws(category: str, limit: int = 3, within_months: int | None = 18) -> list[dict[str, Any]]:
    """Most recent rounds for a category, newest first."""
    cutoff_date = None
    if within_months:
        today = date.today()
        month = today.month - (within_months % 12)
        year = today.year - (within_months // 12)
        if month <= 0:
            month += 12
            year -= 1
        cutoff_date = date(year, month, 1)

    out = []
    for d in load_draws():
        if d.get("category") != category:
            continue
        if cutoff_date and _parse(d["date"]) < cutoff_date:
            continue
        out.append(d)
        if len(out) >= limit:
            break
    return out


def typical_cutoff(category: str, sample: int = 3) -> int | None:
    """Median cut-off across the most recent rounds for a category.

    Median rather than latest, because single rounds swing hard — a 4-ITA round can
    post a cut-off tens of points away from the category's normal range.
    """
    rounds = recent_draws(category, limit=sample)
    if not rounds:
        return None
    return int(statistics.median(r["crs_cutoff"] for r in rounds))


def cutoff_range(category: str, sample: int = 6) -> tuple[int, int] | None:
    rounds = recent_draws(category, limit=sample)
    if not rounds:
        return None
    scores = [r["crs_cutoff"] for r in rounds]
    return (min(scores), max(scores))


def last_drawn(category: str) -> str | None:
    rounds = recent_draws(category, limit=1, within_months=None)
    return rounds[0]["date"] if rounds else None


def category_activity(category: str, months: int = 12) -> dict[str, Any]:
    """How live a category is: rounds held and ITAs issued in the recent window."""
    rounds = recent_draws(category, limit=100, within_months=months)
    return {
        "rounds": len(rounds),
        "total_itas": sum(r.get("itas", 0) for r in rounds),
        "last_drawn": rounds[0]["date"] if rounds else None,
        "typical_cutoff": typical_cutoff(category),
        "cutoff_range": cutoff_range(category),
    }


def all_category_activity(months: int = 12) -> dict[str, dict[str, Any]]:
    data = load_json("draws.json")
    return {cat: category_activity(cat, months) for cat in data.get("category_ids", [])}


def summarize_for_report(months: int = 12) -> dict[str, Any]:
    activity = all_category_activity(months)
    live = {k: v for k, v in activity.items() if v["rounds"] > 0}
    return {
        "window_months": months,
        "metadata": draws_metadata(),
        "generated_at": datetime.now().isoformat(),
        "categories": live,
        "dormant_categories": sorted(k for k, v in activity.items() if v["rounds"] == 0),
    }
