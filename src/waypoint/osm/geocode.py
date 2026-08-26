"""Nominatim geocoding."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from waypoint.config import NOMINATIM_URL
from waypoint.rate_limit import nominatim_limiter


def build_user_agent(email: str, version: str = "1.0") -> str:
    contact = (email or "").strip() or "unknown"
    return f"waypoint-trip-planner/{version} (contact: {contact})"


def geocode_city(city: str, user_agent: str, *, limit: int = 1) -> Optional[Dict[str, Any]]:
    """Geocode a city via Nominatim. Returns top result or None."""
    results = geocode_city_candidates(city, user_agent, limit=limit)
    return results[0] if results else None


def geocode_city_candidates(city: str, user_agent: str, *, limit: int = 5) -> List[Dict[str, Any]]:
    headers = {"User-Agent": user_agent or "waypoint-trip-planner/1.0 (contact: unknown)"}
    params = {"q": city, "format": "json", "limit": max(1, min(limit, 5))}
    nominatim_limiter.wait()
    r = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=20)
    r.raise_for_status()
    data = r.json()
    if not data:
        return []
    out: List[Dict[str, Any]] = []
    for top in data:
        out.append(
            {
                "lat": float(top["lat"]),
                "lon": float(top["lon"]),
                "display_name": top.get("display_name", city),
            }
        )
    return out


def check_nominatim(user_agent: str) -> Dict[str, Any]:
    try:
        geo = geocode_city("Paris, France", user_agent)
        if not geo:
            return {"ok": False, "detail": "No geocode result"}
        return {"ok": True, "detail": geo.get("display_name", "ok")}
    except Exception as e:
        return {"ok": False, "detail": str(e)}
