import json

from app.infrastructure.db.models import JobPosting, MasterResume, UserProfile


def format_location(job: JobPosting) -> str:
    parts = [p for p in (job.location_city, job.location_province) if p]
    return ", ".join(parts)


def format_profile(profile: UserProfile) -> str:
    return json.dumps(
        {
            "legal_name": profile.legal_name,
            "location_city": profile.location_city,
            "location_province": profile.location_province,
            "work_authorization": profile.work_authorization,
            "preferred_provinces": profile.preferred_provinces,
            "preferred_job_categories": profile.preferred_job_categories,
            "skills": profile.skills,
            "salary_min_cad": profile.salary_min_cad,
            "salary_max_cad": profile.salary_max_cad,
            "remote_preference": profile.remote_preference,
            "immigration_goals": profile.immigration_goals,
        },
        indent=2,
    )


def format_master_resumes(resumes: list[MasterResume]) -> str:
    payload = []
    for resume in resumes:
        parsed = resume.parsed_content or {}
        payload.append(
            {
                "id": str(resume.id),
                "label": resume.label,
                "category": resume.category,
                "role_families": resume.role_families,
                "skills": parsed.get("skills", [])[:20],
                "summary": (parsed.get("summary") or "")[:300],
                "experience_count": len(parsed.get("experience", [])),
            }
        )
    return json.dumps(payload, indent=2)


def pick_resume_for_ats(resumes: list[MasterResume], role_family: str | None) -> MasterResume | None:
    if not resumes:
        return None
    if role_family:
        for resume in resumes:
            if resume.category == role_family or role_family in (resume.role_families or []):
                return resume
    return resumes[0]


def resume_text_for_ats(resume: MasterResume) -> str:
    parsed = resume.parsed_content or {}
    parts = [
        f"Label: {resume.label}",
        f"Category: {resume.category}",
        parsed.get("summary", ""),
        "Skills: " + ", ".join(parsed.get("skills", [])[:30]),
    ]
    for exp in parsed.get("experience", [])[:5]:
        if isinstance(exp, dict):
            parts.append(exp.get("text", str(exp)))
        else:
            parts.append(str(exp))
    return "\n".join(p for p in parts if p)


def format_master_resume_full(resume: MasterResume) -> str:
    parsed = resume.parsed_content or {}
    if parsed:
        return json.dumps(parsed, indent=2)
    return resume_text_for_ats(resume)


def format_tailored_resume_text(tailored: dict) -> str:
    parts: list[str] = []
    if summary := tailored.get("summary"):
        parts.append(f"Summary: {summary}")
    for exp in tailored.get("experience", []):
        if not isinstance(exp, dict):
            parts.append(str(exp))
            continue
        header = " — ".join(
            p for p in (exp.get("title"), exp.get("employer"), exp.get("dates")) if p
        )
        if header:
            parts.append(header)
        for bullet in exp.get("bullets", []):
            parts.append(f"  • {bullet}")
    if skills := tailored.get("skills"):
        parts.append("Skills: " + ", ".join(skills))
    for edu in tailored.get("education", []):
        if isinstance(edu, dict):
            parts.append(
                "Education: "
                + " — ".join(p for p in (edu.get("degree"), edu.get("institution")) if p)
            )
    return "\n".join(parts)


def tailored_resume_summary(tailored: dict) -> str:
    return (tailored.get("summary") or "")[:500]


def tailored_resume_highlights(tailored: dict) -> str:
    highlights: list[str] = []
    for exp in tailored.get("experience", [])[:3]:
        if isinstance(exp, dict):
            for bullet in exp.get("bullets", [])[:2]:
                highlights.append(str(bullet))
    if skills := tailored.get("skills", [])[:10]:
        highlights.append("Skills: " + ", ".join(skills))
    return "\n".join(highlights)


def key_qualifications_from_tailored(tailored: dict) -> str:
    quals: list[str] = list(tailored.get("skills", [])[:15])
    for exp in tailored.get("experience", [])[:2]:
        if isinstance(exp, dict):
            for bullet in exp.get("bullets", [])[:2]:
                quals.append(str(bullet))
    return json.dumps(quals, indent=2)
