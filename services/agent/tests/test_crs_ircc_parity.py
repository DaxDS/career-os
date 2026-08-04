"""Parity with IRCC's published CRS grid.

Every expected value here is transcribed from IRCC's official CRS criteria page,
verified 2026-08-04:
https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/check-score/crs-criteria.html

These are not sanity checks on our own logic — they are the source tables. If IRCC
changes the grid, these fail first and the change becomes a deliberate, reviewable edit
rather than a silent drift in someone's immigration decision.
"""

import pytest

from lib.crs import CrsProfile, LanguageScores, SpouseProfile, calculate_crs


def clb(n: int) -> LanguageScores:
    return LanguageScores(n, n, n, n)


def score(**kwargs):
    return calculate_crs(CrsProfile(**kwargs))


# --- A. Core / human capital -------------------------------------------------

# IRCC table: Age (with spouse | without spouse)
AGE_TABLE = [
    (17, 0, 0), (18, 90, 99), (19, 95, 105),
    (20, 100, 110), (25, 100, 110), (29, 100, 110),
    (30, 95, 105), (31, 90, 99), (32, 85, 94), (33, 80, 88), (34, 75, 83),
    (35, 70, 77), (36, 65, 72), (37, 60, 66), (38, 55, 61), (39, 50, 55),
    (40, 45, 50), (41, 35, 39), (42, 25, 28), (43, 15, 17), (44, 5, 6),
    (45, 0, 0), (50, 0, 0),
]


@pytest.mark.parametrize("age,with_spouse,without_spouse", AGE_TABLE)
def test_age_points_match_ircc(age, with_spouse, without_spouse):
    assert score(age=age).breakdown["age"] == without_spouse
    married = score(
        age=age, has_spouse=True, spouse=SpouseProfile()
    ).breakdown["age"]
    assert married == with_spouse


# IRCC table: Level of education (with spouse | without spouse)
EDUCATION_TABLE = [
    ("none", 0, 0),
    ("secondary", 28, 30),
    ("one_year_post_secondary", 84, 90),
    ("two_year_post_secondary", 91, 98),
    ("bachelors_or_three_year", 112, 120),
    ("two_or_more_credentials", 119, 128),
    ("masters_or_professional", 126, 135),
    ("doctoral", 140, 150),
]


@pytest.mark.parametrize("level,with_spouse,without_spouse", EDUCATION_TABLE)
def test_education_points_match_ircc(level, with_spouse, without_spouse):
    assert score(education=level).breakdown["education"] == without_spouse
    married = score(
        education=level, has_spouse=True, spouse=SpouseProfile()
    ).breakdown["education"]
    assert married == with_spouse


# IRCC table: First official language, points PER ABILITY (with | without)
FIRST_LANGUAGE_TABLE = [
    (3, 0, 0), (4, 6, 6), (5, 6, 6), (6, 8, 9),
    (7, 16, 17), (8, 22, 23), (9, 29, 31), (10, 32, 34), (12, 32, 34),
]


@pytest.mark.parametrize("level,with_spouse,without_spouse", FIRST_LANGUAGE_TABLE)
def test_first_language_points_match_ircc(level, with_spouse, without_spouse):
    # Four abilities at the same level, so the total is 4x the per-ability value.
    assert score(first_language=clb(level)).breakdown["first_language"] == without_spouse * 4
    married = score(
        first_language=clb(level), has_spouse=True, spouse=SpouseProfile()
    ).breakdown["first_language"]
    assert married == with_spouse * 4


def test_first_language_section_maximums():
    assert score(first_language=clb(10)).breakdown["first_language"] == 136
    married = score(first_language=clb(10), has_spouse=True, spouse=SpouseProfile())
    assert married.breakdown["first_language"] == 128


# IRCC table: Second official language, points PER ABILITY
SECOND_LANGUAGE_TABLE = [(4, 0), (5, 1), (6, 1), (7, 3), (8, 3), (9, 6), (10, 6)]


@pytest.mark.parametrize("level,per_ability", SECOND_LANGUAGE_TABLE)
def test_second_language_points_match_ircc(level, per_ability):
    assert score(second_language=clb(level)).breakdown["second_language"] == per_ability * 4


def test_second_language_section_maximums():
    assert score(second_language=clb(9)).breakdown["second_language"] == 24
    married = score(second_language=clb(9), has_spouse=True, spouse=SpouseProfile())
    assert married.breakdown["second_language"] == 22


# IRCC table: Canadian work experience (with | without)
CANADIAN_EXPERIENCE_TABLE = [
    (0, 0, 0), (1, 35, 40), (2, 46, 53), (3, 56, 64), (4, 63, 72), (5, 70, 80), (9, 70, 80),
]


@pytest.mark.parametrize("years,with_spouse,without_spouse", CANADIAN_EXPERIENCE_TABLE)
def test_canadian_experience_points_match_ircc(years, with_spouse, without_spouse):
    assert score(canadian_experience_years=years).breakdown["canadian_experience"] == without_spouse
    married = score(
        canadian_experience_years=years, has_spouse=True, spouse=SpouseProfile()
    ).breakdown["canadian_experience"]
    assert married == with_spouse


# --- B. Spouse factors -------------------------------------------------------

SPOUSE_EDUCATION_TABLE = [
    ("none", 0), ("secondary", 2), ("one_year_post_secondary", 6),
    ("two_year_post_secondary", 7), ("bachelors_or_three_year", 8),
    ("two_or_more_credentials", 9), ("masters_or_professional", 10), ("doctoral", 10),
]


@pytest.mark.parametrize("level,points", SPOUSE_EDUCATION_TABLE)
def test_spouse_education_matches_ircc(level, points):
    result = score(has_spouse=True, spouse=SpouseProfile(education=level))
    assert result.breakdown["spouse_education"] == points


SPOUSE_LANGUAGE_TABLE = [(4, 0), (5, 1), (6, 1), (7, 3), (8, 3), (9, 5), (10, 5)]


@pytest.mark.parametrize("level,per_ability", SPOUSE_LANGUAGE_TABLE)
def test_spouse_language_matches_ircc(level, per_ability):
    result = score(has_spouse=True, spouse=SpouseProfile(first_language=clb(level)))
    assert result.breakdown["spouse_language"] == min(per_ability * 4, 20)


SPOUSE_EXPERIENCE_TABLE = [(0, 0), (1, 5), (2, 7), (3, 8), (4, 9), (5, 10), (8, 10)]


@pytest.mark.parametrize("years,points", SPOUSE_EXPERIENCE_TABLE)
def test_spouse_canadian_experience_matches_ircc(years, points):
    result = score(has_spouse=True, spouse=SpouseProfile(canadian_experience_years=years))
    assert result.breakdown["spouse_canadian_experience"] == points


# --- C. Skill transferability -------------------------------------------------

# IRCC: education x language. CLB 7+ with one under 9 -> max 25; CLB 9+ on all -> max 50.
EDUCATION_LANGUAGE_TABLE = [
    ("secondary", 7, 0), ("secondary", 9, 0),
    ("one_year_post_secondary", 7, 13), ("one_year_post_secondary", 9, 25),
    ("bachelors_or_three_year", 7, 13), ("bachelors_or_three_year", 9, 25),
    ("two_or_more_credentials", 7, 25), ("two_or_more_credentials", 9, 50),
    ("masters_or_professional", 7, 25), ("masters_or_professional", 9, 50),
    ("doctoral", 7, 25), ("doctoral", 9, 50),
]


@pytest.mark.parametrize("education,clb_level,expected", EDUCATION_LANGUAGE_TABLE)
def test_education_language_transferability_matches_ircc(education, clb_level, expected):
    result = score(education=education, first_language=clb(clb_level))
    assert result.breakdown["education_transferability"] == expected


# IRCC: education x Canadian work experience. 1 year -> max 25; 2+ years -> max 50.
EDUCATION_EXPERIENCE_TABLE = [
    ("secondary", 1, 0), ("secondary", 2, 0),
    ("one_year_post_secondary", 1, 13), ("one_year_post_secondary", 2, 25),
    ("bachelors_or_three_year", 1, 13), ("bachelors_or_three_year", 2, 25),
    ("two_or_more_credentials", 1, 25), ("two_or_more_credentials", 2, 50),
    ("doctoral", 1, 25), ("doctoral", 2, 50),
]


@pytest.mark.parametrize("education,years,expected", EDUCATION_EXPERIENCE_TABLE)
def test_education_experience_transferability_matches_ircc(education, years, expected):
    # Language held below CLB 7 so only the experience block contributes.
    result = score(education=education, canadian_experience_years=years, first_language=clb(6))
    assert result.breakdown["education_transferability"] == expected


# IRCC: foreign work experience x language.
FOREIGN_LANGUAGE_TABLE = [
    (0, 7, 0), (0, 9, 0),
    (1, 7, 13), (2, 7, 13), (1, 9, 25), (2, 9, 25),
    (3, 7, 25), (5, 7, 25), (3, 9, 50), (5, 9, 50),
]


@pytest.mark.parametrize("foreign_years,clb_level,expected", FOREIGN_LANGUAGE_TABLE)
def test_foreign_language_transferability_matches_ircc(foreign_years, clb_level, expected):
    result = score(foreign_experience_years=foreign_years, first_language=clb(clb_level))
    assert result.breakdown["foreign_experience_transferability"] == expected


# IRCC: foreign work experience x Canadian work experience.
FOREIGN_CANADIAN_TABLE = [
    (1, 1, 13), (2, 1, 13), (1, 2, 25), (2, 2, 25),
    (3, 1, 25), (3, 2, 50), (5, 3, 50),
]


@pytest.mark.parametrize("foreign_years,canadian_years,expected", FOREIGN_CANADIAN_TABLE)
def test_foreign_canadian_transferability_matches_ircc(foreign_years, canadian_years, expected):
    result = score(
        foreign_experience_years=foreign_years,
        canadian_experience_years=canadian_years,
        first_language=clb(6),  # below CLB 7 so the language block contributes nothing
    )
    assert result.breakdown["foreign_experience_transferability"] == expected


# IRCC: certificate of qualification. CLB 5+ with one under 7 -> 25; CLB 7+ all -> 50.
TRADES_TABLE = [(4, 0), (5, 25), (6, 25), (7, 50), (9, 50)]


@pytest.mark.parametrize("clb_level,expected", TRADES_TABLE)
def test_trades_certificate_matches_ircc(clb_level, expected):
    result = score(trades_certificate=True, first_language=clb(clb_level))
    assert result.breakdown["trades_transferability"] == expected


def test_skill_transferability_section_cap_is_100():
    result = score(
        education="doctoral",
        first_language=clb(10),
        canadian_experience_years=5,
        foreign_experience_years=5,
        trades_certificate=True,
    )
    assert result.transferability == 100


# --- D. Additional points -----------------------------------------------------


def test_sibling_in_canada_matches_ircc():
    assert score(sibling_in_canada=True).breakdown["sibling_in_canada"] == 15


def test_french_bonus_matches_ircc():
    # NCLC 7+ French with English CLB 4 or lower (or no English test) -> 25
    assert score(second_language=clb(7), first_language=clb(4)).breakdown["french_bonus"] == 25
    assert score(second_language=clb(7)).breakdown["french_bonus"] == 25
    # NCLC 7+ French with CLB 5+ on all four English abilities -> 50
    assert score(second_language=clb(7), first_language=clb(5)).breakdown["french_bonus"] == 50
    # Below NCLC 7 earns nothing.
    assert score(second_language=clb(6), first_language=clb(9)).breakdown["french_bonus"] == 0


def test_canadian_study_matches_ircc():
    assert score(canadian_study_credential="one_or_two_year").breakdown["canadian_study"] == 15
    assert score(canadian_study_credential="three_year_plus").breakdown["canadian_study"] == 30


def test_provincial_nomination_matches_ircc():
    assert score(provincial_nomination=True).breakdown["provincial_nomination"] == 600


def test_job_offer_is_worth_nothing():
    """IRCC removed arranged-employment points on 2025-03-25 (200 for NOC 00, 50 otherwise)."""
    assert score(age=30).breakdown["arranged_employment"] == 0


# --- Section maximums as published --------------------------------------------


def test_published_section_maximums():
    single = score(
        age=25,
        education="doctoral",
        first_language=clb(10),
        second_language=clb(10),
        canadian_experience_years=5,
    )
    assert single.breakdown["age"] == 110
    assert single.breakdown["education"] == 150
    # IRCC publishes official languages proficiency as 160 without a spouse,
    # which is first (136) plus second (24).
    assert single.breakdown["first_language"] + single.breakdown["second_language"] == 160
    assert single.breakdown["canadian_experience"] == 80
    assert single.core == 500

    married = score(
        age=25,
        education="doctoral",
        first_language=clb(10),
        second_language=clb(10),
        canadian_experience_years=5,
        has_spouse=True,
        spouse=SpouseProfile(
            education="doctoral", first_language=clb(10), canadian_experience_years=5
        ),
    )
    assert married.breakdown["age"] == 100
    assert married.breakdown["education"] == 140
    assert married.breakdown["first_language"] + married.breakdown["second_language"] == 150
    assert married.breakdown["canadian_experience"] == 70
    assert married.core == 460
    assert married.spouse == 40
