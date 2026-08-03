"""PR delta: how much does taking THIS job move THIS candidate's PR odds?

This is the question the product exists to answer. Everything else — NOC codes, TEER
levels, wage-vs-median — is evidence supporting the answer, not the answer.

The model rests on one fact: since 2025-03-25 a job offer is worth zero CRS points.
So a job can only help in three ways, and this module scores exactly those three:

  1. **Experience accrual** — 12 months of Canadian work raises core CRS points and
     can unlock skill-transferability blocks.
  2. **Category eligibility** — 12 months in an eligible NOC (within 3 years) makes
     the candidate eligible for category-based rounds, which usually have far lower
     cut-offs than general rounds.
  3. **Program eligibility** — CEC needs 12 months of Canadian TEER 0-3 experience;
     provincial streams may key off the NOC and province.

Informational only. Not immigration advice.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from lib.crs import CrsProfile, calculate_crs
from lib.data_loaders import load_json
from lib.draws import category_activity, draws_metadata, typical_cutoff

#: A candidate needs this much experience in an eligible occupation to qualify for a
#: category-based round (accumulated within the previous 3 years, not necessarily
#: continuous). Raised from 6 months for 2026.
CATEGORY_MIN_MONTHS = 12

#: Canadian Experience Class threshold.
CEC_MIN_MONTHS = 12
CEC_ELIGIBLE_TEERS = {0, 1, 2, 3}


@dataclass
class JobContext:
    noc_code: str | None
    teer_level: int | None
    province: str | None
    title: str = ""
    employer: str = ""


def _categories() -> list[dict[str, Any]]:
    return load_json("ee_categories.json").get("categories", [])


def _category_match(
    category: dict[str, Any],
    noc_code: str | None,
    teer_level: int | None,
    has_french: bool,
) -> tuple[bool, str]:
    """Return (matches, reason). Unverified NOC lists never assert a match."""
    if category.get("exclude_from_job_scoring"):
        return False, "Not inferable from a job posting."

    if category.get("all_teer_0_3"):
        if not has_french:
            return False, f"Needs NCLC {category.get('requires_french_nclc_min', 7)}+ French."
        if teer_level is None or teer_level > 3:
            return False, "Needs a TEER 0-3 role."
        return True, "TEER 0-3 role and French proficiency on file."

    if not noc_code:
        return False, "Job has no NOC code mapped."

    min_teer = category.get("min_teer", 0)
    max_teer = category.get("max_teer", 5)
    if teer_level is not None and not (min_teer <= teer_level <= max_teer):
        return False, f"Category covers TEER {min_teer}-{max_teer}; this role is TEER {teer_level}."

    codes = set(category.get("noc_codes") or [])
    status = category.get("verification_status", "unverified")

    if status != "verified":
        if codes and noc_code in codes:
            return False, "Possible match, but this category's NOC list is not yet verified against IRCC."
        return False, "Category NOC list not yet verified against IRCC."

    if noc_code in codes:
        return True, f"NOC {noc_code} is on the published list."
    return False, f"NOC {noc_code} is not on the published list."


def _pnp_streams(noc_code: str | None, province: str | None) -> list[str]:
    if not noc_code:
        return []
    data = load_json("pnp_streams.json")
    prov = (province or "").upper()
    out: list[str] = []
    for stream in data.get("streams", []):
        stream_prov = stream.get("province", "")
        if stream_prov == "ATL":
            if prov in stream.get("provinces", ["NB", "NL", "NS", "PE"]):
                out.append(stream["id"])
            continue
        if prov and stream_prov != prov:
            continue
        codes = set(stream.get("noc_codes", []))
        if not codes or noc_code in codes:
            out.append(stream["id"])
    return out


def _with_extra_year(profile: CrsProfile) -> CrsProfile:
    future = copy.deepcopy(profile)
    future.canadian_experience_years = min(profile.canadian_experience_years + 1, 5)
    return future


def evaluate_job(
    profile: CrsProfile,
    job: JobContext,
    canadian_months_in_noc: int = 0,
) -> dict[str, Any]:
    """Score one job by how far it moves the candidate toward an ITA."""
    crs_now = calculate_crs(profile)
    crs_future = calculate_crs(_with_extra_year(profile))
    delta = crs_future.total - crs_now.total

    has_french = profile.second_language.minimum() >= 7
    months_after = canadian_months_in_noc + 12

    unlocked: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    needs_verification: list[dict[str, Any]] = []

    for category in _categories():
        matches, reason = _category_match(category, job.noc_code, job.teer_level, has_french)
        # Draw history keys `french` where the catalogue keys `french_proficiency`.
        cat_id = category["id"]
        activity = category_activity(category.get("draw_category_id") or cat_id)
        entry = {
            "id": cat_id,
            "label": category.get("label", cat_id),
            "reason": reason,
            "typical_cutoff": activity["typical_cutoff"],
            "rounds_last_12_months": activity["rounds"],
            "itas_last_12_months": activity["total_itas"],
            "last_drawn": activity["last_drawn"],
        }

        if matches:
            cutoff = activity["typical_cutoff"]
            entry["eligible_after_months"] = max(0, CATEGORY_MIN_MONTHS - canadian_months_in_noc)
            if cutoff is not None:
                entry["gap_after_12_months"] = crs_future.total - cutoff
                entry["clears_typical_cutoff"] = crs_future.total >= cutoff
            unlocked.append(entry)
        elif category.get("verification_status") != "verified" and not category.get(
            "exclude_from_job_scoring"
        ):
            needs_verification.append(entry)
        else:
            blocked.append(entry)

    # Program-based routes, which do not depend on the category NOC lists.
    programs: list[dict[str, Any]] = []
    cec_eligible = (
        job.teer_level in CEC_ELIGIBLE_TEERS
        and months_after >= CEC_MIN_MONTHS
    )
    cec_cutoff = typical_cutoff("cec")
    programs.append(
        {
            "id": "cec",
            "label": "Canadian Experience Class",
            "eligible_after_this_job": cec_eligible,
            "typical_cutoff": cec_cutoff,
            "gap_after_12_months": (crs_future.total - cec_cutoff) if cec_cutoff else None,
            "reason": (
                f"12 months in a TEER {job.teer_level} role meets the CEC experience threshold."
                if cec_eligible
                else f"CEC needs TEER 0-3 Canadian experience; this role is TEER {job.teer_level}."
            ),
        }
    )

    streams = _pnp_streams(job.noc_code, job.province)
    pnp_cutoff = typical_cutoff("pnp")
    programs.append(
        {
            "id": "pnp",
            "label": "Provincial Nominee Program",
            "eligible_after_this_job": bool(streams),
            "streams": streams,
            "typical_cutoff": pnp_cutoff,
            "note": (
                "A provincial nomination adds 600 CRS points, which effectively guarantees an ITA. "
                "PNP round cut-offs look high only because every candidate in them already holds "
                "that 600-point nomination."
            ),
            "reason": (
                f"NOC {job.noc_code} may align with {len(streams)} stream(s) in {job.province}."
                if streams
                else "No matching provincial stream found for this NOC and province."
            ),
        }
    )

    best_route = _pick_best_route(crs_future.total, unlocked, programs)

    return {
        "job": {
            "title": job.title,
            "employer": job.employer,
            "noc_code": job.noc_code,
            "teer_level": job.teer_level,
            "province": job.province,
        },
        "crs_now": crs_now.to_dict(),
        "crs_after_12_months": crs_future.to_dict(),
        "crs_delta": delta,
        "arranged_employment_points": 0,
        "arranged_employment_note": (
            "IRCC removed arranged-employment CRS points on 2025-03-25. This job offer adds no "
            "points by itself — its value is the experience, category eligibility and provincial "
            "streams it unlocks."
        ),
        "unlocked_categories": sorted(
            unlocked, key=lambda c: (c.get("gap_after_12_months") is None, -(c.get("gap_after_12_months") or 0))
        ),
        "blocked_categories": blocked,
        "needs_verification": needs_verification,
        "programs": programs,
        "best_route": best_route,
        "draws_metadata": draws_metadata(),
    }


def _pick_best_route(
    future_score: int,
    unlocked: list[dict[str, Any]],
    programs: list[dict[str, Any]],
) -> dict[str, Any]:
    """The single most useful sentence we can say about this job."""
    candidates: list[dict[str, Any]] = []

    for cat in unlocked:
        gap = cat.get("gap_after_12_months")
        if gap is None or cat.get("rounds_last_12_months", 0) == 0:
            continue
        candidates.append(
            {
                "route": cat["label"],
                "kind": "category",
                "gap": gap,
                "cutoff": cat["typical_cutoff"],
                "itas_last_12_months": cat.get("itas_last_12_months", 0),
            }
        )

    for prog in programs:
        if prog["id"] == "cec" and prog.get("eligible_after_this_job") and prog.get("typical_cutoff"):
            candidates.append(
                {
                    "route": prog["label"],
                    "kind": "program",
                    "gap": prog["gap_after_12_months"],
                    "cutoff": prog["typical_cutoff"],
                    "itas_last_12_months": 0,
                }
            )

    clearing = [c for c in candidates if c["gap"] >= 0]
    if clearing:
        best = max(clearing, key=lambda c: (c["gap"], c["itas_last_12_months"]))
        return {
            **best,
            "verdict": "clears",
            "summary": (
                f"After 12 months in this role your CRS would be {future_score}, which clears the "
                f"recent {best['route']} cut-off of {best['cutoff']} by {best['gap']} points."
            ),
        }

    if candidates:
        best = max(candidates, key=lambda c: c["gap"])
        return {
            **best,
            "verdict": "short",
            "summary": (
                f"After 12 months in this role your CRS would be {future_score}. Your closest route "
                f"is {best['route']} at a recent cut-off of {best['cutoff']} — still "
                f"{abs(best['gap'])} points short."
            ),
        }

    return {
        "route": None,
        "kind": None,
        "gap": None,
        "cutoff": None,
        "verdict": "no_route",
        "summary": (
            "This role does not open a category-based or CEC route on the data available. "
            "A provincial nomination would be the realistic path."
        ),
    }
