"""Plan limit tests."""

from lib.plan_limits import PlanLimitExceeded, normalize_plan
from lib.plans import PLANS


def test_normalize_plan():
    assert normalize_plan("pro") == "pro"
    assert normalize_plan("invalid") == "free"
    assert normalize_plan(None) == "free"


def test_free_tailoring_limit():
    assert PLANS["free"]["limits"]["tailored_applications_per_month"] == 10


def test_pro_unlimited_tailoring():
    assert PLANS["pro"]["limits"]["tailored_applications_per_month"] is None


def test_pro_has_pathway_reports():
    assert PLANS["pro"]["limits"]["full_pathway_reports"] is True


def test_plan_limit_exception():
    exc = PlanLimitExceeded("limit hit")
    assert exc.upgrade_required is True
