"""Work-authorization hard filters vs user permit status."""

from __future__ import annotations

from typing import Any


def is_eligible(
    profile: dict[str, Any],
    parsed: dict[str, Any],
    job: dict[str, Any],
) -> tuple[bool, str | None]:
    """Return (eligible, rejection_reason)."""
    status = profile.get("status", "outside_canada")
    work_auth = parsed.get("work_auth_required") or job.get("work_auth_required")
    lmia = parsed.get("lmia_flag") or job.get("lmia_flag")
    clearance = parsed.get("clearance_required") or job.get("clearance_required") or "none"

    if work_auth == "citizenship_required" and status not in ("citizen",):
        return False, "Citizenship required"

    if clearance in ("reliability", "secret") and status in ("outside_canada",):
        return False, f"Security clearance required ({clearance})"

    if lmia and status in ("pgwp", "closed_permit", "outside_canada"):
        return False, "LMIA-supported role — may not suit open permit/PGWP holders"

    if status == "outside_canada" and work_auth == "eligible_to_work_in_canada":
        return False, "Must be eligible to work in Canada"

    if status == "pgwp":
        permit_expiry = profile.get("permit_expiry")
        if permit_expiry:
            from datetime import date

            try:
                expiry = date.fromisoformat(str(permit_expiry)[:10])
                if expiry < date.today():
                    return False, "Work permit expired"
            except ValueError:
                pass

    preferred_province = (profile.get("province") or "").upper()
    remote_pref = profile.get("remote_pref", "any")
    job_province = (job.get("province") or "").upper()
    job_remote = job.get("remote") or parsed.get("remote")

    if remote_pref == "remote" and not job_remote:
        return False, "Onsite role — you prefer remote"
    if remote_pref == "onsite" and job_remote:
        return False, "Remote role — you prefer onsite"

    if preferred_province and job_province and preferred_province != job_province and not job_remote:
        if remote_pref not in ("any", "hybrid"):
            return False, f"Location mismatch ({job_province} vs your {preferred_province})"

    return True, None
