"""Build base resume from profile + work history."""

from __future__ import annotations

from typing import Any

from lib.resume_schema import ResumeDocument, ResumeExperience


def build_base_resume(profile: dict[str, Any], work_history: list[dict[str, Any]]) -> ResumeDocument:
    experience: list[ResumeExperience] = []
    for wh in work_history:
        start = wh.get("start_date") or ""
        end = "Present" if wh.get("is_current") else (wh.get("end_date") or "")
        dates = f"{start} – {end}".strip(" –")
        location_parts = [wh.get("city"), wh.get("province"), wh.get("country")]
        location = ", ".join(p for p in location_parts if p)
        bullets = []
        if wh.get("duties_text"):
            for line in wh["duties_text"].split("\n"):
                line = line.strip(" •-\t")
                if line:
                    bullets.append(line[:300])
        if not bullets:
            bullets = [f"{wh.get('title', 'Role')} at {wh.get('employer', 'employer')}."]
        experience.append(
            ResumeExperience(
                title=wh.get("title") or "",
                employer=wh.get("employer") or "",
                dates=dates,
                location=location,
                bullets=bullets[:6],
            )
        )

    skills: list[str] = []
    for wh in work_history:
        if wh.get("mapped_noc_code"):
            skills.append(f"NOC {wh['mapped_noc_code']}")

    return ResumeDocument(
        full_name=profile.get("full_name") or "",
        contact={
            "city": profile.get("city") or "",
            "province": profile.get("province") or "",
        },
        summary="",
        experience=experience,
        skills=skills,
    )
