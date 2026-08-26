"""Tests for feedback boost math and ranking."""
from __future__ import annotations

from waypoint.config import DOWNVOTE_BOOST, UPVOTE_BOOST
from waypoint.feedback import append_feedback, feedback_boost_map
from waypoint.ranking import rank_pois
from waypoint.osm.tags import tags_for_interests


def test_boost_math(tmp_path, monkeypatch):
    path = tmp_path / "feedback.jsonl"
    monkeypatch.setattr("waypoint.feedback.FEEDBACK_PATH", path)
    append_feedback({"city_key": "paris", "poi_id": "osm_1", "vote": "up"})
    append_feedback({"city_key": "paris", "poi_id": "osm_1", "vote": "up"})
    append_feedback({"city_key": "paris", "poi_id": "osm_1", "vote": "down"})
    append_feedback({"city_key": "london", "poi_id": "osm_1", "vote": "up"})

    boost = feedback_boost_map("paris")
    assert boost["osm_1"] == 2 * UPVOTE_BOOST - DOWNVOTE_BOOST
    assert "osm_1" not in feedback_boost_map("tokyo")
    assert feedback_boost_map("london")["osm_1"] == UPVOTE_BOOST


def test_rank_applies_boost():
    pois = [
        {"poi_id": "a", "name": "Alpha Museum", "category": "tourism:museum", "lat": 0.0, "lon": 0.0, "url": ""},
        {"poi_id": "b", "name": "Beta Cafe", "category": "amenity:cafe", "lat": 0.01, "lon": 0.01, "url": "https://x"},
    ]
    ranked = rank_pois(pois, boost={"a": 5.0}, center={"lat": 0.0, "lon": 0.0}, limit=10)
    assert ranked[0]["poi_id"] == "a"


def test_tags_for_food():
    tags = tags_for_interests(["food"])
    assert "amenity" in tags
    assert "restaurant" in tags["amenity"]
