"""Tool implementations called by the agent."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from waypoint.cache_utils import cached_fetch_pois
from waypoint.feedback import feedback_boost_map
from waypoint.rag.retrieve import rag_retrieve
from waypoint.ranking import rank_pois


def tool_search_pois(
    city: str,
    interests: List[str],
    radius_km: float,
    limit: int,
    query: str,
    user_agent: str,
) -> Dict[str, Any]:
    data = cached_fetch_pois(
        city=city,
        interests=tuple(interests),
        radius_km=radius_km,
        limit=max(limit, 60),
        user_agent=user_agent,
    )
    city_key = data.get("city_key", city.strip().lower())
    boost = feedback_boost_map(city_key)
    center = {"lat": data.get("lat"), "lon": data.get("lon")}
    pois = rank_pois(
        data.get("pois", []),
        query=query or "",
        boost=boost,
        center=center,
        limit=limit,
    )
    return {
        "city_key": city_key,
        "display_name": data.get("display_name", city),
        "center": center,
        "pois": pois,
        "error": data.get("error", ""),
    }


def tool_retrieve_guides(
    city: str,
    query: str,
    k: int,
    user_agent: str,
    enabled: bool,
) -> Dict[str, Any]:
    if not enabled:
        return {"city": city, "hits": [], "note": "RAG disabled by user."}
    hits = rag_retrieve(city=city, query=query, user_agent=user_agent, k=k)
    return {
        "city": city,
        "hits": hits,
        "note": "If hits empty, proceed with sources=[].",
    }
