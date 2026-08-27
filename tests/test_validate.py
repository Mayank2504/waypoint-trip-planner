"""Unit tests for validators."""
from __future__ import annotations

import pytest

from waypoint.validate import (
    extract_json_object,
    find_duplicate_poi_ids,
    other_days_unchanged,
    validate_day_count,
    validate_itinerary_poi_ids,
    validate_plan_inputs,
    validate_source_ids,
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


def test_empty_poi_id_is_rejected():
    itin = {
        "days": [
            {"day": 1, "morning": [{"poi_id": " ", "why": ""}], "afternoon": [], "evening": []}
        ]
    }
    assert validate_itinerary_poi_ids(itin, {}) == ["<empty>"]


def test_day_count_and_numbering():
    itin = {"days": [{"day": 2}, {"day": 1}]}
    errors = validate_day_count(itin, 2)
    assert errors and "Day numbers" in errors[0]


def test_unknown_source_is_rejected():
    itin = {"days": [{"day": 1, "sources": [{"chunk_id": "invented"}]}]}
    assert validate_source_ids(itin, {"real": {}}) == ["invented"]


def test_regeneration_rejects_added_day_and_city_change():
    old = {"city": "A", "days": [{"day": 1}, {"day": 2}]}
    new = {"city": "B", "days": [{"day": 1}, {"day": 2}, {"day": 3}]}
    ok, changed = other_days_unchanged(old, new, 2)
    assert not ok
    assert "city" in changed
    assert 3 in changed


def test_regeneration_rejects_duplicate_missing_and_changed_days():
    old = {"city": "A", "days": [{"day": 1, "notes": "same"}, {"day": 2}]}
    duplicate = {"city": "A", "days": [{"day": 1}, {"day": 1}]}
    assert "duplicate day number" in other_days_unchanged(old, duplicate, 2)[1]
    assert 2 in other_days_unchanged(old, {"city": "A", "days": [{"day": 1}]}, 2)[1]
    changed = {"city": "A", "days": [{"day": 1, "notes": "changed"}, {"day": 2}]}
    assert 1 in other_days_unchanged(old, changed, 2)[1]


def test_source_validation_optional_and_empty():
    itin = {"days": [{"day": 1, "sources": [{"chunk_id": ""}]}]}
    assert validate_source_ids(itin, None) == []
    assert validate_source_ids(itin, {}) == ["<empty>"]


def test_extract_json_error_paths():
    with pytest.raises(ValueError, match="Empty"):
        extract_json_object("")
    with pytest.raises(ValueError, match="No JSON"):
        extract_json_object("plain text")


def test_all_input_boundaries():
    assert not validate_plan_inputs("City", 1, 1)
    assert not validate_plan_inputs("City", 7, 50)
    assert validate_plan_inputs("City", 0, 5)
    assert validate_plan_inputs("City", 8, 51)
