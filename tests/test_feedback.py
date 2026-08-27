from __future__ import annotations

import json

import pytest

from waypoint import feedback


def test_malformed_lines_and_invalid_votes(tmp_path, monkeypatch):
    path = tmp_path / "feedback.jsonl"
    path.write_text(
        "{broken\n"
        + json.dumps({"city_key": "x", "poi_id": "a", "vote": "up"})
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(feedback, "FEEDBACK_PATH", path)
    monkeypatch.setenv("WAYPOINT_RUNTIME", "local")
    assert feedback.feedback_boost_map("x") == {"a": 0.25}
    with pytest.raises(ValueError):
        feedback.append_feedback({"city_key": "x", "poi_id": "a", "vote": "sideways"})


def test_city_keys_are_case_insensitive(tmp_path, monkeypatch):
    path = tmp_path / "feedback.jsonl"
    monkeypatch.setattr(feedback, "FEEDBACK_PATH", path)
    monkeypatch.setenv("WAYPOINT_RUNTIME", "local")
    feedback.append_feedback({"city_key": "Paris", "poi_id": "a", "vote": "up"})
    assert feedback.feedback_boost_map("PARIS")["a"] == 0.25
