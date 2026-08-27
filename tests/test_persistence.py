from __future__ import annotations

import json

from waypoint import persistence


def _state():
    return {
        "itinerary": {"title": "T", "city": "C", "days": [{"day": 1}]},
        "allowed_pois": {"p1": {"name": "Place"}},
        "allowed_chunks": {"c1": {"source": "Guide"}},
        "center": {"lat": 1, "lon": 2},
        "city_key": "c",
        "start_date": "2026-08-27",
    }


def test_local_round_trip_is_atomic(tmp_path, monkeypatch):
    path = tmp_path / "app_state.json"
    monkeypatch.setattr(persistence, "APP_STATE_PATH", path)
    monkeypatch.setattr(persistence, "DATA_DIR", tmp_path)
    monkeypatch.setenv("WAYPOINT_RUNTIME", "local")
    persistence.save_app_state(_state())
    assert persistence.load_app_state() == _state()
    assert not list(tmp_path.glob("*.tmp"))


def test_cloud_never_reads_or_writes(tmp_path, monkeypatch):
    path = tmp_path / "app_state.json"
    path.write_text(json.dumps(_state()), encoding="utf-8")
    monkeypatch.setattr(persistence, "APP_STATE_PATH", path)
    monkeypatch.setattr(persistence, "DATA_DIR", tmp_path)
    monkeypatch.setenv("WAYPOINT_RUNTIME", "cloud")
    assert persistence.load_app_state() is None
    persistence.save_app_state(_state())
    assert json.loads(path.read_text(encoding="utf-8")) == _state()
    persistence.clear_app_state_file()
    assert path.exists()


def test_corrupt_and_incomplete_state_are_ignored(tmp_path, monkeypatch):
    path = tmp_path / "app_state.json"
    monkeypatch.setattr(persistence, "APP_STATE_PATH", path)
    monkeypatch.setenv("WAYPOINT_RUNTIME", "local")
    path.write_text("{broken", encoding="utf-8")
    assert persistence.load_app_state() is None
    path.write_text('{"itinerary": {}}', encoding="utf-8")
    assert persistence.load_app_state() is None


def test_disabled_or_incomplete_save_does_nothing(tmp_path, monkeypatch):
    path = tmp_path / "app_state.json"
    monkeypatch.setattr(persistence, "APP_STATE_PATH", path)
    monkeypatch.setattr(persistence, "DATA_DIR", tmp_path)
    monkeypatch.setenv("WAYPOINT_RUNTIME", "local")
    persistence.save_app_state(_state(), enabled=False)
    persistence.save_app_state({"itinerary": {}}, enabled=True)
    assert not path.exists()


def test_local_clear_and_non_dict_state(tmp_path, monkeypatch):
    path = tmp_path / "app_state.json"
    monkeypatch.setattr(persistence, "APP_STATE_PATH", path)
    monkeypatch.setattr(persistence, "DATA_DIR", tmp_path)
    monkeypatch.setenv("WAYPOINT_RUNTIME", "local")
    path.write_text("[]", encoding="utf-8")
    assert persistence.load_app_state() is None
    path.write_text("{}", encoding="utf-8")
    persistence.clear_app_state_file()
    assert not path.exists()


def test_cloud_detection_explicit(monkeypatch):
    monkeypatch.setenv("WAYPOINT_RUNTIME", "cloud")
    assert persistence.is_cloud_runtime()
    monkeypatch.setenv("WAYPOINT_RUNTIME", "local")
    assert not persistence.is_cloud_runtime()
