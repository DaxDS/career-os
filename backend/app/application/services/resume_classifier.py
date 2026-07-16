from app.domain.enums import LABEL_TO_CATEGORY, JobCategory, ResumeLabel


class ResumeClassifier:
    """Rule-based resume classification — AI enhancement deferred to Layer 4+."""

    def classify(self, label: str, parsed_content: dict) -> dict:
        category = LABEL_TO_CATEGORY.get(label, JobCategory.GENERAL)
        skills = parsed_content.get("skills", [])
        experience = parsed_content.get("experience", [])

        return {
            "label": label,
            "role_family": category.value,
            "role_families": [category.value],
            "detected_skills": skills[:30],
            "experience_count": len(experience),
            "has_summary": bool(parsed_content.get("summary")),
            "classification_method": "rule_based",
            "confidence": 1.0 if label in {e.value for e in ResumeLabel} else 0.7,
        }

    @staticmethod
    def validate_label(label: str) -> str:
        valid = {e.value for e in ResumeLabel}
        if label not in valid:
            raise ValueError(f"Invalid label. Must be one of: {sorted(valid)}")
        return label
