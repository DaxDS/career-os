"""Tests for NOC classification validation."""

import json
from pathlib import Path

import pytest

from graphs.noc_classify import classify_posting, validate_noc_code

FIXTURES = json.loads((Path(__file__).parent / "fixtures" / "jd_fixtures.json").read_text(encoding="utf-8"))


def test_validate_noc_code_rejects_invalid():
    assert validate_noc_code("99999") is False
    assert validate_noc_code("21231") is True


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda f: f["id"])
def test_noc_classify_returns_valid_code(fixture, monkeypatch):
    import config

    monkeypatch.setattr(config.settings, "anthropic_api_key", "")
    result = classify_posting(fixture["title"], fixture["description"])
    assert validate_noc_code(result.noc_code)
    assert 0 <= result.teer_level <= 5
    assert 0 <= result.confidence <= 1


def test_job_bank_pretagged_noc():
    result = classify_posting("Developer", "Build software", suggested_noc="21231")
    assert result.noc_code == "21231"
    assert result.confidence >= 0.9
