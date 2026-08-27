from __future__ import annotations

from waypoint.osm import overpass
from waypoint.config import OVERPASS_URLS


def test_query_covers_all_osm_element_types_and_radius():
    query = overpass._overpass_query_one(10, 20, 25_000, "tourism", "museum", 12)
    assert "node(around:25000" in query
    assert "way(around:25000" in query
    assert "relation(around:25000" in query
    assert "out center 12" in query


def test_parse_elements_deduplicates_and_builds_urls():
    elements = [
        {"type": "node", "id": 1, "lat": 1, "lon": 2, "tags": {"name": "A", "tourism": "museum"}},
        {"type": "node", "id": 1, "lat": 1, "lon": 2, "tags": {"name": "A", "tourism": "museum"}},
        {"type": "way", "id": 2, "center": {"lat": 3, "lon": 4}, "tags": {"name": "B", "leisure": "park"}},
    ]
    pois = overpass._parse_elements(elements, 10)
    assert [p["poi_id"] for p in pois] == ["osm_node_1", "osm_way_2"]
    assert pois[0]["url"] == "https://www.openstreetmap.org/node/1"
    assert pois[1]["lat"] == 3


def test_fetch_preserves_balanced_categories(monkeypatch):
    monkeypatch.setattr(
        overpass,
        "geocode_city",
        lambda *_args, **_kwargs: {"lat": 1, "lon": 2, "display_name": "City"},
    )
    monkeypatch.setattr(
        "waypoint.cache_utils.cached_geocode",
        lambda *_args, **_kwargs: {"lat": 1, "lon": 2, "display_name": "City"},
    )
    monkeypatch.setattr(
        overpass,
        "tags_for_interests",
        lambda _interests: {"amenity": "cafe", "tourism": "museum"},
    )

    def fake_post(query, _headers, deadline=None):
        if "amenity" in query:
            return [
                {"poi_id": f"a{i}", "name": f"Cafe {i}", "category": "amenity:cafe", "lat": 1, "lon": 2, "url": ""}
                for i in range(10)
            ], None
        return [
            {"poi_id": f"t{i}", "name": f"Museum {i}", "category": "tourism:museum", "lat": 1, "lon": 2, "url": ""}
            for i in range(10)
        ], None

    monkeypatch.setattr(overpass, "_post_overpass", fake_post)
    result = overpass.fetch_pois("City", ("food", "museums"), 10, 10, "ua")
    assert len(result["pois"]) == 10
    assert {p["category"].split(":")[0] for p in result["pois"]} == {"amenity", "tourism"}


def test_fetch_returns_partial_results(monkeypatch):
    monkeypatch.setattr(
        "waypoint.cache_utils.cached_geocode",
        lambda *_args, **_kwargs: {"lat": 1, "lon": 2, "display_name": "City"},
    )
    monkeypatch.setattr(overpass, "tags_for_interests", lambda _: {"amenity": "cafe", "tourism": "museum"})
    calls = {"count": 0}

    def partial(*_args, **_kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return [
                {"poi_id": "a", "name": "Cafe", "category": "amenity:cafe", "lat": 1, "lon": 2, "url": ""}
            ], None
        return [], "timeout"

    monkeypatch.setattr(overpass, "_post_overpass", partial)
    result = overpass.fetch_pois("City", ("food",), 5, 10, "ua")
    assert [p["poi_id"] for p in result["pois"]] == ["a"]
    assert result["error"] == ""


def test_post_overpass_falls_back_between_hosts(monkeypatch):
    calls = {"count": 0}

    def fake_request(*_args, **_kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("first host down")
        return {
            "elements": [
                {"type": "node", "id": 1, "lat": 1, "lon": 2, "tags": {"name": "Place", "tourism": "museum"}}
            ]
        }

    monkeypatch.setattr(overpass, "request_json", fake_request)
    pois, error = overpass._post_overpass("query", {"User-Agent": "ua"})
    assert error is None
    assert pois[0]["poi_id"] == "osm_node_1"
    assert calls["count"] == 2


def test_empty_success_does_not_try_other_mirrors(monkeypatch):
    calls = {"count": 0}

    def empty_success(*_args, **_kwargs):
        calls["count"] += 1
        return {"elements": []}

    monkeypatch.setattr(overpass, "request_json", empty_success)
    pois, error = overpass._post_overpass("query", {"User-Agent": "ua"})
    assert pois == []
    assert error is None
    assert calls["count"] == 1


def test_check_overpass_reports_success_and_failure(monkeypatch):
    monkeypatch.setattr(overpass, "request_json", lambda *_args, **_kwargs: {})
    healthy = overpass.check_overpass("ua")
    assert healthy["ok"]
    assert len(healthy["mirrors"]) == len(OVERPASS_URLS)
    monkeypatch.setattr(
        overpass,
        "request_json",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    assert not overpass.check_overpass("ua")["ok"]


def test_mirror_list_is_global_and_excludes_retired_endpoints():
    assert OVERPASS_URLS[0].startswith("https://lz4.overpass-api.de")
    assert all("kumi.systems" not in host for host in OVERPASS_URLS)
    assert all("overpass.osm.ch" not in host for host in OVERPASS_URLS)
