"""Policy-compliant OSRM route enrichment using FOSSGIS profiles."""
from __future__ import annotations

import math
from typing import Any, Dict, List, Sequence, Tuple

from waypoint.http import request_json
from waypoint.rate_limit import RateLimiter

OSRM_BASE_URL = "https://routing.openstreetmap.de"
PROFILE_PREFIX = {"foot": "routed-foot", "bike": "routed-bike", "car": "routed-car"}
_route_limiter = RateLimiter(1.0)
_ROUTE_CACHE: Dict[Tuple[Any, ...], Dict[str, Any]] = {}


def _haversine_km(a: Sequence[float], b: Sequence[float]) -> float:
    lon1, lat1 = map(float, a)
    lon2, lat2 = map(float, b)
    radius = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    value = (
        math.sin(dphi / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(value))


def ordered_day_stops(day: Dict[str, Any], allowed_pois: Dict[str, Any]) -> List[Dict[str, Any]]:
    stops: List[Dict[str, Any]] = []
    for block in ("morning", "afternoon", "evening"):
        for item in day.get(block, []) or []:
            poi = allowed_pois.get(item.get("poi_id"))
            if not poi or poi.get("lat") is None or poi.get("lon") is None:
                continue
            stops.append(
                {
                    "poi_id": item["poi_id"],
                    "name": poi.get("name") or item["poi_id"],
                    "lat": float(poi["lat"]),
                    "lon": float(poi["lon"]),
                    "block": block,
                }
            )
    return stops


def route_day(
    day: Dict[str, Any],
    allowed_pois: Dict[str, Any],
    user_agent: str,
    *,
    mode: str = "foot",
    base_url: str = OSRM_BASE_URL,
) -> Dict[str, Any]:
    day_number = int(day.get("day", 0))
    stops = ordered_day_stops(day, allowed_pois)
    if len(stops) < 2:
        return {
            "day": day_number,
            "geometry": [],
            "legs": [],
            "distance_km": 0.0,
            "duration_min": 0.0,
            "error": "",
        }

    prefix = PROFILE_PREFIX.get(mode, PROFILE_PREFIX["foot"])
    coordinates = tuple((round(stop["lon"], 5), round(stop["lat"], 5)) for stop in stops)
    cache_key = (base_url, prefix, coordinates)
    if cache_key in _ROUTE_CACHE:
        cached = dict(_ROUTE_CACHE[cache_key])
        cached["day"] = day_number
        return cached

    coordinate_path = ";".join(f"{lon},{lat}" for lon, lat in coordinates)
    url = f"{base_url.rstrip('/')}/{prefix}/route/v1/driving/{coordinate_path}"
    _route_limiter.wait()
    try:
        payload = request_json(
            "GET",
            url,
            service="OSRM",
            params={
                "overview": "full",
                "geometries": "geojson",
                "steps": "false",
                "annotations": "false",
            },
            headers={"User-Agent": user_agent, "Referer": "https://github.com/Mayank2504/waypoint-trip-planner"},
            timeout=(5, 25),
            attempts=2,
        )
        if payload.get("code") != "Ok" or not payload.get("routes"):
            raise ValueError(payload.get("message") or payload.get("code") or "NoRoute")
        route = payload["routes"][0]
        waypoints = payload.get("waypoints") or []
        for requested, snapped in zip(coordinates, waypoints):
            location = snapped.get("location") or []
            if len(location) >= 2 and _haversine_km(requested, location) > 1.0:
                raise ValueError("OSRM snapped a stop more than 1 km away.")

        osrm_legs = route.get("legs") or []
        legs: List[Dict[str, Any]] = []
        for index, (origin, destination) in enumerate(zip(stops, stops[1:])):
            raw_leg = osrm_legs[index] if index < len(osrm_legs) else {}
            legs.append(
                {
                    "from_poi_id": origin["poi_id"],
                    "to_poi_id": destination["poi_id"],
                    "from_name": origin["name"],
                    "to_name": destination["name"],
                    "distance_km": round(float(raw_leg.get("distance", 0)) / 1000, 2),
                    "duration_min": round(float(raw_leg.get("duration", 0)) / 60),
                }
            )
        result = {
            "day": day_number,
            "geometry": ((route.get("geometry") or {}).get("coordinates") or []),
            "legs": legs,
            "distance_km": round(float(route.get("distance", 0)) / 1000, 2),
            "duration_min": round(float(route.get("duration", 0)) / 60),
            "error": "",
        }
        _ROUTE_CACHE[cache_key] = dict(result)
        return result
    except Exception as exc:
        return {
            "day": day_number,
            "geometry": [],
            "legs": [],
            "distance_km": 0.0,
            "duration_min": 0.0,
            "error": str(exc),
        }


def route_itinerary(
    itinerary: Dict[str, Any],
    allowed_pois: Dict[str, Any],
    user_agent: str,
    *,
    mode: str = "foot",
) -> Dict[int, Dict[str, Any]]:
    return {
        int(day["day"]): route_day(day, allowed_pois, user_agent, mode=mode)
        for day in itinerary.get("days", []) or []
    }


def route_warnings(routes: Dict[int, Dict[str, Any]], pace: str) -> List[str]:
    limits = {"relaxed": 75, "balanced": 120, "packed": 180}
    limit = limits.get(pace, limits["balanced"])
    return [
        f"Day {day} includes about {route['duration_min']} minutes of walking."
        for day, route in sorted(routes.items())
        if not route.get("error") and float(route.get("duration_min", 0)) > limit
    ]


def clear_route_cache() -> None:
    _ROUTE_CACHE.clear()
