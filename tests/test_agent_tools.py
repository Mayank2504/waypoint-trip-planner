from __future__ import annotations

from waypoint.agent import tools


def test_search_tool_applies_feedback_and_limit(monkeypatch):
    monkeypatch.setattr(
        tools,
        "cached_fetch_pois",
        lambda **_kwargs: {
            "city_key": "city",
            "display_name": "City",
            "lat": 1,
            "lon": 2,
            "pois": [
                {"poi_id": "a", "name": "A", "category": "x", "lat": 1, "lon": 2, "url": ""},
                {"poi_id": "b", "name": "B", "category": "x", "lat": 1, "lon": 2, "url": ""},
            ],
            "error": "",
        },
    )
    monkeypatch.setattr(tools, "feedback_boost_map", lambda _city: {"b": 2})
    result = tools.tool_search_pois("City", [], 5, 1, "", "ua")
    assert [poi["poi_id"] for poi in result["pois"]] == ["b"]
    assert result["center"] == {"lat": 1, "lon": 2}


def test_retrieve_guides_disabled_and_failure(monkeypatch):
    disabled = tools.tool_retrieve_guides("City", "q", 2, "ua", False)
    assert disabled["hits"] == []
    monkeypatch.setattr(
        tools,
        "rag_retrieve",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("blocked")),
    )
    failed = tools.tool_retrieve_guides("City", "q", 2, "ua", True)
    assert failed["hits"] == []
    assert "unavailable" in failed["note"]
