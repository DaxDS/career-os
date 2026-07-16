"""Tests for activity log helpers."""

from lib.activity_log import format_filter_summary


def test_format_filter_summary_empty():
    assert format_filter_summary({}) == ""


def test_format_filter_summary_single_reason():
    assert format_filter_summary({"Citizenship required": 3}) == (
        "3 jobs filtered out: 3 citizenship required"
    )


def test_format_filter_summary_multiple_reasons():
    text = format_filter_summary({"Citizenship required": 3, "LMIA-supported role — may not suit open permit/PGWP holders": 2})
    assert text.startswith("5 jobs filtered out:")
    assert "3 citizenship required" in text
    assert "2 lmia-supported role" in text.lower()
