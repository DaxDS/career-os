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


# 21231 is deliberately NOT on IRCC's 2026 STEM list — see
# test_software_developer_noc_does_not_unlock_stem below.
SOFTWARE_JOB = JobContext(
    noc_code="21231",
    teer_level=1,
    province="ON",
    title="Senior AI Engineer",
    employer="Example Corp",
)

# 21300 (civil engineers) is on the published 2026 STEM list.
STEM_JOB = JobContext(
    noc_code="21300",
    teer_level=1,
    province="ON",
    title="Civil Engineer",
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
    result = evaluate_job(_candidate(), STEM_JOB)
    unlocked = {c["id"] for c in result["unlocked_categories"]}
    assert "stem" in unlocked


def test_software_developer_noc_does_not_unlock_stem():
    """Regression: IRCC's 2026 STEM list dropped the software occupations.

    Our category data wrongly carried 21231/21232 under STEM, so software engineers
    were told they qualified for a category IRCC no longer lists them in. The old
    version of this suite asserted the opposite and passed, because the tests and the
    data shared the same wrong assumption.
    """
    for noc in ("21231", "21232"):
        job = JobContext(noc_code=noc, teer_level=1, province="ON", title="Developer")
        unlocked = {c["id"] for c in evaluate_job(_candidate(), job)["unlocked_categories"]}
        assert "stem" not in unlocked, f"{noc} must not unlock STEM"


def test_non_stem_noc_does_not_unlock_stem():
    cook = JobContext(noc_code="63200", teer_level=3, province="ON", title="Cook")
    result = evaluate_job(_candidate(), cook)
    unlocked = {c["id"] for c in result["unlocked_categories"]}
    assert "stem" not in unlocked


def test_unverified_categories_never_assert_eligibility():
    """An unverified NOC list must never produce an eligibility claim.

    Every category is currently verified against IRCC, so this asserts the mechanism
    rather than naming categories — otherwise the test silently stops testing anything
    the moment the data changes, which is exactly what happened to its previous form.
    """
    import json
    from pathlib import Path

    data = json.loads(
        (Path(__file__).resolve().parent.parent / "data" / "ee_categories.json").read_text(
            encoding="utf-8"
        )
    )
    unverified = {
        c["id"] for c in data["categories"] if c.get("verification_status") != "verified"
    }

    result = evaluate_job(_candidate(), SOFTWARE_JOB)
    unlocked = {c["id"] for c in result["unlocked_categories"]}
    flagged = {c["id"] for c in result["needs_verification"]}

    for cid in unverified:
        assert cid not in unlocked, f"{cid} is unverified and must not assert eligibility"
        assert cid in flagged, f"{cid} is unverified and must be surfaced for verification"


def test_every_category_is_verified_against_ircc():
    """Guards the audit: an unverified list means users get told nothing about it."""
    import json
    from pathlib import Path

    data = json.loads(
        (Path(__file__).resolve().parent.parent / "data" / "ee_categories.json").read_text(
            encoding="utf-8"
        )
    )
    for c in data["categories"]:
        assert c.get("verification_status") == "verified", f"{c['id']} is not verified"
        if not c.get("all_teer_0_3"):
            assert c.get("noc_codes"), f"{c['id']} is verified but has no NOC codes"


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
    """STEM has had no rounds in over two years; eligibility alone must not sell it.

    Uses STEM_JOB rather than SOFTWARE_JOB: a software NOC no longer matches STEM at
    all, so routing this through it would assert nothing about dormancy.
    """
    result = evaluate_job(_candidate(), STEM_JOB)
    stem = next(c for c in result["unlocked_categories"] if c["id"] == "stem")
    assert stem["rounds_last_12_months"] == 0
    assert result["best_route"]["route"] != stem["label"]


def test_report_carries_provenance():
    result = evaluate_job(_candidate(), SOFTWARE_JOB)
    assert result["draws_metadata"]["last_verified"]
    assert result["draws_metadata"]["source_url"]
