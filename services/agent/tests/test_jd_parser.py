"""Tests for jd_parser rule-based path (no API key)."""

import json
from pathlib import Path

import pytest

from parsers.jd_parser import parse_jd

FIXTURES = json.loads((Path(__file__).parent / "fixtures" / "jd_fixtures.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda f: f["id"])
def test_jd_parser_rule_based(fixture, monkeypatch):
    import config

    monkeypatch.setattr(config.settings, "anthropic_api_key", "")
    result = parse_jd(fixture["title"], fixture["description"], fixture.get("company", ""))

    if fixture["id"] == "lmia_flagged":
        assert result.lmia_flag is True
    if fixture["id"] == "clearance_required":
        assert result.clearance_required == "secret"
    if fixture["id"] == "bilingual_required":
        assert result.bilingual_required is True
    if fixture["id"] == "wage_stated_hourly":
        assert result.wage_offered == 45.0
        assert result.wage_period == "hourly"
    if fixture["id"] == "citizenship_required":
        assert result.work_auth_required == "citizenship_required"
    if fixture["id"] == "remote_hybrid":
        assert result.remote is True

    assert isinstance(result.requirements, list)
