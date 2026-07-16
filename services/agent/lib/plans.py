"""Subscription plan limits — mirrors packages/shared/src/plans.ts."""

from __future__ import annotations

PLANS = {
    "free": {
        "label": "Free",
        "price_monthly_cad": 0,
        "daily_send_cap": 5,
        "limits": {
            "tailored_applications_per_month": 10,
            "full_pathway_reports": False,
        },
    },
    "pro": {
        "label": "Pro",
        "price_monthly_cad": 24,
        "daily_send_cap": 25,
        "limits": {
            "tailored_applications_per_month": None,  # unlimited
            "full_pathway_reports": True,
        },
    },
}


def normalize_plan(tier: str | None) -> str:
    return tier if tier in PLANS else "free"
