from __future__ import annotations

from ui.map import itinerary_paths, itinerary_points, routed_paths


ITIN = {
    "days": [
        {
            "day": 1,
            "morning": [{"poi_id": "a"}],
            "afternoon": [{"poi_id": "b"}],
            "evening": [{"poi_id": "c"}],
        },
        {
            "day": 2,
            "morning": [{"poi_id": "d"}],
            "afternoon": [],
            "evening": [],
        },
    ]
}
POIS = {
    key: {"name": key.upper(), "category": "test", "lat": index, "lon": index + 10}
    for index, key in enumerate(("a", "b", "c", "d"))
}


def test_points_and_paths_preserve_temporal_order():
    points = itinerary_points(ITIN, POIS)
    paths = itinerary_paths(ITIN, POIS)
    assert [p["poi_id"] for p in points[:3]] == ["a", "b", "c"]
    assert paths[0]["path"] == [[10.0, 0.0], [11.0, 1.0], [12.0, 2.0]]


def test_day_filter_and_single_stop_path():
    assert [p["poi_id"] for p in itinerary_points(ITIN, POIS, 2)] == ["d"]
    assert itinerary_paths(ITIN, POIS, 2) == []


def test_routed_paths_filter_and_ignore_errors():
    routes = {
        1: {"geometry": [[10, 0], [11, 1]], "error": ""},
        2: {"geometry": [], "error": "NoRoute"},
    }
    assert routed_paths(routes) == [
        {"day": 1, "path": [[10, 0], [11, 1]], "color": [11, 110, 79, 200]}
    ]
    assert routed_paths(routes, 2) == []
