"""Load versioned reference data files."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@lru_cache
def load_json(name: str) -> dict:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def wage_median(noc_code: str, region: str) -> float | None:
    data = load_json("wage_data.json")
    for entry in data.get("entries", []):
        if entry["noc_code"] == noc_code and entry["region"] == region:
            return float(entry["median_hourly"])
    return None


def teer_for_noc(noc_code: str) -> int | None:
    data = load_json("noc_2021.json")
    for ug in data.get("unit_groups", []):
        if ug["code"] == noc_code:
            return int(ug["teer"])
    return None
