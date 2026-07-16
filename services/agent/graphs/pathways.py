"""Immigration pathway evaluation from versioned JSON rules."""

from __future__ import annotations

from typing import Any

from lib.data_loaders import load_json


def evaluate_pathways(noc_code: str | None, teer_level: int | None, province: str | None) -> dict[str, Any]:
    if not noc_code:
        return {"ee_eligible": False, "ee_categories": [], "pnp_streams": [], "aip_relevant": False}

    teer = teer_level if teer_level is not None else 99
    ee_eligible = teer <= 3

    ee_data = load_json("ee_categories.json")
    ee_categories: list[str] = []
    for cat in ee_data.get("categories", []):
        if cat.get("all_teer_0_3"):
            if ee_eligible:
                ee_categories.append(cat["id"])
            continue
        codes = set(cat.get("noc_codes", []))
        min_teer = cat.get("min_teer", 0)
        max_teer = cat.get("max_teer", 5)
        if noc_code in codes and min_teer <= teer <= max_teer:
            ee_categories.append(cat["id"])

    pnp_data = load_json("pnp_streams.json")
    pnp_streams: list[str] = []
    prov = (province or "").upper()
    for stream in pnp_data.get("streams", []):
        stream_prov = stream.get("province", "")
        if stream_prov == "ATL":
            atl = stream.get("provinces", ["NB", "NL", "NS", "PE"])
            if prov in atl:
                pnp_streams.append(stream["id"])
            continue
        if prov and stream_prov != prov:
            continue
        codes = set(stream.get("noc_codes", []))
        if not codes or noc_code in codes:
            min_teer = stream.get("min_teer", 0)
            max_teer = stream.get("max_teer", 5)
            if min_teer <= teer <= max_teer:
                pnp_streams.append(stream["id"])

    aip_relevant = prov in ("NB", "NL", "NS", "PE") and teer <= 4

    return {
        "ee_eligible": ee_eligible,
        "ee_categories": ee_categories,
        "pnp_streams": pnp_streams,
        "aip_relevant": aip_relevant,
    }
