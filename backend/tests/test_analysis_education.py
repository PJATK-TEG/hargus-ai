"""Tests for analysis activity input coercion helpers."""

from __future__ import annotations

from hargus_api.temporal.activities import analysis as analysis_activities


def test_normalize_education_coerces_numeric_year_to_string() -> None:
    c = analysis_activities._CoercionCounter()
    raw = [
        {
            "institution": "MIT",
            "degree": "B.S.",
            "field": "CS",
            "year": 2015,
        }
    ]
    out = analysis_activities._normalize_education_entries(raw, c)
    assert len(out) == 1
    assert out[0]["year"] == "2015"
    assert out[0]["institution"] == "MIT"
    assert c.count >= 1


def test_normalize_education_skips_non_dict_entries() -> None:
    c = analysis_activities._CoercionCounter()
    out = analysis_activities._normalize_education_entries(["not-a-dict"], c)
    assert out == []
    assert c.count >= 1


def test_normalize_education_non_list_returns_empty() -> None:
    c = analysis_activities._CoercionCounter()
    assert analysis_activities._normalize_education_entries(None, c) == []
    assert c.count >= 1
