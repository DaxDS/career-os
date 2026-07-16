"""Resume + cover letter tailoring for Canadian job market."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import tempfile
from typing import Any

from config import settings
from lib.activity_log import log_activity
from lib.base_resume import build_base_resume
from lib.pdf_render import html_to_pdf, render_resume_html
from lib.plan_limits import PlanLimitExceeded, check_tailoring_allowed
from lib.resume_schema import CoverLetter, TailoredResume
from lib.supabase_client import get_supabase

CANADIAN_TAILORING_RULES = """
HARD RULES — Canadian resume norms:
- NO photo, age, marital status, SIN, or references section
- 1–2 pages maximum; reverse-chronological experience
- Canadian spelling (colour, organisation, centre)
- Never fabricate experience, skills, employers, or metrics
- Quantify ONLY with numbers already in the profile
- Ban AI-sounding words: spearheaded, leveraged, passionate, dynamic, synergy, cutting-edge
- Avoid em-dash-heavy cadence; write like a human professional
- No "References available upon request"
"""


def _load_base_resume(user_id: str, profile: dict, work_history: list) -> dict:
    sb = get_supabase()
    resume_row = (
        sb.table("resumes")
        .select("base_resume_json")
        .eq("user_id", user_id)
        .eq("is_primary", True)
        .limit(1)
        .execute()
        .data
    )
    if resume_row and resume_row[0].get("base_resume_json"):
        return resume_row[0]["base_resume_json"]
    return build_base_resume(profile, work_history).model_dump()


def _tailor_with_claude(base: dict, job: dict, profile: dict) -> TailoredResume:
    if not settings.anthropic_api_key:
        return TailoredResume.model_validate({**base, "changes_made": [{"section": "note", "reason": "No API key — base resume used"}]})

    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    parsed = job.get("parsed_requirements") or {}
    prompt = f"""Tailor this resume for the job below. Return ONLY valid JSON matching TailoredResume schema.

Job: {job.get('title')} at {job.get('company')}
Location: {job.get('city')}, {job.get('province')}
NOC: {job.get('noc_code')} TEER {job.get('teer_level')}
Requirements: {json.dumps(parsed.get('requirements', [])[:8])}
Skills sought: {json.dumps(parsed.get('skills', []))}

Base resume (source of truth):
{json.dumps(base, indent=2)[:8000]}

Candidate status in Canada: {profile.get('status')}

Include changes_made array documenting each edit."""

    message = client.messages.create(
        model=settings.claude_sonnet_model,
        max_tokens=4096,
        system=CANADIAN_TAILORING_RULES + "\nReturn JSON only.",
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text if message.content else "{}"
    start, end = raw.find("{"), raw.rfind("}") + 1
    data = json.loads(raw[start:end])
    return TailoredResume.model_validate(data)


def _cover_letter_with_claude(tailored: TailoredResume, job: dict, profile: dict) -> CoverLetter:
    if not settings.anthropic_api_key:
        text = (
            f"Dear Hiring Manager,\n\n"
            f"I am writing to express my interest in the {job.get('title')} position at {job.get('company')}. "
            f"My background aligns with the role requirements.\n\n"
            f"Sincerely,\n{profile.get('full_name') or 'Applicant'}"
        )
        return CoverLetter(full_text=text, word_count=len(text.split()))

    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    prompt = f"""Write a cover letter ≤250 words for this Canadian job application.
Reference ONE specific verifiable thing about {job.get('company')} from the job description.
{CANADIAN_TAILORING_RULES}

Job: {job.get('title')} at {job.get('company')}
JD excerpt: {(job.get('raw_jd') or '')[:2000]}
Resume summary: {tailored.summary}
Key experience: {json.dumps([e.model_dump() for e in tailored.experience[:2]])}

Return JSON: {{"full_text": "...", "word_count": N}}"""

    message = client.messages.create(
        model=settings.claude_sonnet_model,
        max_tokens=1024,
        system="Return JSON only. Max 250 words in full_text.",
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text if message.content else "{}"
    start, end = raw.find("{"), raw.rfind("}") + 1
    data = json.loads(raw[start:end])
    letter = CoverLetter.model_validate(data)
    if letter.word_count > 250:
        words = letter.full_text.split()[:250]
        letter = CoverLetter(full_text=" ".join(words), word_count=len(words))
    return letter


def run_tailoring(user_id: str, match_id: str) -> dict[str, Any]:
    try:
        check_tailoring_allowed(user_id)
    except PlanLimitExceeded as exc:
        log_activity(
            user_id,
            "tailoring_blocked",
            f"Tailoring blocked: {exc}",
            {"reason": "plan_limit", "match_id": match_id},
            entity_type="match",
            entity_id=match_id,
        )
        raise

    sb = get_supabase()
    match = (
        sb.table("matches")
        .select("*, jobs(*)")
        .eq("id", match_id)
        .eq("user_id", user_id)
        .single()
        .execute()
        .data
    )
    if not match:
        log_activity(
            user_id,
            "tailoring_failed",
            "Tailoring failed: match not found",
            {"match_id": match_id},
            entity_type="match",
            entity_id=match_id,
        )
        raise ValueError("Match not found")

    job = match["jobs"]
    job_title = job.get("title") or "Unknown role"
    log_activity(
        user_id,
        "tailoring_started",
        f"Tailoring resume for {job_title}",
        {"match_id": match_id, "job_title": job_title, "company": job.get("company")},
        entity_type="match",
        entity_id=match_id,
    )

    profile = sb.table("profiles").select("*").eq("id", user_id).single().execute().data
    work_history = (
        sb.table("work_history").select("*").eq("user_id", user_id).order("sort_order").execute().data or []
    )

    base = _load_base_resume(user_id, profile, work_history)
    tailored = _tailor_with_claude(base, job, profile)
    cover = _cover_letter_with_claude(tailored, job, profile)

    html = render_resume_html(tailored)
    pdf_path_storage = f"{user_id}/applications/{match_id}.pdf"

    pdf_generated = False
    with tempfile.TemporaryDirectory() as tmpdir:
        local_pdf = Path(tmpdir) / "resume.pdf"
        pdf_generated = html_to_pdf(html, local_pdf)
        if pdf_generated:
            sb.storage.from_("resumes").upload(
                pdf_path_storage,
                local_pdf.read_bytes(),
                file_options={"content-type": "application/pdf", "upsert": "true"},
            )

    existing = (
        sb.table("applications").select("id").eq("match_id", match_id).eq("user_id", user_id).execute().data
    )
    app_row = {
        "match_id": match_id,
        "user_id": user_id,
        "tailored_resume_json": {
            **tailored.model_dump(),
            "_base_resume": base,
            "_rendered_html": html[:50000],
        },
        "tailored_resume_pdf_path": pdf_path_storage if pdf_generated else None,
        "cover_letter_text": cover.full_text,
        "submission_method": job.get("url"),
        "status": "pending_review",
    }
    if existing:
        app_id = existing[0]["id"]
        sb.table("applications").update(app_row).eq("id", app_id).execute()
    else:
        inserted = sb.table("applications").insert(app_row).execute().data
        app_id = inserted[0]["id"]

    sb.table("matches").update({"status": "queued"}).eq("id", match_id).execute()
    log_activity(
        user_id,
        "tailoring_completed",
        f"Tailored resume for {job_title} — ready for your review",
        {
            "match_id": match_id,
            "application_id": app_id,
            "job_title": job_title,
            "pdf": pdf_generated,
        },
        entity_type="application",
        entity_id=app_id,
    )

    return {"application_id": app_id, "pdf_generated": pdf_generated, "status": "pending_review"}
