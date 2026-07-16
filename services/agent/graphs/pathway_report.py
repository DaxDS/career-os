"""Full immigration pathway situational report."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from graphs.pathways import evaluate_pathways
from lib.activity_log import log_activity
from lib.data_loaders import load_json, teer_for_noc
from lib.plan_limits import PlanLimitExceeded, check_pathway_report_allowed
from lib.supabase_client import get_supabase

DISCLAIMER = (
    "This is informational only, based on published program criteria, and is not immigration advice. "
    "Consult a licensed RCIC or immigration lawyer for decisions."
)


def _months_between(start: str | None, end: str | None, is_current: bool) -> int:
    if not start:
        return 0
    try:
        s = date.fromisoformat(str(start)[:10])
        e = date.today() if is_current or not end else date.fromisoformat(str(end)[:10])
        return max(0, (e.year - s.year) * 12 + (e.month - s.month))
    except ValueError:
        return 0


def _canadian_experience_months(work_history: list[dict]) -> tuple[int, dict[str, int]]:
    by_noc: dict[str, int] = {}
    total = 0
    for wh in work_history:
        if (wh.get("country") or "CA").upper() not in ("CA", "CANADA"):
            continue
        months = wh.get("months_canadian_experience") or _months_between(
            wh.get("start_date"), wh.get("end_date"), wh.get("is_current", False)
        )
        total += months
        noc = wh.get("mapped_noc_code")
        if noc:
            by_noc[noc] = by_noc.get(noc, 0) + months
    return total, by_noc


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

    total_months, by_noc = _canadian_experience_months(work_history)
    teer_data = load_json("teer_rules.json")
    ee_eligible_teers = set(teer_data.get("ee_teer_eligible_range", [0, 1, 2, 3]))

    primary_noc = None
    primary_teer = None
    if by_noc:
        primary_noc = max(by_noc, key=by_noc.get)
        primary_teer = teer_for_noc(primary_noc)

    pathway_flags = evaluate_pathways(primary_noc, primary_teer, profile.get("province"))

    recommendations: list[str] = []
    if profile.get("status") == "pgwp" and profile.get("permit_expiry"):
        try:
            expiry = date.fromisoformat(str(profile["permit_expiry"])[:10])
            days_left = (expiry - date.today()).days
            recommendations.append(f"PGWP expires in {days_left} days ({expiry.isoformat()}).")
        except ValueError:
            pass

    if primary_noc and by_noc.get(primary_noc, 0) < 12:
        needed = 12 - by_noc.get(primary_noc, 0)
        recommendations.append(
            f"{needed} more months in NOC {primary_noc} → closer to Canadian Experience Class threshold (typically 12 months TEER 0–3)."
        )
    elif total_months >= 12 and primary_teer in ee_eligible_teers:
        recommendations.append("You may have sufficient Canadian TEER 0–3 experience for CEC — verify current IRCC requirements.")

    if profile.get("language_fr") in ("advanced", "native") and pathway_flags.get("ee_categories"):
        if "french_proficiency" not in pathway_flags["ee_categories"]:
            recommendations.append("Strong French proficiency may qualify you for Express Entry French-category draws.")

    matched_streams = pathway_flags.get("pnp_streams", [])
    if matched_streams:
        recommendations.append(f"Profile NOC may align with: {', '.join(matched_streams[:3])}.")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": DISCLAIMER,
        "profile_summary": {
            "status": profile.get("status"),
            "province": profile.get("province"),
            "permit_expiry": profile.get("permit_expiry"),
            "language_en": profile.get("language_en"),
            "language_fr": profile.get("language_fr"),
        },
        "canadian_experience": {
            "total_months": total_months,
            "by_noc": by_noc,
            "primary_noc": primary_noc,
            "primary_teer": primary_teer,
        },
        "pathway_flags": pathway_flags,
        "ee_teer_eligible": primary_teer in ee_eligible_teers if primary_teer is not None else False,
        "recommendations": recommendations,
    }

    sb.table("pathway_reports").insert({"user_id": user_id, "report_json": report}).execute()
    noc_label = primary_noc or "none mapped"
    log_activity(
        user_id,
        "pathway_report_generated",
        f"Generated pathway report (primary NOC {noc_label}, {total_months} months Canadian experience)",
        {
            "primary_noc": primary_noc,
            "primary_teer": primary_teer,
            "total_months": total_months,
            "ee_teer_eligible": report["ee_teer_eligible"],
        },
    )

    return report
