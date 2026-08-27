"""Optional Streamlit cache wrappers around OSM / RAG fetchers."""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

try:
    import streamlit as st

    @st.cache_data(ttl=24 * 3600, show_spinner=False)
    def cached_geocode(city: str, user_agent: str) -> Optional[Dict[str, Any]]:
        from waypoint.osm.geocode import geocode_city

        return geocode_city(city, user_agent)

    @st.cache_data(ttl=6 * 3600, show_spinner=False)
    def _cached_fetch_pois_ok(
        city: str,
        interests: Tuple[str, ...],
        radius_km: float,
        limit: int,
        user_agent: str,
    ) -> Dict[str, Any]:
        from waypoint.osm.overpass import fetch_pois

        data = fetch_pois(city, interests, radius_km, limit, user_agent)
        if not data.get("pois"):
            # Do not cache empty/error responses — Overpass/Nominatim flakes are common.
            raise RuntimeError(data.get("error") or "No POIs returned")
        return data

    def cached_fetch_pois(
        city: str,
        interests: Tuple[str, ...],
        radius_km: float,
        limit: int,
        user_agent: str,
    ) -> Dict[str, Any]:
        try:
            return _cached_fetch_pois_ok(city, interests, radius_km, limit, user_agent)
        except Exception:
            from waypoint.osm.overpass import fetch_pois

            return fetch_pois(city, interests, radius_km, limit, user_agent)

    @st.cache_data(ttl=7 * 24 * 3600, show_spinner=False)
    def cached_wikivoyage_text(city: str, user_agent: str) -> Dict[str, str]:
        from waypoint.rag.wikivoyage import wikivoyage_plaintext, wikivoyage_resolve_title

        title = wikivoyage_resolve_title(city, user_agent) or ""
        text = wikivoyage_plaintext(title, user_agent) if title else ""
        return {"title": title, "text": text}

except Exception:  # pragma: no cover - non-Streamlit contexts
    def cached_geocode(city: str, user_agent: str) -> Optional[Dict[str, Any]]:
        from waypoint.osm.geocode import geocode_city

        return geocode_city(city, user_agent)

    def cached_fetch_pois(
        city: str,
        interests: Tuple[str, ...],
        radius_km: float,
        limit: int,
        user_agent: str,
    ) -> Dict[str, Any]:
        from waypoint.osm.overpass import fetch_pois

        return fetch_pois(city, interests, radius_km, limit, user_agent)

    def cached_wikivoyage_text(city: str, user_agent: str) -> Dict[str, str]:
        from waypoint.rag.wikivoyage import wikivoyage_plaintext, wikivoyage_resolve_title

        title = wikivoyage_resolve_title(city, user_agent) or ""
        text = wikivoyage_plaintext(title, user_agent) if title else ""
        return {"title": title, "text": text}
