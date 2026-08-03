"""PR situational report: a real CRS score, live draw activity, and what to do next.

This is the artifact a user pays for, so it holds itself to three rules:

  1. **Every claim carries its evidence.** A score shows its breakdown; a cut-off shows
     its date and round count. No bare assertions.
  2. **Dormant categories are called dormant.** Being on IRCC's published category list
     means nothing if no round has been held. A category with zero rounds in the window
     is reported as dormant, not as an opportunity.
  3. **Unverified data never becomes advice.** If a category's NOC list has not been
     checked against IRCC, the report says so instead of guessing.

Informational only. Not immigration advice.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from graphs.pathways import evaluate_pathways
from lib.activity_log import log_activity
from lib.crs import calculate_crs, profile_from_db
from lib.data_loaders import load_json, teer_for_noc
from lib.draws import all_category_activity, draws_metadata, typical_cutoff
from lib.plan_limits import PlanLimitExceeded, check_pathway_report_allowed
from lib.supabase_client import get_supabase

DISCLAIMER = (
    "This is informational only, based on published program criteria, and is not immigration advice. "
    "Consult a licensed RCIC or immigration lawyer for decisions."
)

#: A category with no rounds in this window is treated as dormant.
DORMANCY_WINDOW_MONTHS = 12

#: Program rounds are not occupation categories, so they have no entry in
#: ee_categories.json and need their own display names.
PROGRAM_LABELS = {
    "general": "General (all-program) round",
    "cec": "Canadian Experience Class",
    "fsw": "Federal Skilled Worker",
    "fst": "Federal Skilled Trades",
    "pnp": "Provincial Nominee Program",
}

#: Category-based selection requires this much experience in an eligible occupation,
#: accumulated within the preceding 3 years. Raised from 6 months for 2026.
CATEGORY_MIN_MONTHS = 12
CEC_MIN_MONTHS = 12
CEC_ELIGIBLE_TEERS = {0, 1, 2, 3}


def _months_between(start: str | None, end: str | None, is_current: bool) -> int:
    if not start:
        return 0
    try:
        s = date.fromisoformat(str(start)[:10])
        e = date.today() if is_current or not end else date.fromisoformat(str(end)[:10])
        return max(0, (e.year - s.year) * 12 + (e.month - s.month))
    except ValueError:
        return 0


def _split_experience(work_history: list[dict]) -> tuple[int, int, dict[str, int]]:
    """Return (canadian_months, foreign_months, canadian_months_by_noc)."""
    by_noc: dict[str, int] = {}
    canadian = 0
    foreign = 0
    for wh in work_history:
        months = wh.get("months_canadian_experience") or _months_between(
            wh.get("start_date"), wh.get("end_date"), wh.get("is_current", False)
        )
        if (wh.get("country") or "CA").upper() in ("CA", "CANADA"):
            canadian += months
            noc = wh.get("mapped_noc_code")
            if noc:
                by_noc[noc] = by_noc.get(noc, 0) + months
        else:
            foreign += months
    return canadian, foreign, by_noc


def _draw_landscape() -> dict[str, Any]:
    """Which categories are actually being drawn, and which are dormant."""
    activity = all_category_activity(DORMANCY_WINDOW_MONTHS)
    catalogue = {c["id"]: c for c in load_json("ee_categories.json").get("categories", [])}

    live: list[dict[str, Any]] = []
    dormant: list[dict[str, Any]] = []

    for cat_id, stats in activity.items():
        meta = catalogue.get(cat_id, {})
        entry = {
            "id": cat_id,
            "label": meta.get("label") or PROGRAM_LABELS.get(cat_id, cat_id.replace("_", " ").title()),
            "rounds_last_12_months": stats["rounds"],
            "itas_last_12_months": stats["total_itas"],
            "last_drawn": stats["last_drawn"],
            "typical_cutoff": stats["typical_cutoff"],
            "cutoff_range": stats["cutoff_range"],
            "verification_status": meta.get("verification_status"),
        }
        if stats["rounds"] > 0:
            live.append(entry)
        else:
            entry["warning"] = (
                f"Listed by IRCC as a {date.today().year} category, but no round has been held in the "
                f"last {DORMANCY_WINDOW_MONTHS} months. Being eligible for a dormant category does not "
                "produce an invitation."
            )
            dormant.append(entry)

    live.sort(key=lambda c: c["itas_last_12_months"], reverse=True)
    return {"live": live, "dormant": dormant}


def _eligibility(
    crs_profile,
    canadian_months: int,
    foreign_months: int,
    canadian_by_noc: dict[str, int],
    primary_teer: int | None,
    has_nomination: bool,
) -> dict[str, dict[str, Any]]:
    """Whether the candidate qualifies for each route, independent of their score.

    A cut-off is only meaningful for a route the candidate can actually be invited
    from. Comparing a score against a category the candidate cannot enter produces a
    confident, precise, wrong answer — so eligibility is resolved first and gates
    everything downstream.
    """
    out: dict[str, dict[str, Any]] = {}
    total_months = canadian_months + foreign_months
    canadian_noc_months = canadian_by_noc or {}

    for cat in load_json("ee_categories.json").get("categories", []):
        # The draw history and the category catalogue disagree on one id
        # (`french` vs `french_proficiency`). Key eligibility by the draw id so the
        # lookup in _gap_analysis cannot silently miss and default to ineligible.
        cat_id = cat.get("draw_category_id") or cat["id"]

        if cat.get("exclude_from_job_scoring"):
            out[cat_id] = {
                "eligible": False,
                "reason": "Eligibility depends on a Canadian Armed Forces job offer, which this profile cannot confirm.",
            }
            continue

        if cat.get("all_teer_0_3"):
            has_french = crs_profile.second_language.minimum() >= cat.get("requires_french_nclc_min", 7)
            enough = total_months >= CATEGORY_MIN_MONTHS
            teer_ok = primary_teer is not None and primary_teer <= 3
            out[cat_id] = {
                "eligible": has_french and enough and teer_ok,
                "reason": (
                    "NCLC 7+ French with TEER 0-3 experience on file."
                    if (has_french and enough and teer_ok)
                    else (
                        f"Needs NCLC {cat.get('requires_french_nclc_min', 7)}+ in all four French abilities."
                        if not has_french
                        else f"Needs {CATEGORY_MIN_MONTHS} months of TEER 0-3 experience."
                    )
                ),
            }
            continue

        if cat.get("verification_status") != "verified":
            out[cat_id] = {
                "eligible": False,
                "reason": "This category's occupation list has not been verified against IRCC, so eligibility cannot be asserted.",
                "needs_verification": True,
            }
            continue

        codes = set(cat.get("noc_codes") or [])
        # Only Canadian experience is counted per-NOC today. For the "with Canadian
        # work experience" categories that is exactly right. For the others, foreign
        # experience can also count toward the threshold, so this under-reports rather
        # than over-reports — the safe direction for a paid recommendation.
        months = sum(m for noc, m in canadian_noc_months.items() if noc in codes)

        out[cat_id] = {
            "eligible": months >= CATEGORY_MIN_MONTHS,
            "reason": (
                f"{months} months of experience in an eligible occupation."
                if months >= CATEGORY_MIN_MONTHS
                else f"Needs {CATEGORY_MIN_MONTHS} months in an eligible occupation; you have {months}."
            ),
        }

    cec_ok = canadian_months >= CEC_MIN_MONTHS and primary_teer in CEC_ELIGIBLE_TEERS
    out["cec"] = {
        "eligible": cec_ok,
        "reason": (
            f"{canadian_months} months of Canadian TEER {primary_teer} experience."
            if cec_ok
            else f"Needs {CEC_MIN_MONTHS} months of Canadian TEER 0-3 experience; you have {canadian_months}."
        ),
    }

    out["pnp"] = {
        "eligible": has_nomination,
        "reason": (
            "Provincial nomination on file."
            if has_nomination
            else "PNP round cut-offs apply only to candidates who already hold a nomination."
        ),
    }

    for program in ("general", "fsw", "fst"):
        out.setdefault(program, {"eligible": False, "reason": "No round held in the reporting window."})

    return out


def _gap_analysis(
    crs_total: int,
    landscape: dict[str, Any],
    eligibility: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Distance to each live route's recent cut-off, gated by eligibility.

    Routes the candidate cannot enter are still returned, flagged ``eligible: False``,
    so the report can show why they are closed rather than hiding them.
    """
    gaps = []
    for cat in landscape["live"]:
        cutoff = cat["typical_cutoff"]
        if cutoff is None:
            continue
        elig = eligibility.get(cat["id"], {"eligible": False, "reason": "Eligibility unknown."})
        gaps.append(
            {
                "route": cat["label"],
                "id": cat["id"],
                "typical_cutoff": cutoff,
                "your_score": crs_total,
                "gap": crs_total - cutoff,
                "score_clears_cutoff": crs_total >= cutoff,
                "eligible": elig["eligible"],
                "eligibility_reason": elig["reason"],
                # Only an eligible candidate whose score clears is actually in range.
                "clears": elig["eligible"] and crs_total >= cutoff,
                "itas_last_12_months": cat["itas_last_12_months"],
                "last_drawn": cat["last_drawn"],
            }
        )
    # Eligible routes first, then by margin.
    gaps.sort(key=lambda g: (g["eligible"], g["gap"]), reverse=True)
    return gaps


def _next_moves(
    crs_result, canadian_months: int, primary_noc: str | None, profile: dict[str, Any]
) -> list[dict[str, Any]]:
    """Ranked, quantified actions. Each carries the points it is actually worth."""
    moves: list[dict[str, Any]] = []
    breakdown = crs_result.breakdown

    # Provincial nomination dwarfs everything else.
    if not profile.get("has_provincial_nomination"):
        moves.append(
            {
                "action": "Pursue a provincial nomination",
                "points": 600,
                "effort": "high",
                "detail": (
                    "A nomination adds 600 CRS points and effectively guarantees an invitation. "
                    "This is the single largest lever available and outweighs every other action combined."
                ),
            }
        )

    # Language is the cheapest large gain for most candidates.
    first_lang = breakdown.get("first_language", 0)
    if first_lang < 128:
        moves.append(
            {
                "action": "Retake your English test to reach CLB 9 in all four abilities",
                "points": 128 - first_lang,
                "effort": "medium",
                "detail": (
                    f"You currently score {first_lang} of a possible 136 on first-language points. "
                    "CLB 9 also unlocks the higher skill-transferability tiers, so the real gain is "
                    "usually larger than the language points alone."
                ),
            }
        )

    if breakdown.get("french_bonus", 0) == 0:
        moves.append(
            {
                "action": "Reach NCLC 7 in French",
                "points": 50,
                "effort": "high",
                "detail": (
                    "French draws have been the most heavily used category, with cut-offs far below "
                    "the Canadian Experience Class. This is the highest-volume route currently open."
                ),
            }
        )

    if canadian_months < 12:
        moves.append(
            {
                "action": f"Complete 12 months of Canadian TEER 0-3 work ({12 - canadian_months} to go)",
                "points": 40,
                "effort": "medium",
                "detail": (
                    "Twelve months opens the Canadian Experience Class and satisfies the 2026 "
                    "category-based experience threshold, which rose from 6 months to 12."
                ),
            }
        )
    elif canadian_months < 36:
        moves.append(
            {
                "action": "Keep accruing Canadian experience",
                "points": 24,
                "effort": "low",
                "detail": (
                    f"You have {canadian_months} months. Years two and three are worth roughly "
                    "13 and 11 more core points, plus transferability gains."
                ),
            }
        )

    if breakdown.get("canadian_study", 0) == 0:
        moves.append(
            {
                "action": "Claim points for Canadian post-secondary study, if you have it",
                "points": 30,
                "effort": "low",
                "detail": "Worth 15 points for a one- or two-year credential, 30 for three years or more.",
            }
        )

    if breakdown.get("sibling_in_canada", 0) == 0:
        moves.append(
            {
                "action": "Claim the sibling bonus, if you have a sibling who is a citizen or PR",
                "points": 15,
                "effort": "low",
                "detail": "Frequently missed. Requires a sibling aged 18+ resident in Canada.",
            }
        )

    moves.sort(key=lambda m: m["points"], reverse=True)
    return moves


def run_pathway_report(user_id: str) -> dict[str, Any]:
    try:
        check_pathway_report_allowed(user_id)
    except PlanLimitExceeded as exc:
        log_activity(
            user_id,
            "pathway_report_blocked",
            f"Pathway report blocked: {exc}",
            {"reason": "plan_limit"},
        )
        raise

    sb = get_supabase()
    profile = sb.table("profiles").select("*").eq("id", user_id).single().execute().data
    work_history = (
        sb.table("work_history").select("*").eq("user_id", user_id).order("sort_order").execute().data or []
    )

    canadian_months, foreign_months, by_noc = _split_experience(work_history)

    primary_noc = max(by_noc, key=by_noc.get) if by_noc else None
    primary_teer = teer_for_noc(primary_noc) if primary_noc else None

    crs_profile = profile_from_db(profile, canadian_months, foreign_months)
    crs_result = calculate_crs(crs_profile)

    landscape = _draw_landscape()
    eligibility = _eligibility(
        crs_profile,
        canadian_months,
        foreign_months,
        by_noc,
        primary_teer,
        bool(profile.get("has_provincial_nomination")),
    )
    gaps = _gap_analysis(crs_result.total, landscape, eligibility)
    moves = _next_moves(crs_result, canadian_months, primary_noc, profile)
    pathway_flags = evaluate_pathways(primary_noc, primary_teer, profile.get("province"))

    cec_cutoff = typical_cutoff("cec")
    headline = _headline(crs_result.total, gaps, cec_cutoff)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": DISCLAIMER,
        "headline": headline,
        "crs": crs_result.to_dict(),
        "profile_summary": {
            "status": profile.get("status"),
            "province": profile.get("province"),
            "permit_expiry": profile.get("permit_expiry"),
            "canadian_experience_months": canadian_months,
            "foreign_experience_months": foreign_months,
            "primary_noc": primary_noc,
            "primary_teer": primary_teer,
        },
        "draw_landscape": landscape,
        "eligibility": eligibility,
        "gap_analysis": gaps,
        "next_moves": moves,
        "pathway_flags": pathway_flags,
        "arranged_employment_note": (
            "IRCC removed arranged-employment CRS points on 2025-03-25. A job offer adds no points "
            "on its own; its value is the Canadian experience and category or provincial eligibility "
            "it unlocks."
        ),
        "draws_metadata": draws_metadata(),
    }

    if profile.get("status") == "pgwp" and profile.get("permit_expiry"):
        try:
            expiry = date.fromisoformat(str(profile["permit_expiry"])[:10])
            report["permit_runway_days"] = (expiry - date.today()).days
        except ValueError:
            pass

    sb.table("pathway_reports").insert({"user_id": user_id, "report_json": report}).execute()
    log_activity(
        user_id,
        "pathway_report_generated",
        f"Generated pathway report (CRS {crs_result.total}, {canadian_months} months Canadian experience)",
        {
            "crs_total": crs_result.total,
            "primary_noc": primary_noc,
            "canadian_months": canadian_months,
            "live_categories": len(landscape["live"]),
        },
    )

    return report


def _headline(crs_total: int, gaps: list[dict[str, Any]], cec_cutoff: int | None) -> dict[str, Any]:
    """One sentence stating where the candidate actually stands."""
    eligible = [g for g in gaps if g["eligible"]]

    clearing = [g for g in eligible if g["score_clears_cutoff"]]
    if clearing:
        best = max(clearing, key=lambda g: g["itas_last_12_months"])
        return {
            "crs": crs_total,
            "status": "clears",
            "text": (
                f"Your CRS is {crs_total}. That clears the recent {best['route']} cut-off of "
                f"{best['typical_cutoff']} — a route that issued {best['itas_last_12_months']:,} "
                "invitations in the last 12 months."
            ),
        }

    if eligible:
        closest = max(eligible, key=lambda g: g["gap"])
        return {
            "crs": crs_total,
            "status": "short",
            "text": (
                f"Your CRS is {crs_total}. The best route you currently qualify for is "
                f"{closest['route']} at a recent cut-off of {closest['typical_cutoff']} — "
                f"{abs(closest['gap'])} points away."
            ),
        }

    return {
        "crs": crs_total,
        "status": "no_route",
        "text": (
            f"Your CRS is {crs_total}, but you do not yet qualify for any route currently being "
            "drawn. Becoming eligible matters more than raising your score right now."
        ),
    }
