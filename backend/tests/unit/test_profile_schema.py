"""Verify UserProfile schema supports all future-layer requirements."""

from app.domain.enums import JobCategory, RemotePreference, WorkAuthorization
from app.infrastructure.db.models import UserProfile


REQUIRED_PROFILE_COLUMNS = {
    "work_authorization",
    "immigration_goals",
    "preferred_provinces",
    "preferred_job_categories",
    "skills",
    "salary_min_cad",
    "salary_max_cad",
    "remote_preference",
    "languages",
}


def test_user_profile_has_required_columns():
    columns = {c.name for c in UserProfile.__table__.columns}
    missing = REQUIRED_PROFILE_COLUMNS - columns
    assert not missing, f"Missing profile columns: {missing}"


def test_job_category_enum_covers_resume_types():
    values = {c.value for c in JobCategory}
    assert values == {"production", "construction", "it", "ai", "general"}


def test_work_authorization_enum():
    assert WorkAuthorization.PGWP.value == "pgwp"


def test_remote_preference_enum():
    assert RemotePreference.HYBRID.value == "hybrid"
