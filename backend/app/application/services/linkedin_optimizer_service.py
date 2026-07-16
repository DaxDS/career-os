"""LinkedIn profile optimizer — free acquisition feature, manual paste only (no scraping)."""

import json
import re

from app.application.ports.llm import LLMMessage, ModelRouterPort
from app.domain.enums import AICapability


class LinkedInOptimizerService:
    def __init__(self, router: ModelRouterPort):
        self._router = router

    def optimize(self, headline: str, about: str, target_role_family: str) -> dict:
        prompt = f"""You are a LinkedIn profile optimizer for job seekers targeting {target_role_family} roles in Canada.

Current headline:
{headline or "(empty)"}

Current About section:
{about or "(empty)"}

Analyze keyword density against what recruiters and LinkedIn search rank for {target_role_family} roles, then suggest specific rewrites. Keep the candidate's real experience — never invent qualifications.

Respond with JSON only:
{{
  "keyword_score": <0-100 integer, how well the current text matches {target_role_family} recruiter searches>,
  "missing_keywords": ["keywords recruiters search for that are absent", ...],
  "headline_rewrite": "improved headline, max 220 chars",
  "about_rewrite": "improved About section preserving the candidate's actual experience",
  "suggestions": [
    {{"section": "headline|about", "issue": "what is weak", "fix": "specific change to make"}}
  ]
}}"""

        response = self._router.complete_for_capability(
            AICapability.LINKEDIN_OPTIMIZATION,
            [LLMMessage(role="user", content=prompt)],
        )
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        data = json.loads(raw)
        return {
            "keyword_score": max(0, min(100, int(data.get("keyword_score") or 0))),
            "missing_keywords": [str(k) for k in data.get("missing_keywords") or []][:15],
            "headline_rewrite": str(data.get("headline_rewrite") or ""),
            "about_rewrite": str(data.get("about_rewrite") or ""),
            "suggestions": [
                {
                    "section": str(s.get("section") or ""),
                    "issue": str(s.get("issue") or ""),
                    "fix": str(s.get("fix") or ""),
                }
                for s in data.get("suggestions") or []
                if isinstance(s, dict)
            ][:10],
        }
