"""Pathway report generation tests."""

from graphs.pathway_report import run_pathway_report, DISCLAIMER
from graphs.pathways import evaluate_pathways


def test_disclaimer_present():
    assert "not immigration advice" in DISCLAIMER.lower()


def test_evaluate_pathways_stem_noc():
    flags = evaluate_pathways("21231", 1, "ON")
    assert flags["ee_eligible"] is True
    assert "stem" in flags["ee_categories"]
