"""Geocoding with Nominatim plus public fallbacks (403 is common)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from waypoint.config import NOMINATIM_URL, PLACEHOLDER_EMAILS
from waypoint.http import request_json
from waypoint.rate_limit import nominatim_limiter

GITHUB_HOME = "https://github.com/Mayank2504/waypoint-trip-planner"


def build_user_agent(email: str, version: str = "1.0") -> str:
    """Public OSM endpoints 403/406 generic 'example.com' User-Agents."""
    contact = (email or "").strip()
    if not contact or contact.lower() in PLACEHOLDER_EMAILS:
        contact = GITHUB_HOME
    return f"WaypointTripPlanner/{version} (+{GITHUB_HOME}; {contact})"


def _nominatim_headers(user_agent: str) -> Dict[str, str]:
    return {
        "User-Agent": user_agent or f"WaypointTripPlanner/1.0 (+{GITHUB_HOME})",
        "Accept": "application/json",
        "Accept-Language": "en",
        "Referer": GITHUB_HOME,
    }


def geocode_city(city: str, user_agent: str, *, limit: int = 1) -> Optional[Dict[str, Any]]:
    """Geocode a city. Returns top result or None (never raises on 403/empty)."""
    results = geocode_city_candidates(city, user_agent, limit=limit)
    return results[0] if results else None


def geocode_city_candidates(city: str, user_agent: str, *, limit: int = 5) -> List[Dict[str, Any]]:
    q = (city or "").strip()
    if not q:
        return []
    errors: List[str] = []
    for fn in (_geocode_nominatim, _geocode_open_meteo, _geocode_photon):
        try:
            hits = fn(q, user_agent, limit=limit)
            if hits:
                return hits
        except Exception as e:
            errors.append(f"{fn.__name__}: {e}")
            continue
    return []


def _geocode_nominatim(city: str, user_agent: str, *, limit: int) -> List[Dict[str, Any]]:
    headers = _nominatim_headers(user_agent)
    params = {"q": city, "format": "json", "limit": max(1, min(limit, 5))}
    nominatim_limiter.wait()
    data = request_json(
        "GET",
        NOMINATIM_URL,
        service="Nominatim",
        params=params,
        headers=headers,
        timeout=(5, 20),
        attempts=2,
    )
    if not data:
        return []
    return [
        {
            "lat": float(top["lat"]),
            "lon": float(top["lon"]),
            "display_name": top.get("display_name", city),
        }
        for top in data
    ]


def _geocode_open_meteo(city: str, user_agent: str, *, limit: int) -> List[Dict[str, Any]]:
    """Fallback: Open-Meteo geocoding (no OSM Nominatim User-Agent policy)."""
    payload = request_json(
        "GET",
        "https://geocoding-api.open-meteo.com/v1/search",
        service="Open-Meteo geocoding",
        params={"name": city, "count": max(1, min(limit, 5)), "language": "en", "format": "json"},
        headers=_nominatim_headers(user_agent),
        timeout=(5, 20),
        attempts=2,
    )
    results = payload.get("results") or []
    out: List[Dict[str, Any]] = []
    for top in results:
        name = top.get("name") or city
        admin = top.get("admin1") or ""
        country = top.get("country") or ""
        display = ", ".join(p for p in (name, admin, country) if p)
        out.append({"lat": float(top["latitude"]), "lon": float(top["longitude"]), "display_name": display})
    return out


def _geocode_photon(city: str, user_agent: str, *, limit: int) -> List[Dict[str, Any]]:
    """Fallback: Komoot Photon."""
    payload = request_json(
        "GET",
        "https://photon.komoot.io/api/",
        service="Photon geocoding",
        params={"q": city, "limit": max(1, min(limit, 5))},
        headers=_nominatim_headers(user_agent),
        timeout=(5, 20),
        attempts=2,
    )
    features = payload.get("features") or []
    out: List[Dict[str, Any]] = []
    for feat in features:
        coords = (feat.get("geometry") or {}).get("coordinates") or []
        if len(coords) < 2:
            continue
        lon, lat = float(coords[0]), float(coords[1])
        props = feat.get("properties") or {}
        display = props.get("name") or city
        extra = ", ".join(
            p for p in (props.get("city"), props.get("state"), props.get("country")) if p
        )
        if extra:
            display = f"{display}, {extra}" if display.lower() not in extra.lower() else extra
        out.append({"lat": lat, "lon": lon, "display_name": display})
    return out


def check_nominatim(user_agent: str) -> Dict[str, Any]:
    try:
        results = _geocode_nominatim("Paris, France", user_agent, limit=1)
        if not results:
            return {"ok": False, "detail": "Nominatim returned no geocode result"}
        return {"ok": True, "detail": results[0].get("display_name", "Nominatim ok")}
    except Exception as e:
        return {"ok": False, "detail": str(e)}
