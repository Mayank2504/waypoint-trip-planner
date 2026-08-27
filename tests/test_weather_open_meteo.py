from __future__ import annotations

from datetime import date, timedelta

from waypoint.weather import open_meteo
from waypoint.weather.codes import weather_label


def forecast_payload(day):
    return {
        "timezone": "Asia/Kolkata",
        "daily_units": {"temperature_2m_max": "°C", "wind_speed_10m_max": "km/h"},
        "daily": {
            "time": [day.isoformat()],
            "weather_code": [61],
            "temperature_2m_max": [24],
            "temperature_2m_min": [16],
            "precipitation_probability_max": [70],
            "precipitation_sum": [4.2],
            "wind_speed_10m_max": [18],
        },
    }


def test_forecast_request_and_date_mapping(monkeypatch):
    open_meteo.clear_weather_cache()
    start = date.today()
    captured = {}

    def fake_request(_method, _url, **kwargs):
        captured.update(kwargs["params"])
        return forecast_payload(start)

    monkeypatch.setattr(open_meteo, "request_json", fake_request)
    result = open_meteo.fetch_daily_forecast(10, 20, start, 2)
    first = result["by_date"][start.isoformat()]
    second = result["by_date"][(start + timedelta(days=1)).isoformat()]
    assert captured["timezone"] == "auto"
    assert first["label"] == "Light rain"
    assert first["precipitation_probability"] == 70
    assert second["available"] is False


def test_out_of_horizon_does_not_call_network(monkeypatch):
    called = {"value": False}
    monkeypatch.setattr(
        open_meteo,
        "request_json",
        lambda *_args, **_kwargs: called.update(value=True),
    )
    start = date.today() + timedelta(days=30)
    result = open_meteo.fetch_daily_forecast(10, 20, start, 3)
    assert called["value"] is False
    assert all(not day["available"] for day in result["by_date"].values())


def test_provider_failure_is_nonblocking(monkeypatch):
    open_meteo.clear_weather_cache()
    monkeypatch.setattr(
        open_meteo,
        "request_json",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    result = open_meteo.fetch_daily_forecast(10, 20, date.today(), 1)
    assert result["error"]
    assert not result["by_date"][date.today().isoformat()]["available"]


def test_unknown_and_null_weather_codes():
    assert weather_label(999) == "Weather code 999"
    assert weather_label(None) == "Forecast unavailable"
