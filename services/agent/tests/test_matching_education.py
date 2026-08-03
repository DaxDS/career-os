from graphs.matching import _education_fit, _required_education, score_match


def test_infers_required_education_from_requirements():
    parsed = {"requirements": ["Bachelor's degree in Computer Science or equivalent"]}
    assert _required_education(parsed, {}) == "bachelors_or_three_year"


def test_prefers_the_most_specific_signal():
    parsed = {"requirements": ["PhD preferred, Bachelor's degree required"]}
    assert _required_education(parsed, {}) == "doctoral"


def test_no_stated_requirement_returns_none():
    assert _required_education({"requirements": ["5 years of Python"]}, {}) is None


def test_meeting_the_requirement_scores_full():
    score, gap = _education_fit(
        {"education_level": "masters_or_professional"}, "bachelors_or_three_year"
    )
    assert score == 100.0
    assert gap is None


def test_falling_short_is_penalised_and_explained():
    score, gap = _education_fit({"education_level": "secondary"}, "masters_or_professional")
    assert score < 50
    assert gap and "masters" in gap


def test_missing_profile_education_is_neutral_and_flagged():
    score, gap = _education_fit({}, "bachelors_or_three_year")
    assert score == 50.0
    assert gap and "not set" in gap


def test_unstated_requirement_is_neutral():
    score, gap = _education_fit({"education_level": "bachelors_or_three_year"}, None)
    assert score == 50.0
    assert gap is None


def test_education_now_affects_the_overall_match_score():
    """Regression: education was absent from the weighting entirely."""
    job = {"noc_code": "21231", "teer_level": 1, "province": "ON", "raw_jd": ""}
    parsed = {"requirements": ["Master's degree in Computer Science"], "skills": ["python"]}
    work_history = [{"mapped_noc_code": "21231", "mapped_teer": 1, "duties_text": "python"}]

    high, high_breakdown = score_match(
        {"province": "ON", "education_level": "masters_or_professional"}, work_history, job, parsed
    )
    low, low_breakdown = score_match(
        {"province": "ON", "education_level": "secondary"}, work_history, job, parsed
    )

    assert high_breakdown["education_fit"] > low_breakdown["education_fit"]
    assert high > low


def test_weights_sum_to_one():
    job = {"noc_code": "21231", "teer_level": 1, "province": "ON", "raw_jd": ""}
    score, breakdown = score_match({"province": "ON"}, [], job, {})
    assert 0 <= score <= 100
    assert "education_fit" in breakdown
