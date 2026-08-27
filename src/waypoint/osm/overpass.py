"""Overpass API POI fetching with retries and host fallbacks."""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

import requests

from waypoint.config import OVERPASS_URLS
from waypoint.osm.geocode import geocode_city
from waypoint.osm.tags import tags_for_interests


def _overpass_query_one(lat: float, lon: float, radius_m: int, key: str, value: str) -> str:
    """One small node query. Combined regex unions often 504/406 on public Overpass."""
    radius_m = int(min(max(radius_m, 500), 8000))
    return (
        f'[out:json][timeout:15];'
        f'node(around:{radius_m},{lat},{lon})["{key}"~"{value}"]["name"];'
        f'out center 40;'
    )


def category_from_tags(tags: Dict[str, str]) -> str:
    for key in ("tourism", "amenity", "leisure", "historic", "natural", "shop"):
        if key in tags:
            return f"{key}:{tags.get(key)}"
    return "other"


def _parse_elements(elements: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for el in elements:
        tags = el.get("tags") or {}
        name = tags.get("name")
        if not name:
            continue
        if "lat" in el and "lon" in el:
            plat, plon = el["lat"], el["lon"]
        else:
            c = el.get("center") or {}
            plat, plon = c.get("lat"), c.get("lon")
        if plat is None or plon is None:
            continue
        poi_id = f"osm_{el['type']}_{el['id']}"
        if poi_id in seen:
            continue
        seen.add(poi_id)
        out.append(
            {
                "poi_id": poi_id,
                "name": name,
                "category": category_from_tags(tags),
                "lat": float(plat),
                "lon": float(plon),
                "url": tags.get("website") or tags.get("url") or "",
            }
        )
        if len(out) >= max(1, min(limit, 200)):
            break
    return out


def _post_overpass(q: str, headers: Dict[str, str]) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    last_err: Optional[str] = None
    for host in OVERPASS_URLS:
        try:
            r = requests.post(host, data={"data": q}, headers=headers, timeout=20)
            if r.status_code in (403, 406, 429) or r.status_code >= 500:
                last_err = f"{host} HTTP {r.status_code}"
                time.sleep(0.4)
                continue
            r.raise_for_status()
            data = r.json()
            pois = _parse_elements(data.get("elements", []) or [], 80)
            if pois:
                return pois, None
            last_err = f"{host} returned 0 POIs"
        except Exception as e:
            last_err = f"{host}: {e}"
            continue
    return [], last_err


def fetch_pois(
    city: str,
    interests: Tuple[str, ...],
    radius_km: float,
    limit: int,
    user_agent: str,
) -> Dict[str, Any]:
    geo = geocode_city(city, user_agent=user_agent)
    if not geo:
        return {
            "city_key": city.strip().lower(),
            "display_name": city,
            "lat": None,
            "lon": None,
            "pois": [],
            "error": (
                "Could not geocode this city (Nominatim often returns 403). "
                "Try 'City, Country' and a real User-Agent email."
            ),
        }

    lat, lon = geo["lat"], geo["lon"]
    display_name = geo["display_name"]
    city_key = display_name.strip().lower()
    tag_filters = tags_for_interests(list(interests))
    radius_m = int(max(500, min(radius_km, 8) * 1000))

    headers = {
        "User-Agent": user_agent or "WaypointTripPlanner/1.0 (+https://github.com/Mayank2504/waypoint-trip-planner)",
        "Accept": "*/*",
    }

    merged: List[Dict[str, Any]] = []
    seen = set()
    last_err: Optional[str] = None
    per_key_limit = max(8, int(limit))

    for key, value in tag_filters.items():
        q = _overpass_query_one(lat, lon, radius_m, key, value)
        chunk, err = _post_overpass(q, headers)
        if err:
            last_err = err
        for p in chunk:
            if p["poi_id"] in seen:
                continue
            seen.add(p["poi_id"])
            merged.append(p)
            if len(merged) >= per_key_limit:
                break
        if len(merged) >= per_key_limit:
            break

    if not merged:
        return {
            "city_key": city_key,
            "display_name": display_name,
            "lat": lat,
            "lon": lon,
            "pois": [],
            "error": last_err or "No POIs matched interests in this radius.",
        }

    return {
        "city_key": city_key,
        "display_name": display_name,
        "lat": lat,
        "lon": lon,
        "pois": merged[: max(1, min(limit, 200))],
        "error": "",
    }


def check_overpass(user_agent: str) -> Dict[str, Any]:
    """Tiny Overpass query around a known point (Eiffel Tower area)."""
    q = '[out:json][timeout:15];node(around:200,48.8584,2.2945)["tourism"="attraction"];out center 3;'
    headers = {
        "User-Agent": user_agent or "WaypointTripPlanner/1.0 (+https://github.com/Mayank2504/waypoint-trip-planner)",
        "Accept": "*/*",
    }
    last = ""
    for host in OVERPASS_URLS[:2]:
        try:
            r = requests.post(host, data={"data": q}, headers=headers, timeout=20)
            if r.status_code == 200:
                return {"ok": True, "detail": f"{host} ok"}
            last = f"{host} HTTP {r.status_code}"
        except Exception as e:
            last = str(e)
    return {"ok": False, "detail": last or "Overpass failed"}
