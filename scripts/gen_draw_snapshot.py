"""Generate the marketing draw snapshot from the agent's draw history.

The landing page makes a factual claim — which categories are live and which are
dormant. That claim must come from the same data the product scores against, or the
marketing and the report will eventually contradict each other.

Run after refreshing services/agent/data/draws.json:

    python scripts/gen_draw_snapshot.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENT = ROOT / "services" / "agent"
sys.path.insert(0, str(AGENT))

from lib.data_loaders import load_json  # noqa: E402
from lib.draws import all_category_activity, draws_metadata  # noqa: E402

OUT = ROOT / "apps" / "web" / "src" / "lib" / "draw-snapshot.json"

PROGRAM_LABELS = {
    "general": "General round",
    "cec": "Canadian Experience Class",
    "fsw": "Federal Skilled Worker",
    "fst": "Federal Skilled Trades",
    "pnp": "Provincial Nominee Program",
}


def main() -> None:
    catalogue = {c["id"]: c for c in load_json("ee_categories.json").get("categories", [])}
    by_draw_id = {(c.get("draw_category_id") or c["id"]): c for c in catalogue.values()}

    activity = all_category_activity(12)
    live, dormant = [], []

    for cat_id, stats in activity.items():
        meta = by_draw_id.get(cat_id, {})
        entry = {
            "id": cat_id,
            "label": meta.get("label") or PROGRAM_LABELS.get(cat_id, cat_id.replace("_", " ").title()),
            "rounds": stats["rounds"],
            "itas": stats["total_itas"],
            "lastDrawn": stats["last_drawn"],
            "typicalCutoff": stats["typical_cutoff"],
        }
        (live if stats["rounds"] > 0 else dormant).append(entry)

    live.sort(key=lambda c: c["itas"], reverse=True)
    dormant.sort(key=lambda c: c["label"])

    payload = {
        "_generated_by": "scripts/gen_draw_snapshot.py — do not edit by hand",
        "asOf": draws_metadata()["last_verified"],
        "sourceUrl": draws_metadata()["source_url"],
        "windowMonths": 12,
        "live": live,
        "dormant": dormant,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}  ({len(live)} live, {len(dormant)} dormant)")


if __name__ == "__main__":
    main()
