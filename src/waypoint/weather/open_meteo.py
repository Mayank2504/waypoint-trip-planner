"""Date-aware Open-Meteo daily forecast enrichment."""
from __future__ import annotations

import time
from datetime import date, timedelta
from typing import Any, Dict, Tuple

from waypoint.http import request_json
from waypoint.weather.codes import weather_label

OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
FORECAST_HORIZON_DAYS = 16
WEATHER_CACHE_TTL_S = 30 * 60
_WEATHER_CACHE: Dict[Tuple[Any, ...], Tuple[float, Dict[str, Any]]] = {}


def _unavailable_dates(start: date, days: int, reason: str) -> Dict[str, Any]:
    return {
        "by_date": {
            (start + timedelta(days=index)).isoformat(): {
                "available": False,
                "label": "Forecast not available",
            }
            for index in range(days)
        },
        "timezone": "",
        "error": reason,
        "attribution": "Weather data by Open-Meteo.com",
    }


def fetch_daily_forecast(
    lat: float,
    lon: float,
    start_date: date,
    days: int,
    *,
    temperature_unit: str = "celsius",
    wind_speed_unit: str = "kmh",
) -> Dict[str, Any]:
    today = date.today()
    if start_date < today or start_date > today + timedelta(days=FORECAST_HORIZON_DAYS - 1):
        return _unavailable_dates(start_date, days, "Trip dates are outside the forecast window.")
    end_date = start_date + timedelta(days=max(1, days) - 1)
    if end_date > today + timedelta(days=FORECAST_HORIZON_DAYS - 1):
        end_date = today + timedelta(days=FORECAST_HORIZON_DAYS - 1)

    key = (
        round(float(lat), 3),
        round(float(lon), 3),
        start_date.isoformat(),
        int(days),
        temperature_unit,
        wind_speed_unit,
    )
    cached = _WEATHER_CACHE.get(key)
    if cached and time.monotonic() - cached[0] < WEATHER_CACHE_TTL_S:
        return cached[1]

    requested_dates = [
        (start_date + timedelta(days=index)).isoformat() for index in range(max(1, days))
    ]
    try:
        payload = request_json(
            "GET",
            OPEN_METEO_FORECAST_URL,
            service="Open-Meteo forecast",
            params={
                "latitude": float(lat),
                "longitude": float(lon),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "timezone": "auto",
                "temperature_unit": temperature_unit,
                "wind_speed_unit": wind_speed_unit,
                "daily": ",".join(
                    (
                        "weather_code",
                        "temperature_2m_max",
                        "temperature_2m_min",
                        "precipitation_probability_max",
                        "precipitation_sum",
                        "wind_speed_10m_max",
                    )
                ),
            },
            timeout=(5, 20),
            attempts=2,
        )
        daily = payload.get("daily") or {}
        dates = daily.get("time") or []
        by_date: Dict[str, Dict[str, Any]] = {}
        for index, day_string in enumerate(dates):
            def value(name: str) -> Any:
                values = daily.get(name) or []
                return values[index] if index < len(values) else None

            code = value("weather_code")
            by_date[str(day_string)] = {
                "available": True,
                "label": weather_label(code),
                "weather_code": code,
                "temperature_max": value("temperature_2m_max"),
                "temperature_min": value("temperature_2m_min"),
                "precipitation_probability": value("precipitation_probability_max"),
                "precipitation_sum": value("precipitation_sum"),
                "wind_speed_max": value("wind_speed_10m_max"),
                "temperature_unit": (payload.get("daily_units") or {}).get(
                    "temperature_2m_max", "°C"
                ),
                "wind_speed_unit": (payload.get("daily_units") or {}).get(
                    "wind_speed_10m_max", "km/h"
                ),
            }
        for day_string in requested_dates:
            by_date.setdefault(
                day_string,
                {"available": False, "label": "Forecast not available"},
            )
        result = {
            "by_date": by_date,
            "timezone": payload.get("timezone") or "",
            "error": "",
            "attribution": "Weather data by Open-Meteo.com",
        }
        _WEATHER_CACHE[key] = (time.monotonic(), result)
        return result
    except Exception as exc:
        return _unavailable_dates(start_date, days, str(exc))


def clear_weather_cache() -> None:
    _WEATHER_CACHE.clear()
