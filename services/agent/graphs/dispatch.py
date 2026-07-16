"""Post-approval dispatch — daily cap, assisted apply, activity log."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from lib.activity_log import log_activity
from lib.supabase_client import get_supabase


def _sent_today_count(user_id: str) -> int:
    sb = get_supabase()
    today = datetime.now(timezone.utc).date().isoformat()
    rows = (
        sb.table("applications")
        .select("id, sent_at")
        .eq("user_id", user_id)
        .eq("status", "sent")
        .execute()
        .data
        or []
    )
    return sum(1 for r in rows if r.get("sent_at") and str(r["sent_at"]).startswith(today))


def run_dispatch(user_id: str, application_id: str) -> dict[str, Any]:
    sb = get_supabase()
    profile = sb.table("profiles").select("daily_send_cap").eq("id", user_id).single().execute().data
    cap = int(profile.get("daily_send_cap") or 10)
    sent_today = _sent_today_count(user_id)

    if sent_today >= cap:
        log_activity(
            user_id,
            "dispatch_blocked",
            f"Dispatch blocked: daily cap reached ({sent_today}/{cap})",
            {"cap": cap, "sent_today": sent_today, "application_id": application_id},
            entity_type="application",
            entity_id=application_id,
        )
        raise ValueError(f"Daily send cap ({cap}) reached. Try again tomorrow.")

    app = (
        sb.table("applications")
        .select("*, matches(job_id, jobs(url, title, company))")
        .eq("id", application_id)
        .eq("user_id", user_id)
        .single()
        .execute()
        .data
    )
    if not app:
        log_activity(
            user_id,
            "dispatch_failed",
            "Dispatch failed: application not found",
            {"application_id": application_id},
            entity_type="application",
            entity_id=application_id,
        )
        raise ValueError("Application not found")

    job = app["matches"]["jobs"]
    job_title = job.get("title") or "Unknown role"

    if app["status"] not in ("approved", "pending_review"):
        if app["status"] == "sent":
            log_activity(
                user_id,
                "dispatch_blocked",
                f"Dispatch blocked: application for {job_title} was already sent",
                {"application_id": application_id, "status": app["status"]},
                entity_type="application",
                entity_id=application_id,
            )
            raise ValueError("Application already sent")
        log_activity(
            user_id,
            "dispatch_blocked",
            f"Dispatch blocked: application for {job_title} is in status '{app['status']}'",
            {"application_id": application_id, "status": app["status"]},
            entity_type="application",
            entity_id=application_id,
        )
        raise ValueError(f"Cannot dispatch application in status: {app['status']}")

    if app["status"] == "pending_review":
        log_activity(
            user_id,
            "dispatch_blocked",
            f"Dispatch blocked: {job_title} is still awaiting your approval in the review queue",
            {"application_id": application_id},
            entity_type="application",
            entity_id=application_id,
        )
        raise ValueError("Approve the application in the review queue before sending")

    apply_url = job.get("url") or app.get("submission_method")
    now = datetime.now(timezone.utc).isoformat()

    sb.table("applications").update({"status": "sent", "sent_at": now}).eq("id", application_id).execute()
    match_id = app["match_id"]
    sb.table("matches").update({"status": "approved"}).eq("id", match_id).execute()

    log_activity(
        user_id,
        "application_dispatched",
        f"Application marked sent for {job_title} — open the apply URL to submit yourself",
        {"apply_url": apply_url, "method": "assisted_apply", "job_title": job_title},
        entity_type="application",
        entity_id=application_id,
    )

    return {
        "application_id": application_id,
        "status": "sent",
        "apply_url": apply_url,
        "message": "Materials ready — open the apply URL to submit yourself.",
    }
