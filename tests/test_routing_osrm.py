from __future__ import annotations

from waypoint.routing import osrm


def itinerary():
    return {
        "days": [
            {
                "day": 1,
                "morning": [{"poi_id": "a", "why": ""}],
                "afternoon": [{"poi_id": "b", "why": ""}],
                "evening": [{"poi_id": "c", "why": ""}],
            }
        ]
    }


def pois():
    return {
        "a": {"name": "A", "lat": 10.0, "lon": 20.0},
        "b": {"name": "B", "lat": 10.01, "lon": 20.01},
        "c": {"name": "C", "lat": 10.02, "lon": 20.02},
    }


def response():
    return {
        "code": "Ok",
        "waypoints": [
            {"location": [20.0, 10.0]},
            {"location": [20.01, 10.01]},
            {"location": [20.02, 10.02]},
        ],
        "routes": [
            {
                "distance": 3000,
                "duration": 1800,
                "geometry": {"coordinates": [[20.0, 10.0], [20.02, 10.02]]},
                "legs": [
                    {"distance": 1000, "duration": 600},
                    {"distance": 2000, "duration": 1200},
                ],
            }
        ],
    }


def test_foot_url_coordinate_order_and_legs(monkeypatch):
    osrm.clear_route_cache()
    monkeypatch.setattr(osrm._route_limiter, "wait", lambda: None)
    captured = {}

    def fake_request(method, url, **kwargs):
        captured["url"] = url
        captured["params"] = kwargs["params"]
        return response()

    monkeypatch.setattr(osrm, "request_json", fake_request)
    route = osrm.route_day(itinerary()["days"][0], pois(), "ua")
    assert "/routed-foot/route/v1/driving/20.0,10.0;20.01,10.01;20.02,10.02" in captured["url"]
    assert route["distance_km"] == 3
    assert route["duration_min"] == 30
    assert route["legs"][0]["from_poi_id"] == "a"
    assert route["legs"][1]["to_poi_id"] == "c"


def test_no_route_is_nonblocking(monkeypatch):
    osrm.clear_route_cache()
    monkeypatch.setattr(osrm._route_limiter, "wait", lambda: None)
    monkeypatch.setattr(osrm, "request_json", lambda *_args, **_kwargs: {"code": "NoRoute"})
    route = osrm.route_day(itinerary()["days"][0], pois(), "ua")
    assert route["error"]
    assert route["geometry"] == []


def test_implausible_snap_rejected(monkeypatch):
    osrm.clear_route_cache()
    monkeypatch.setattr(osrm._route_limiter, "wait", lambda: None)
    payload = response()
    payload["waypoints"][0]["location"] = [0, 0]
    monkeypatch.setattr(osrm, "request_json", lambda *_args, **_kwargs: payload)
    route = osrm.route_day(itinerary()["days"][0], pois(), "ua")
    assert "more than 1 km" in route["error"]


def test_cached_route_avoids_second_request(monkeypatch):
    osrm.clear_route_cache()
    monkeypatch.setattr(osrm._route_limiter, "wait", lambda: None)
    calls = {"count": 0}

    def fake_request(*_args, **_kwargs):
        calls["count"] += 1
        return response()

    monkeypatch.setattr(osrm, "request_json", fake_request)
    osrm.route_day(itinerary()["days"][0], pois(), "ua")
    osrm.route_day(itinerary()["days"][0], pois(), "ua")
    assert calls["count"] == 1


def test_route_warning_respects_pace():
    warnings = osrm.route_warnings(
        {1: {"duration_min": 100, "error": ""}, 2: {"duration_min": 200, "error": "failed"}},
        "relaxed",
    )
    assert warnings == ["Day 1 includes about 100 minutes of walking."]
