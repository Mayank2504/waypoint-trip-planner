"""Overpass API POI fetching with retries and host fallbacks."""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

import requests

from waypoint.config import OVERPASS_URLS
from waypoint.osm.geocode import geocode_city
from waypoint.osm.tags import tags_for_interests


def _overpass_query(lat: float, lon: float, radius_m: int, tag_filters: Dict[str, str]) -> str:
    parts: List[str] = []
    for k, v in tag_filters.items():
        parts.append(f'node(around:{radius_m},{lat},{lon})["{k}"~"{v}"];')
        parts.append(f'way(around:{radius_m},{lat},{lon})["{k}"~"{v}"];')
        parts.append(f'relation(around:{radius_m},{lat},{lon})["{k}"~"{v}"];')
    body = "\n".join(parts)
    return f"""
[out:json][timeout:35];
(
{body}
);
out center tags;
"""


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


def fetch_pois(
    city: str,
    interests: Tuple[str, ...],
    radius_km: float,
    limit: int,
    user_agent: str,
) -> Dict[str, Any]:
    # Prefer cached geocode when Streamlit is available
    try:
        from waypoint.cache_utils import cached_geocode

        geo = cached_geocode(city, user_agent)
    except Exception:
        geo = geocode_city(city, user_agent=user_agent)
    if not geo:
        return {
            "city_key": city.strip().lower(),
            "display_name": city,
            "lat": None,
            "lon": None,
            "pois": [],
            "error": "No geocode result. Try 'City, Country'.",
        }

    lat, lon = geo["lat"], geo["lon"]
    display_name = geo["display_name"]
    city_key = display_name.strip().lower()
    tag_filters = tags_for_interests(list(interests))
    radius_m = int(max(500, radius_km * 1000))
    q = _overpass_query(lat, lon, radius_m, tag_filters)

    headers = {"User-Agent": user_agent or "waypoint-trip-planner/1.0 (contact: unknown)"}
    last_err: Optional[Exception] = None

    for host in OVERPASS_URLS:
        for attempt in range(3):
            try:
                r = requests.post(host, data={"data": q}, headers=headers, timeout=30)
                if r.status_code == 429:
                    time.sleep(1.5 * (2**attempt))
                    continue
                if r.status_code >= 500:
                    time.sleep(1.0 * (2**attempt))
                    continue
                r.raise_for_status()
                data = r.json()
                pois = _parse_elements(data.get("elements", []) or [], limit)
                return {
                    "city_key": city_key,
                    "display_name": display_name,
                    "lat": lat,
                    "lon": lon,
                    "pois": pois,
                    "error": "" if pois else "No POIs matched interests in this radius.",
                }
            except Exception as e:
                last_err = e
                time.sleep(1.0 * (2**attempt))
        # try next host

    return {
        "city_key": city_key,
        "display_name": display_name,
        "lat": lat,
        "lon": lon,
        "pois": [],
        "error": str(last_err) if last_err else "Overpass unavailable",
    }


def check_overpass(user_agent: str) -> Dict[str, Any]:
    """Tiny Overpass query around a known point (Eiffel Tower area)."""
    q = """
[out:json][timeout:15];
node(around:200,48.8584,2.2945)["tourism"="attraction"];
out center tags 3;
"""
    headers = {"User-Agent": user_agent or "waypoint-trip-planner/1.0 (contact: unknown)"}
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
