"""NOC-layer scoring + wage comparison."""

from __future__ import annotations

import re
from typing import Any

from lib.data_loaders import wage_median


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9+#]+", text.lower()) if len(t) > 2}


def score_match(
    profile: dict[str, Any],
    work_history: list[dict[str, Any]],
    job: dict[str, Any],
    parsed: dict[str, Any],
) -> tuple[float, dict[str, Any]]:
    """Return (match_score 0-100, score_breakdown)."""
    noc_code = job.get("noc_code")
    user_nocs = [wh.get("mapped_noc_code") for wh in work_history if wh.get("mapped_noc_code")]
    user_teer = [wh.get("mapped_teer") for wh in work_history if wh.get("mapped_teer") is not None]

    noc_alignment = 0.0
    if noc_code and noc_code in user_nocs:
        noc_alignment = 100.0
    elif noc_code and user_nocs:
        noc_prefix = noc_code[:4]
        if any((n or "")[:4] == noc_prefix for n in user_nocs):
            noc_alignment = 70.0
        elif any((n or "")[:3] == noc_code[:3] for n in user_nocs):
            noc_alignment = 45.0
    elif user_nocs:
        noc_alignment = 20.0

    all_duties = " ".join(wh.get("duties_text") or "" for wh in work_history)
    job_skills = set(parsed.get("skills") or [])
    job_reqs = " ".join(parsed.get("requirements") or [])
    profile_tokens = _tokenize(all_duties + " " + " ".join(wh.get("title", "") for wh in work_history))
    job_tokens = _tokenize(job_reqs + " " + job.get("raw_jd", "")[:2000]) | job_skills
    overlap = profile_tokens & job_tokens
    skills_overlap = min(100.0, (len(overlap) / max(len(job_tokens), 1)) * 120) if job_tokens else 50.0

    job_teer = job.get("teer_level")
    experience_fit = 50.0
    if job_teer is not None and user_teer:
        avg_teer = sum(user_teer) / len(user_teer)
        diff = abs(avg_teer - job_teer)
        experience_fit = max(0.0, 100.0 - diff * 25)

    location_ok = 50.0
    pref = (profile.get("province") or "").upper()
    job_prov = (job.get("province") or "").upper()
    if job.get("remote") or parsed.get("remote"):
        location_ok = 90.0
    elif pref and job_prov and pref == job_prov:
        location_ok = 100.0
    elif pref and job_prov:
        location_ok = 30.0

    wage_fit = 50.0
    salary_min = profile.get("salary_min")
    wage_offered = job.get("wage_offered") or parsed.get("wage_offered")
    median = job.get("wage_median_region")
    if wage_offered and median:
        if wage_offered >= median:
            wage_fit = 85.0
        else:
            wage_fit = 40.0
    if salary_min and wage_offered:
        annual_equiv = wage_offered * 2080 if parsed.get("wage_period") == "hourly" else wage_offered
        if annual_equiv >= salary_min:
            wage_fit = max(wage_fit, 80.0)

    weights = {
        "noc_alignment": 0.35,
        "skills_overlap": 0.30,
        "experience_fit": 0.15,
        "location_ok": 0.10,
        "wage_fit": 0.10,
    }
    components = {
        "noc_alignment": round(noc_alignment, 1),
        "skills_overlap": round(skills_overlap, 1),
        "experience_fit": round(experience_fit, 1),
        "location_ok": round(location_ok, 1),
        "wage_fit": round(wage_fit, 1),
    }
    total = sum(components[k] * weights[k] for k in weights)

    gaps: list[str] = []
    if noc_alignment < 70:
        gaps.append(f"Your NOC history ({', '.join(user_nocs) or 'none mapped'}) doesn't closely match {noc_code or 'unknown'}.")
    if skills_overlap < 50:
        missing = list(job_tokens - profile_tokens)[:5]
        if missing:
            gaps.append(f"Posting emphasizes: {', '.join(missing)} — not prominent in your profile.")
    if experience_fit < 60 and job_teer is not None:
        gaps.append(f"TEER {job_teer} role — your experience averages TEER {sum(user_teer)/len(user_teer):.0f}." if user_teer else f"TEER {job_teer} role — confirm experience level fit.")
    if location_ok < 60:
        gaps.append(f"Location: {job_prov or 'unknown'} vs your target {pref or 'any'}.")
    if wage_fit < 50 and median and wage_offered:
        gaps.append(f"Offered wage may be below regional median (${median:.2f}/hr) for NOC {noc_code}.")

    breakdown = {**components, "gaps": gaps}
    return round(min(100.0, max(0.0, total)), 2), breakdown


def enrich_wage_median(job: dict[str, Any]) -> float | None:
    noc = job.get("noc_code")
    prov = job.get("province")
    if not noc or not prov:
        return None
    return wage_median(noc, prov)
