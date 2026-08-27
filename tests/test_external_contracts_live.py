from __future__ import annotations

import os
from datetime import date

import pytest

from waypoint.osm.geocode import build_user_agent, geocode_city
from waypoint.osm.overpass import check_overpass
from waypoint.rag.wikivoyage import wikivoyage_resolve_title
from waypoint.routing.osrm import route_day
from waypoint.weather.open_meteo import fetch_daily_forecast


pytestmark = pytest.mark.live


def _enabled():
    if os.environ.get("WAYPOINT_RUN_LIVE_TESTS") != "1":
        pytest.skip("Set WAYPOINT_RUN_LIVE_TESTS=1 for low-volume provider checks.")


def test_live_geocoding_contract():
    _enabled()
    result = geocode_city(
        "Santa Fe, New Mexico",
        build_user_agent("https://github.com/Mayank2504/waypoint-trip-planner"),
    )
    assert result and result["lat"] and result["lon"]


def test_live_weather_contract():
    _enabled()
    result = fetch_daily_forecast(35.687, -105.938, date.today(), 1)
    assert date.today().isoformat() in result["by_date"]


def test_live_overpass_contract():
    _enabled()
    result = check_overpass(
        build_user_agent("https://github.com/Mayank2504/waypoint-trip-planner")
    )
    assert result["ok"], result["detail"]


def test_live_osrm_foot_contract():
    _enabled()
    day = {
        "day": 1,
        "morning": [{"poi_id": "a"}],
        "afternoon": [{"poi_id": "b"}],
        "evening": [],
    }
    pois = {
        "a": {"name": "A", "lat": 52.5208, "lon": 13.4095},
        "b": {"name": "B", "lat": 52.5163, "lon": 13.3777},
    }
    result = route_day(
        day,
        pois,
        build_user_agent("https://github.com/Mayank2504/waypoint-trip-planner"),
    )
    assert not result["error"]
    assert result["geometry"]


def test_live_wikivoyage_contract_degrades_cleanly():
    _enabled()
    result = wikivoyage_resolve_title(
        "Paris",
        build_user_agent("https://github.com/Mayank2504/waypoint-trip-planner"),
    )
    assert result is None or isinstance(result, str)
