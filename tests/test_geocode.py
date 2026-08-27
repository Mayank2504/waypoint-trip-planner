from __future__ import annotations

from waypoint.osm import geocode


def test_nominatim_parses_list(monkeypatch):
    monkeypatch.setattr(geocode.nominatim_limiter, "wait", lambda: None)
    monkeypatch.setattr(
        geocode,
        "request_json",
        lambda *_args, **_kwargs: [{"lat": "1.2", "lon": "3.4", "display_name": "City"}],
    )
    assert geocode._geocode_nominatim("City", "ua", limit=1)[0]["lat"] == 1.2


def test_fallback_order_after_primary_failure(monkeypatch):
    monkeypatch.setattr(
        geocode,
        "_geocode_nominatim",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("blocked")),
    )
    monkeypatch.setattr(
        geocode,
        "_geocode_open_meteo",
        lambda *_args, **_kwargs: [{"lat": 1, "lon": 2, "display_name": "Fallback"}],
    )
    monkeypatch.setattr(geocode, "_geocode_photon", lambda *_args, **_kwargs: [])
    assert geocode.geocode_city("City", "ua")["display_name"] == "Fallback"


def test_open_meteo_and_photon_parsing(monkeypatch):
    monkeypatch.setattr(
        geocode,
        "request_json",
        lambda *_args, **_kwargs: {
            "results": [
                {
                    "name": "Paris",
                    "admin1": "Île-de-France",
                    "country": "France",
                    "latitude": 48.8,
                    "longitude": 2.3,
                }
            ]
        },
    )
    result = geocode._geocode_open_meteo("Paris", "ua", limit=1)[0]
    assert result["display_name"] == "Paris, Île-de-France, France"

    monkeypatch.setattr(
        geocode,
        "request_json",
        lambda *_args, **_kwargs: {
            "features": [
                {
                    "geometry": {"coordinates": [2.3, 48.8]},
                    "properties": {"name": "Paris", "country": "France"},
                }
            ]
        },
    )
    assert geocode._geocode_photon("Paris", "ua", limit=1)[0]["lon"] == 2.3


def test_blank_city_and_all_failures(monkeypatch):
    assert geocode.geocode_city("", "ua") is None
    for name in ("_geocode_nominatim", "_geocode_open_meteo", "_geocode_photon"):
        monkeypatch.setattr(
            geocode,
            name,
            lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("offline")),
        )
    assert geocode.geocode_city("Nowhere", "ua") is None


def test_placeholder_user_agent_uses_repository():
    value = geocode.build_user_agent("your-email@example.com")
    assert "github.com/Mayank2504" in value
