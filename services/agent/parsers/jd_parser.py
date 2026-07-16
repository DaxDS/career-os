"""JD → structured requirements + work-auth/clearance flags."""

from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, Field

from config import settings

ClearanceLevel = Literal["none", "reliability", "secret"]


class ParsedJD(BaseModel):
    requirements: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    experience_years_min: float | None = None
    bilingual_required: bool = False
    french_required: bool = False
    work_auth_required: str | None = None
    lmia_flag: bool = False
    clearance_required: ClearanceLevel = "none"
    wage_offered: float | None = None
    wage_period: Literal["hourly", "annual", "unknown"] | None = None
    remote: bool = False


def _rule_based_parse(title: str, description: str) -> ParsedJD:
    text = f"{title}\n{description}".lower()
    bilingual = any(
        p in text
        for p in (
            "bilingual",
            "english and french",
            "french and english",
            "français et anglais",
        )
    )
    french_required = any(p in text for p in ("french required", "français requis", "must be fluent in french"))
    lmia = any(p in text for p in ("lmia", "labour market impact assessment"))
    clearance: ClearanceLevel = "none"
    if "secret clearance" in text or "top secret" in text:
        clearance = "secret"
    elif "reliability status" in text or "reliability clearance" in text or "security clearance" in text:
        clearance = "reliability"

    work_auth = None
    if any(p in text for p in ("eligible to work in canada", " legally entitled to work", "must be legally able to work")):
        work_auth = "eligible_to_work_in_canada"
    if "canadian citizen" in text or "citizenship required" in text:
        work_auth = "citizenship_required"

    remote = any(p in text for p in ("remote", "work from home", "telework", "hybrid"))

    wage_offered = None
    wage_period: Literal["hourly", "annual", "unknown"] | None = None
    hourly = re.search(r"\$\s*(\d+(?:\.\d+)?)\s*(?:/|\s+per\s+)hr", text)
    annual = re.search(r"\$\s*(\d{2,3}(?:,\d{3})*)\s*(?:/|\s+per\s+)(?:year|annum|annually)", text)
    if hourly:
        wage_offered = float(hourly.group(1).replace(",", ""))
        wage_period = "hourly"
    elif annual:
        wage_offered = float(annual.group(1).replace(",", ""))
        wage_period = "annual"

    skills: list[str] = []
    for token in ("python", "sql", "aws", "azure", "kubernetes", "react", "java", "excel"):
        if token in text:
            skills.append(token)

    requirements: list[str] = []
    for line in description.split("\n"):
        stripped = line.strip(" •-\t")
        if stripped and len(stripped) > 10:
            requirements.append(stripped[:200])
        if len(requirements) >= 8:
            break

    exp_match = re.search(r"(\d+)\+?\s*years?\s*(?:of\s+)?experience", text)
    experience_years_min = float(exp_match.group(1)) if exp_match else None

    return ParsedJD(
        requirements=requirements,
        skills=skills,
        experience_years_min=experience_years_min,
        bilingual_required=bilingual,
        french_required=french_required,
        work_auth_required=work_auth,
        lmia_flag=lmia,
        clearance_required=clearance,
        wage_offered=wage_offered,
        wage_period=wage_period,
        remote=remote,
    )


def parse_jd(title: str, description: str, company: str = "") -> ParsedJD:
    """Claude with JSON schema when API key present; rule-based fallback otherwise."""
    if not settings.anthropic_api_key:
        return _rule_based_parse(title, description)

    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    schema = ParsedJD.model_json_schema()
    prompt = f"""Parse this Canadian job posting into structured JSON matching the schema exactly.

Company: {company}
Title: {title}

Description:
{description[:6000]}

Rules:
- bilingual_required: true if posting mentions bilingual EN/FR
- lmia_flag: true only if LMIA explicitly mentioned
- clearance_required: none | reliability | secret
- work_auth_required: null, eligible_to_work_in_canada, or citizenship_required
- Extract wage_offered as numeric CAD if stated
- Do not invent requirements not in the text"""

    for attempt in range(2):
        message = client.messages.create(
            model=settings.claude_sonnet_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
            system=f"Return ONLY valid JSON matching this schema: {json.dumps(schema)}",
        )
        raw = message.content[0].text if message.content else "{}"
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            data = json.loads(raw[start:end])
            return ParsedJD.model_validate(data)
        except (json.JSONDecodeError, ValueError):
            if attempt == 1:
                return _rule_based_parse(title, description)
            prompt += "\n\nYour previous response was invalid JSON. Return ONLY valid JSON."

    return _rule_based_parse(title, description)
