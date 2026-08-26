"""Unit tests for validators."""
from __future__ import annotations

import pytest

from waypoint.validate import (
    extract_json_object,
    find_duplicate_poi_ids,
    other_days_unchanged,
    validate_itinerary_poi_ids,
    validate_plan_inputs,
)


def test_validate_poi_ids_ok():
    itin = {
        "days": [
            {
                "day": 1,
                "morning": [{"poi_id": "a", "why": "x"}],
                "afternoon": [],
                "evening": [],
            }
        ]
    }
    assert validate_itinerary_poi_ids(itin, {"a": {}}) == []


def test_validate_poi_ids_bad():
    itin = {
        "days": [
            {
                "day": 1,
                "morning": [{"poi_id": "missing", "why": "x"}],
                "afternoon": [],
                "evening": [],
            }
        ]
    }
    assert validate_itinerary_poi_ids(itin, {"a": {}}) == ["missing"]


def test_duplicates():
    itin = {
        "days": [
            {
                "day": 1,
                "morning": [{"poi_id": "a", "why": "x"}],
                "afternoon": [{"poi_id": "a", "why": "y"}],
                "evening": [],
            }
        ]
    }
    assert find_duplicate_poi_ids(itin) == ["a"]


def test_other_days_unchanged():
    old = {
        "days": [
            {"day": 1, "morning": [{"poi_id": "a", "why": "1"}], "afternoon": [], "evening": []},
            {"day": 2, "morning": [{"poi_id": "b", "why": "2"}], "afternoon": [], "evening": []},
        ]
    }
    new_ok = {
        "days": [
            {"day": 1, "morning": [{"poi_id": "a", "why": "1"}], "afternoon": [], "evening": []},
            {"day": 2, "morning": [{"poi_id": "c", "why": "new"}], "afternoon": [], "evening": []},
        ]
    }
    ok, changed = other_days_unchanged(old, new_ok, target_day=2)
    assert ok and changed == []

    new_bad = {
        "days": [
            {"day": 1, "morning": [{"poi_id": "z", "why": "changed"}], "afternoon": [], "evening": []},
            {"day": 2, "morning": [{"poi_id": "c", "why": "new"}], "afternoon": [], "evening": []},
        ]
    }
    ok2, changed2 = other_days_unchanged(old, new_bad, target_day=2)
    assert not ok2 and changed2 == [1]


def test_extract_json():
    raw = (
        'Here you go:\n```json\n'
        '{"title": "T", "city": "C", "days": [{"day": 1, "morning": [], '
        '"afternoon": [], "evening": [], "notes": "", "sources": []}]}\n```\n'
    )
    data = extract_json_object(raw)
    assert data["title"] == "T"


def test_validate_plan_inputs():
    assert validate_plan_inputs("", 3, 8)
    assert not validate_plan_inputs("Paris", 3, 8)
