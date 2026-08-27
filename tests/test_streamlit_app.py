from __future__ import annotations

from pathlib import Path
import json

from streamlit.testing.v1 import AppTest


def test_initial_app_render_is_error_free(monkeypatch):
    monkeypatch.setenv("WAYPOINT_RUNTIME", "cloud")
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=20)
    assert not app.exception
    assert app.title[0].value == "Waypoint"
    assert any(button.label == "Generate itinerary" for button in app.button)


def test_saved_itinerary_map_exports_and_feedback_render(monkeypatch, valid_itinerary, allowed_pois):
    monkeypatch.setenv("WAYPOINT_RUNTIME", "cloud")
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path))
    app.session_state["_loaded_app_state"] = True
    app.session_state["itinerary"] = valid_itinerary
    app.session_state["allowed_pois"] = allowed_pois
    app.session_state["allowed_chunks"] = {}
    app.session_state["center"] = {"lat": 10, "lon": 20}
    app.session_state["city_key"] = "test city"
    app.session_state["routing_enabled"] = False
    app.session_state["weather_enabled"] = False
    app.session_state["show_trace"] = True
    app.session_state["trace"] = [
        {"kind": "model_call", "step": 1, "ts": 1},
        {"kind": "model_result", "step": 1, "elapsed_s": 0.2, "ts": 1},
        {"kind": "tool_call", "name": "search_pois", "args": {}, "ts": 1},
        {"kind": "tool_result", "name": "search_pois", "elapsed_s": 0.1, "ts": 1},
        {"kind": "tool_error", "name": "guide", "elapsed_s": 0.1, "error": "blocked", "ts": 1},
        {"kind": "note", "message": "fallback", "ts": 1},
        {"kind": "run_complete", "elapsed_s": 0.5, "ts": 1},
    ]
    app.session_state["_health_results"] = {
        "Nominatim": {"ok": True, "detail": "ok"},
        "Overpass": {"ok": False, "detail": "offline"},
        "Wikivoyage": {"ok": False, "detail": "blocked"},
    }
    app = app.run(timeout=20)
    assert not app.exception
    assert any(header.value == "Itinerary" for header in app.header)
    assert any(button.label == "Up" for button in app.button)
    assert len(app.download_button) == 2


def test_route_weather_degraded_state_renders(monkeypatch, valid_itinerary, allowed_pois):
    monkeypatch.setenv("WAYPOINT_RUNTIME", "cloud")
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path))
    app.session_state["_loaded_app_state"] = True
    app.session_state["itinerary"] = valid_itinerary
    app.session_state["allowed_pois"] = allowed_pois
    app.session_state["allowed_chunks"] = {}
    app.session_state["center"] = {"lat": 10, "lon": 20}
    app.session_state["city_key"] = "test city"
    app.session_state["routing_enabled"] = True
    app.session_state["weather_enabled"] = True
    signature = json.dumps(
        {"itinerary": valid_itinerary, "allowed_pois": allowed_pois},
        ensure_ascii=False,
        sort_keys=True,
    )
    app.session_state["_route_signature"] = signature
    app.session_state["routes"] = {
        1: {"day": 1, "geometry": [], "legs": [], "error": "offline", "duration_min": 0}
    }
    app = app.run(timeout=20)
    assert not app.exception
    assert any("straight-line" in caption.value for caption in app.caption)
