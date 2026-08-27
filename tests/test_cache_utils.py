from __future__ import annotations

import uuid

from waypoint import cache_utils
from waypoint.osm import geocode, overpass
from waypoint.rag import wikivoyage


def test_cached_geocode_success(monkeypatch):
    monkeypatch.setattr(
        geocode,
        "geocode_city",
        lambda *_args, **_kwargs: {"lat": 1, "lon": 2, "display_name": "City"},
    )
    result = cache_utils.cached_geocode(f"City-{uuid.uuid4()}", "ua")
    assert result["lat"] == 1


def test_cached_pois_success_and_error(monkeypatch):
    good_city = f"Good-{uuid.uuid4()}"
    monkeypatch.setattr(
        overpass,
        "fetch_pois",
        lambda *_args, **_kwargs: {
            "city_key": "good",
            "display_name": "Good",
            "lat": 1,
            "lon": 2,
            "pois": [{"poi_id": "p"}],
            "error": "",
        },
    )
    assert cache_utils.cached_fetch_pois(good_city, (), 5, 10, "ua")["pois"]

    monkeypatch.setattr(
        overpass,
        "fetch_pois",
        lambda *_args, **_kwargs: {
            "city_key": "bad",
            "display_name": "Bad",
            "pois": [],
            "error": "offline",
        },
    )
    result = cache_utils.cached_fetch_pois(f"Bad-{uuid.uuid4()}", (), 5, 10, "ua")
    assert result["pois"] == []
    assert "offline" in result["error"]


def test_cached_wikivoyage_success_and_empty(monkeypatch):
    monkeypatch.setattr(wikivoyage, "wikivoyage_resolve_title", lambda *_args: "City")
    monkeypatch.setattr(wikivoyage, "wikivoyage_plaintext", lambda *_args: "Guide text")
    assert cache_utils.cached_wikivoyage_text(f"Good-{uuid.uuid4()}", "ua")["text"] == "Guide text"

    monkeypatch.setattr(wikivoyage, "wikivoyage_resolve_title", lambda *_args: None)
    assert cache_utils.cached_wikivoyage_text(f"Empty-{uuid.uuid4()}", "ua") == {
        "title": "",
        "text": "",
    }
