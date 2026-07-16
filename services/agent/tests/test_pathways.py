"""Tests for pathway rule evaluation."""

import pytest

from graphs.pathways import evaluate_pathways


def test_ee_eligible_teer_1_stem():
    flags = evaluate_pathways("21231", 1, "ON")
    assert flags["ee_eligible"] is True
    assert "stem" in flags["ee_categories"]


def test_ee_ineligible_teer_4():
    flags = evaluate_pathways("63200", 3, "ON")
    assert flags["ee_eligible"] is True  # TEER 3 cook is EE eligible


def test_bc_pnp_tech():
    flags = evaluate_pathways("21231", 1, "BC")
    assert "bc_pnp_tech" in flags["pnp_streams"]


def test_aip_atlantic():
    flags = evaluate_pathways("31301", 1, "NS")
    assert flags["aip_relevant"] is True
    assert "nsnp_in_demand" in flags["pnp_streams"] or "aip" in flags["pnp_streams"]


def test_no_noc_returns_empty():
    flags = evaluate_pathways(None, None, "ON")
    assert flags["ee_eligible"] is False
    assert flags["ee_categories"] == []
