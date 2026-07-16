"""Posting → NOC 2021 + TEER with ground-truth validation."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

from config import settings
from lib.data_loaders import teer_for_noc

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class NOCClassification(BaseModel):
    noc_code: str
    teer_level: int = Field(ge=0, le=5)
    confidence: float = Field(ge=0, le=1)
    rationale: str = ""


@lru_cache
def load_noc_hierarchy() -> dict:
    with open(DATA_DIR / "noc_2021.json", encoding="utf-8") as f:
        return json.load(f)


def valid_noc_codes() -> set[str]:
    data = load_noc_hierarchy()
    return {ug["code"] for ug in data["unit_groups"]}


def validate_noc_code(code: str) -> bool:
    return code in valid_noc_codes()


def _noc_catalog_snippet(max_items: int = 40) -> str:
    data = load_noc_hierarchy()
    lines = []
    for ug in data["unit_groups"][:max_items]:
        lines.append(f"{ug['code']}: {ug['title']} (TEER {ug['teer']})")
    return "\n".join(lines)


def _best_guess_rule_based(title: str, description: str) -> NOCClassification:
    text = f"{title} {description}".lower()
    data = load_noc_hierarchy()
    best: NOCClassification | None = None
    for ug in data["unit_groups"]:
        title_l = ug["title"].lower()
        score = 0.0
        if title_l in text or text in title_l:
            score += 0.5
        for example in ug.get("example_titles", []):
            if example.lower() in text:
                score += 0.3
        if any(w in text for w in title_l.split()[:2]):
            score += 0.1
        if score > 0 and (best is None or score > best.confidence):
            best = NOCClassification(
                noc_code=ug["code"],
                teer_level=int(ug["teer"]),
                confidence=min(score, 0.65),
                rationale=f"Keyword match to {ug['title']}",
            )
    if best:
        return best
    fallback = data["unit_groups"][0]
    return NOCClassification(
        noc_code=fallback["code"],
        teer_level=int(fallback["teer"]),
        confidence=0.3,
        rationale="Low-confidence fallback — confirm manually",
    )


def classify_posting(title: str, description: str, suggested_noc: str | None = None) -> NOCClassification:
    if suggested_noc and validate_noc_code(suggested_noc):
        teer = teer_for_noc(suggested_noc)
        return NOCClassification(
            noc_code=suggested_noc,
            teer_level=teer if teer is not None else 2,
            confidence=0.95,
            rationale="Pre-tagged by Job Bank",
        )

    if not settings.anthropic_api_key:
        return _best_guess_rule_based(title, description)

    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    catalog = _noc_catalog_snippet()
    valid_codes = sorted(valid_noc_codes())
    prompt = f"""Classify this job to exactly ONE NOC 2021 unit-group code from the allowed list.

Title: {title}
Duties: {description[:4000]}

Reference unit groups (you MUST pick a code from the allowed list only):
{catalog}

Allowed codes: {", ".join(valid_codes)}

Return JSON: {{"noc_code": "#####", "teer_level": 0-5, "confidence": 0.0-1.0, "rationale": "..."}}"""

    for attempt in range(2):
        message = client.messages.create(
            model=settings.claude_haiku_model,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
            system="Return ONLY valid JSON. noc_code MUST be from the allowed list.",
        )
        raw = message.content[0].text if message.content else "{}"
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            result = NOCClassification.model_validate(json.loads(raw[start:end]))
            if validate_noc_code(result.noc_code):
                if result.teer_level != teer_for_noc(result.noc_code):
                    teer = teer_for_noc(result.noc_code)
                    if teer is not None:
                        result.teer_level = teer
                return result
        except (json.JSONDecodeError, ValueError):
            pass

    return _best_guess_rule_based(title, description)
