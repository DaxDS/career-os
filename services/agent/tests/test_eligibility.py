"""Eligibility filter tests."""

from parsers.eligibility import is_eligible


def test_citizenship_required_blocks_pgwp():
    profile = {"status": "pgwp", "province": "ON", "remote_pref": "any"}
    parsed = {"work_auth_required": "citizenship_required", "lmia_flag": False, "clearance_required": "none"}
    job = {"province": "ON", "remote": False}
    ok, reason = is_eligible(profile, parsed, job)
    assert ok is False
    assert "Citizenship" in (reason or "")


def test_pgwp_passes_standard_posting():
    profile = {"status": "pgwp", "province": "ON", "remote_pref": "any", "permit_expiry": "2027-01-01"}
    parsed = {"work_auth_required": "eligible_to_work_in_canada", "lmia_flag": False, "clearance_required": "none", "remote": False}
    job = {"province": "ON", "remote": False}
    ok, _ = is_eligible(profile, parsed, job)
    assert ok is True
