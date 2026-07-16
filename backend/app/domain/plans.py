"""Subscription plan definitions — single source of truth for tiers and limits."""

PLAN_FREE = "free"
PLAN_PRO = "pro"
PLAN_TEAM = "team"

PLANS: dict[str, dict] = {
    PLAN_FREE: {
        "plan_label": "Starter",
        "price_monthly_cad": 0,
        "limits": {"ai_pipeline_runs": 5, "jobs_per_month": 10, "resume_slots": 2},
        "features": [
            "5 AI pipeline runs per month",
            "10 job imports per month",
            "2 resume tracks",
            "Review queue",
        ],
        "upgrade_available": True,
    },
    PLAN_PRO: {
        "plan_label": "Pro",
        "price_monthly_cad": 29,
        "limits": {"ai_pipeline_runs": 50, "jobs_per_month": 100, "resume_slots": 5},
        "features": [
            "50 AI pipeline runs per month",
            "100 job imports per month",
            "5 resume tracks",
            "Interview prep",
            "Priority AI routing",
            "Email support",
        ],
        "upgrade_available": True,
    },
    PLAN_TEAM: {
        "plan_label": "Career Coach",
        "price_monthly_cad": 99,
        "limits": {"ai_pipeline_runs": 9999, "jobs_per_month": 9999, "resume_slots": 20},
        "features": [
            "Unlimited pipeline runs",
            "Multi-client workspace",
            "White-label reports",
            "API access",
        ],
        "upgrade_available": False,
    },
}


def plan_or_free(plan_tier: str | None) -> str:
    """Normalize a stored plan tier, falling back to free for unknown values."""
    return plan_tier if plan_tier in PLANS else PLAN_FREE
