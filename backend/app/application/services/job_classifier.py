import re

from app.domain.enums import JobCategory


class RuleBasedJobClassifier:
    """Rule-based job classification — used as fallback when AI is unavailable."""

    _KEYWORDS: dict[JobCategory, tuple[str, ...]] = {
        JobCategory.AI: (
            "machine learning",
            "deep learning",
            "artificial intelligence",
            "llm",
            "nlp",
            "computer vision",
            "data scientist",
            "ml engineer",
        ),
        JobCategory.IT: (
            "software",
            "developer",
            "devops",
            "cloud",
            "network",
            "cybersecurity",
            "database",
            "full stack",
            "backend",
            "frontend",
        ),
        JobCategory.PRODUCTION: (
            "manufacturing",
            "production operator",
            "assembly",
            "cnc",
            "welding",
            "quality control",
            "plant",
            "industrial",
            "plc",
        ),
        JobCategory.CONSTRUCTION: (
            "construction",
            "carpenter",
            "electrician",
            "plumber",
            "foreman",
            "site supervisor",
            "hvac",
            "trades",
        ),
    }

    def classify(
        self,
        title: str,
        description: str,
        remote_type: str | None = None,
        *,
        company: str = "",
        location: str = "",
    ) -> dict:
        text = f"{title}\n{description}".lower()
        scores: dict[str, int] = {cat.value: 0 for cat in JobCategory}

        for category, keywords in self._KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    scores[category.value] += 1

        best = max(scores, key=scores.get)
        role_family = best if scores[best] > 0 else JobCategory.GENERAL.value

        return {
            "role_family": role_family,
            "seniority": self._detect_seniority(title),
            "employment_type": self._detect_employment_type(text),
            "remote_type": remote_type or self._detect_remote_type(text),
            "classification_method": "rule_based",
            "classification_confidence": min(1.0, 0.5 + scores.get(role_family, 0) * 0.15),
        }

    @staticmethod
    def _detect_seniority(title: str) -> str:
        title_lower = title.lower()
        if re.search(r"\b(senior|sr\.?|lead|principal|staff)\b", title_lower):
            return "senior"
        if re.search(r"\b(junior|jr\.?|entry|graduate)\b", title_lower):
            return "entry"
        if re.search(r"\b(manager|director|head of)\b", title_lower):
            return "lead"
        return "mid"

    @staticmethod
    def _detect_employment_type(text: str) -> str:
        if "contract" in text:
            return "contract"
        if "part-time" in text or "part time" in text:
            return "part_time"
        if "intern" in text:
            return "internship"
        return "full_time"

    @staticmethod
    def _detect_remote_type(text: str) -> str:
        if "remote" in text and "hybrid" not in text:
            return "remote"
        if "hybrid" in text:
            return "hybrid"
        if "on-site" in text or "onsite" in text or "in office" in text:
            return "onsite"
        return "onsite"


JobClassifier = RuleBasedJobClassifier
