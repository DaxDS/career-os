from lib.crs import (
    MAX_TOTAL,
    CrsProfile,
    LanguageScores,
    SpouseProfile,
    calculate_crs,
)


def _clb(level: int) -> LanguageScores:
    return LanguageScores(reading=level, writing=level, listening=level, speaking=level)


def test_empty_profile_scores_zero():
    result = calculate_crs(CrsProfile())
    assert result.total == 0


def test_single_candidate_core_factors():
    """29, master's, CLB 9 across the board, no Canadian experience."""
    profile = CrsProfile(
        age=29,
        education="masters_or_professional",
        first_language=_clb(9),
    )
    result = calculate_crs(profile)

    assert result.breakdown["age"] == 110
    assert result.breakdown["education"] == 135
    assert result.breakdown["first_language"] == 124  # 31 x 4
    assert result.breakdown["canadian_experience"] == 0
    assert result.core == 369


def test_spouse_reduces_core_and_adds_spouse_block():
    base = CrsProfile(age=29, education="masters_or_professional", first_language=_clb(9))
    with_spouse = CrsProfile(
        age=29,
        education="masters_or_professional",
        first_language=_clb(9),
        has_spouse=True,
        spouse=SpouseProfile(education="bachelors_or_three_year", first_language=_clb(9)),
    )

    single = calculate_crs(base)
    married = calculate_crs(with_spouse)

    # Core factors are worth less with an accompanying spouse.
    assert married.breakdown["age"] == 100
    assert married.breakdown["education"] == 126
    # Spouse contributes education + language points.
    assert married.breakdown["spouse_education"] == 8
    assert married.breakdown["spouse_language"] == 20
    assert married.spouse == 28
    assert single.core > married.core


def test_age_45_and_over_scores_zero_age_points():
    result = calculate_crs(CrsProfile(age=45, education="bachelors_or_three_year"))
    assert result.breakdown["age"] == 0


def test_canadian_experience_caps_at_five_years():
    four = calculate_crs(CrsProfile(canadian_experience_years=4))
    ten = calculate_crs(CrsProfile(canadian_experience_years=10))
    assert four.breakdown["canadian_experience"] == 72
    assert ten.breakdown["canadian_experience"] == 80


def test_skill_transferability_caps_at_100():
    profile = CrsProfile(
        age=29,
        education="doctoral",
        first_language=_clb(10),
        canadian_experience_years=3,
        foreign_experience_years=5,
        trades_certificate=True,
    )
    result = calculate_crs(profile)
    assert result.transferability == 100


def test_provincial_nomination_adds_600():
    without = calculate_crs(CrsProfile(age=29, education="bachelors_or_three_year"))
    with_pn = calculate_crs(
        CrsProfile(age=29, education="bachelors_or_three_year", provincial_nomination=True)
    )
    assert with_pn.total - without.total == 600


def test_arranged_employment_is_always_zero():
    """IRCC removed arranged-employment points on 2025-03-25."""
    result = calculate_crs(CrsProfile(age=29, education="bachelors_or_three_year"))
    assert result.breakdown["arranged_employment"] == 0


def test_french_bonus_tiers():
    strong_french_weak_english = calculate_crs(
        CrsProfile(first_language=_clb(4), second_language=_clb(7))
    )
    strong_french_good_english = calculate_crs(
        CrsProfile(first_language=_clb(7), second_language=_clb(7))
    )
    assert strong_french_weak_english.breakdown["french_bonus"] == 25
    assert strong_french_good_english.breakdown["french_bonus"] == 50


def test_total_never_exceeds_maximum():
    maxed = CrsProfile(
        age=20,
        education="doctoral",
        first_language=_clb(10),
        second_language=_clb(10),
        canadian_experience_years=5,
        foreign_experience_years=5,
        provincial_nomination=True,
        sibling_in_canada=True,
        canadian_study_credential="three_year_plus",
        trades_certificate=True,
        has_spouse=True,
        spouse=SpouseProfile(
            education="doctoral", first_language=_clb(10), canadian_experience_years=5
        ),
    )
    assert calculate_crs(maxed).total <= MAX_TOTAL


def test_extra_year_of_canadian_experience_raises_score():
    before = calculate_crs(
        CrsProfile(age=29, education="bachelors_or_three_year", first_language=_clb(9))
    )
    after = calculate_crs(
        CrsProfile(
            age=29,
            education="bachelors_or_three_year",
            first_language=_clb(9),
            canadian_experience_years=1,
        )
    )
    assert after.total > before.total
