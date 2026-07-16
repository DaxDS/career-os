"""Plan limit enforcement."""

from __future__ import annotations

from datetime import datetime, timezone

from lib.plans import PLANS, normalize_plan
from lib.supabase_client import get_supabase


class PlanLimitExceeded(Exception):
    def __init__(self, message: str, upgrade_required: bool = True):
        super().__init__(message)
        self.upgrade_required = upgrade_required


def _month_start_iso() -> str:
    now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, 1, tzinfo=timezone.utc).isoformat()


def get_user_plan(user_id: str) -> str:
    sb = get_supabase()
    row = sb.table("profiles").select("plan").eq("id", user_id).single().execute().data
    return normalize_plan(row.get("plan") if row else None)


def tailored_apps_this_month(user_id: str) -> int:
    sb = get_supabase()
    rows = (
        sb.table("applications")
        .select("id, created_at")
        .eq("user_id", user_id)
        .gte("created_at", _month_start_iso())
        .execute()
        .data
        or []
    )
    return len(rows)


def check_tailoring_allowed(user_id: str) -> None:
    plan = get_user_plan(user_id)
    limit = PLANS[plan]["limits"]["tailored_applications_per_month"]
    if limit is None:
        return
    used = tailored_apps_this_month(user_id)
    if used >= limit:
        raise PlanLimitExceeded(
            f"Monthly limit reached ({used}/{limit} tailored applications). "
            "Upgrade to Pro for unlimited tailoring."
        )


def check_pathway_report_allowed(user_id: str) -> None:
    plan = get_user_plan(user_id)
    if not PLANS[plan]["limits"]["full_pathway_reports"]:
        raise PlanLimitExceeded(
            "Full pathway reports are a Pro feature. Upgrade to unlock situational analysis.",
            upgrade_required=True,
        )
