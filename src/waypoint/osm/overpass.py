"""Overpass API POI fetching with retries and host fallbacks."""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from waypoint.config import OVERPASS_URLS
from waypoint.http import request_json
from waypoint.osm.geocode import geocode_city
from waypoint.osm.tags import tags_for_interests


def _overpass_query_one(
    lat: float,
    lon: float,
    radius_m: int,
    key: str,
    value: str,
    result_limit: int = 40,
    element_types: Sequence[str] = ("node", "way", "relation"),
) -> str:
    """One bounded category query covering nodes, ways, and relations."""
    radius_m = int(min(max(radius_m, 500), 30_000))
    result_limit = max(5, min(int(result_limit), 60))
    selectors = "".join(
        f'{kind}(around:{radius_m},{lat},{lon})["{key}"~"{value}"]["name"];'
        for kind in element_types
    )
    return f"[out:json][timeout:20];({selectors});out center {result_limit};"


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
                "url": (
                    tags.get("website")
                    or tags.get("url")
                    or f"https://www.openstreetmap.org/{el['type']}/{el['id']}"
                ),
            }
        )
        if len(out) >= max(1, min(limit, 200)):
            break
    return out


def _post_overpass(
    q: str,
    headers: Dict[str, str],
    *,
    deadline: Optional[float] = None,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    last_err: Optional[str] = None
    for host in OVERPASS_URLS:
        try:
            data = request_json(
                "POST",
                host,
                service="Overpass",
                data={"data": q},
                headers=headers,
                timeout=(4, 12),
                attempts=1,
                deadline=deadline,
            )
            pois = _parse_elements(data.get("elements", []) or [], 80)
            # HTTP 200 with zero matches is valid data, not a mirror failure.
            return pois, None
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
            "error": (
                "Could not geocode this city (Nominatim often returns 403). "
                "Try 'City, Country' and a real User-Agent email."
            ),
        }

    lat, lon = geo["lat"], geo["lon"]
    display_name = geo["display_name"]
    city_key = display_name.strip().lower()
    tag_filters = tags_for_interests(list(interests))
    radius_m = int(max(500, min(radius_km, 30) * 1000))

    headers = {
        "User-Agent": user_agent or "WaypointTripPlanner/1.0 (+https://github.com/Mayank2504/waypoint-trip-planner)",
        "Accept": "*/*",
    }

    merged: List[Dict[str, Any]] = []
    seen = set()
    last_err: Optional[str] = None
    category_count = max(1, len(tag_filters))
    per_key_limit = max(5, (int(limit) + category_count - 1) // category_count)
    deadline = time.monotonic() + 45.0

    for key, value in tag_filters.items():
        added = 0
        # Query common nodes first; only query area-like ways/relations if needed.
        for element_types in (("node",), ("way", "relation")):
            if time.monotonic() >= deadline:
                break
            q = _overpass_query_one(
                lat,
                lon,
                radius_m,
                key,
                value,
                per_key_limit - added,
                element_types,
            )
            chunk, err = _post_overpass(q, headers, deadline=deadline)
            if err:
                last_err = err
            else:
                last_err = None
            for p in chunk:
                if p["poi_id"] in seen:
                    continue
                seen.add(p["poi_id"])
                merged.append(p)
                added += 1
                if added >= per_key_limit:
                    break
            if added >= per_key_limit:
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
    mirrors: List[Dict[str, Any]] = []
    for host in OVERPASS_URLS:
        label = host.split("/")[2]
        try:
            data = request_json(
                "POST",
                host,
                service="Overpass",
                data={"data": q},
                headers=headers,
                timeout=(3, 8),
                attempts=1,
            )
            mirrors.append(
                {
                    "host": label,
                    "ok": True,
                    "detail": f"ok ({len(data.get('elements') or [])} result(s))",
                }
            )
        except Exception as e:
            mirrors.append({"host": label, "ok": False, "detail": str(e)})
    healthy = [mirror for mirror in mirrors if mirror["ok"]]
    detail = "; ".join(
        f"{mirror['host']}: {mirror['detail']}" for mirror in mirrors
    )
    return {"ok": bool(healthy), "detail": detail, "mirrors": mirrors}
