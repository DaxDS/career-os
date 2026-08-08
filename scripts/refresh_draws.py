"""Refresh Express Entry draw history from IRCC's official feed.

Replaces the original hand-seeded draws.json, which was transcribed from two
third-party trackers and went stale the moment a new round was held. IRCC publishes
every round as JSON at a stable URL; this reads that directly, so the data has one
authoritative source and refreshing is a single command.

    python scripts/refresh_draws.py            # refresh current year
    python scripts/refresh_draws.py --year 2025

Then regenerate the derived files the app reads:

    python scripts/gen_draw_snapshot.py

The endpoint rejects requests without a browser-like User-Agent, which is why one is
set explicitly below rather than relying on urllib's default.
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DRAWS_PATH = ROOT / "services" / "agent" / "data" / "draws.json"

FEED_URL = "https://www.canada.ca/content/dam/ircc/documents/json/ee_rounds_123_en.json"
SOURCE_PAGE = (
    "https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/"
    "express-entry/submit-profile/rounds-invitations.html"
)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 CareerOS/1.0"
)

#: IRCC's draw names carry a year and a version suffix that changes between seasons
#: ("Trades Occupations, 2026-Version 3"), so matching is done on stable keywords
#: rather than on the full string. Order matters: the first match wins, so the more
#: specific patterns must come before the general ones — "Physicians with Canadian
#: Work Experience" would otherwise be caught by a bare "canadian experience" rule.
CATEGORY_PATTERNS: list[tuple[str, str]] = [
    (r"physician", "physicians"),
    (r"senior manager", "senior_managers"),
    (r"researcher", "researchers"),
    (r"military", "military"),
    (r"transport", "transport"),
    (r"healthcare|health care|social services", "healthcare"),
    (r"\bstem\b|science, technology", "stem"),
    (r"trade", "trades"),
    (r"education", "education"),
    (r"agricultur|agri-food", "agriculture"),
    (r"french", "french"),
    (r"canadian experience class", "cec"),
    (r"provincial nominee", "pnp"),
    (r"federal skilled worker", "fsw"),
    (r"federal skilled trades", "fst"),
    (r"general", "general"),
    (r"no program specified", "general"),
]


def classify(draw_name: str) -> str | None:
    name = (draw_name or "").lower()
    for pattern, category in CATEGORY_PATTERNS:
        if re.search(pattern, name):
            return category
    return None


def to_int(value: object) -> int | None:
    try:
        return int(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def fetch_rounds() -> list[dict]:
    request = urllib.request.Request(FEED_URL, headers={"User-Agent": USER_AGENT})
    context = ssl.create_default_context()
    with urllib.request.urlopen(request, timeout=30, context=context) as response:
        payload = json.loads(response.read().decode("utf-8", "replace"))
    return payload.get("rounds", [])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", default=str(date.today().year))
    args = parser.parse_args()

    raw = fetch_rounds()
    if not raw:
        print("No rounds returned — feed shape may have changed. Aborting without writing.")
        return 1

    draws: list[dict] = []
    unmapped: set[str] = set()

    for entry in raw:
        drawn_on = (entry.get("drawDate") or "").strip()
        if not drawn_on.startswith(args.year):
            continue

        category = classify(entry.get("drawName", ""))
        if category is None:
            unmapped.add(entry.get("drawName", "?"))
            continue

        number = to_int(entry.get("drawNumber"))
        cutoff = to_int(entry.get("drawCRS"))
        itas = to_int(entry.get("drawSize"))
        if number is None or cutoff is None:
            continue

        draws.append(
            {
                "round": number,
                "date": drawn_on,
                "category": category,
                "itas": itas or 0,
                "crs_cutoff": cutoff,
            }
        )

    if not draws:
        print(f"No {args.year} rounds found. Aborting without writing.")
        return 1

    draws.sort(key=lambda d: d["round"], reverse=True)

    existing = json.loads(DRAWS_PATH.read_text(encoding="utf-8"))
    previous_rounds = {d["round"] for d in existing.get("draws", [])}
    added = sorted(d["round"] for d in draws if d["round"] not in previous_rounds)

    existing["draws"] = draws
    existing["last_verified"] = datetime.now(timezone.utc).date().isoformat()
    existing["source_url"] = SOURCE_PAGE
    existing["seed_provenance"] = (
        f"Pulled from IRCC's official rounds feed ({FEED_URL}) by scripts/refresh_draws.py. "
        "Authoritative — supersedes the original hand-transcribed seed."
    )

    DRAWS_PATH.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {len(draws)} rounds for {args.year} -> {DRAWS_PATH.relative_to(ROOT)}")
    if added:
        print(f"new rounds added: {added}")
    else:
        print("no new rounds since last refresh")
    if unmapped:
        # Loud on purpose: an unmapped name means a category silently vanishes from
        # the draw board, which reads as "dormant" — the exact false signal this
        # product exists to prevent.
        print("\nWARNING — unmapped draw names (add a pattern to CATEGORY_PATTERNS):")
        for name in sorted(unmapped):
            print(f"  {name}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
