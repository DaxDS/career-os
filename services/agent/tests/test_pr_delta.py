from graphs.pr_delta import JobContext, evaluate_job
from lib.crs import CrsProfile, LanguageScores


def _clb(level: int) -> LanguageScores:
    return LanguageScores(reading=level, writing=level, listening=level, speaking=level)


def _candidate(**overrides) -> CrsProfile:
    base = dict(
        age=29,
        education="masters_or_professional",
        first_language=_clb(9),
        canadian_experience_years=0,
        foreign_experience_years=3,
    )
    base.update(overrides)
    return CrsProfile(**base)


SOFTWARE_JOB = JobContext(
    noc_code="21231",
    teer_level=1,
    province="ON",
    title="Senior AI Engineer",
    employer="Example Corp",
)


def test_job_offer_itself_is_worth_zero_points():
    result = evaluate_job(_candidate(), SOFTWARE_JOB)
    assert result["arranged_employment_points"] == 0


def test_twelve_months_raises_crs():
    result = evaluate_job(_candidate(), SOFTWARE_JOB)
    assert result["crs_delta"] > 0
    assert result["crs_after_12_months"]["total"] > result["crs_now"]["total"]


def test_stem_noc_unlocks_stem_category():
    result = evaluate_job(_candidate(), SOFTWARE_JOB)
    unlocked = {c["id"] for c in result["unlocked_categories"]}
    assert "stem" in unlocked


def test_non_stem_noc_does_not_unlock_stem():
    cook = JobContext(noc_code="63200", teer_level=3, province="ON", title="Cook")
    result = evaluate_job(_candidate(), cook)
    unlocked = {c["id"] for c in result["unlocked_categories"]}
    assert "stem" not in unlocked


def test_unverified_categories_never_assert_eligibility():
    """A category whose NOC list is unverified must surface as needing verification."""
    result = evaluate_job(_candidate(), SOFTWARE_JOB)
    unlocked = {c["id"] for c in result["unlocked_categories"]}
    flagged = {c["id"] for c in result["needs_verification"]}
    for unverified in ("transport", "researchers", "senior_managers", "education"):
        assert unverified not in unlocked
        assert unverified in flagged


def test_military_category_excluded_from_job_scoring():
    result = evaluate_job(_candidate(), SOFTWARE_JOB)
    all_ids = (
        {c["id"] for c in result["unlocked_categories"]}
        | {c["id"] for c in result["needs_verification"]}
    )
    assert "military" not in all_ids


def test_teer_1_role_opens_cec():
    result = evaluate_job(_candidate(), SOFTWARE_JOB)
    cec = next(p for p in result["programs"] if p["id"] == "cec")
    assert cec["eligible_after_this_job"] is True


def test_teer_5_role_does_not_open_cec():
    labourer = JobContext(noc_code="85110", teer_level=5, province="ON", title="Farm labourer")
    result = evaluate_job(_candidate(), labourer)
    cec = next(p for p in result["programs"] if p["id"] == "cec")
    assert cec["eligible_after_this_job"] is False


def test_best_route_produces_a_sentence():
    result = evaluate_job(_candidate(), SOFTWARE_JOB)
    assert result["best_route"]["summary"]
    assert result["best_route"]["verdict"] in {"clears", "short", "no_route"}


def test_french_speaker_unlocks_french_category():
    result = evaluate_job(_candidate(second_language=_clb(7)), SOFTWARE_JOB)
    unlocked = {c["id"] for c in result["unlocked_categories"]}
    assert "french_proficiency" in unlocked


def test_french_category_resolves_its_draw_history():
    """Regression: the catalogue keys `french_proficiency`, draw history keys `french`.

    A silent key miss made French look like a dormant category with zero rounds.
    """
    result = evaluate_job(_candidate(second_language=_clb(7)), SOFTWARE_JOB)
    french = next(c for c in result["unlocked_categories"] if c["id"] == "french_proficiency")
    assert french["rounds_last_12_months"] > 0
    assert french["typical_cutoff"] is not None


def test_dormant_stem_never_becomes_the_recommended_route():
    """STEM has had no rounds since early 2024; eligibility alone must not sell it."""
    result = evaluate_job(_candidate(), SOFTWARE_JOB)
    stem = next(c for c in result["unlocked_categories"] if c["id"] == "stem")
    assert stem["rounds_last_12_months"] == 0
    assert result["best_route"]["route"] != stem["label"]


def test_report_carries_provenance():
    result = evaluate_job(_candidate(), SOFTWARE_JOB)
    assert result["draws_metadata"]["last_verified"]
    assert result["draws_metadata"]["source_url"]
