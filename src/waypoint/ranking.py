"""POI ranking: interest match, query, feedback boost, distance, tag signals."""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def popularity_heuristic(poi: Dict[str, Any]) -> float:
    """Weak popularity signals from OSM-ish fields already on the POI."""
    score = 0.0
    url = (poi.get("url") or "").strip()
    if url:
        score += 0.15
    cat = (poi.get("category") or "").lower()
    if any(k in cat for k in ("museum", "attraction", "viewpoint", "gallery")):
        score += 0.1
    if "restaurant" in cat or "cafe" in cat:
        score += 0.05
    return score


def score_poi(
    poi: Dict[str, Any],
    *,
    query: str = "",
    boost: Optional[Dict[str, float]] = None,
    center: Optional[Dict[str, Any]] = None,
) -> float:
    boost = boost or {}
    base = popularity_heuristic(poi)
    q = (query or "").strip().lower()
    if q:
        name = (poi.get("name") or "").lower()
        base += 1.0 if q in name else 0.0
    else:
        base += 0.5  # slight preference so sort is stable with boosts

    base += float(boost.get(poi.get("poi_id", ""), 0.0))

    if center and center.get("lat") is not None and center.get("lon") is not None:
        try:
            dist = _haversine_km(
                float(center["lat"]),
                float(center["lon"]),
                float(poi["lat"]),
                float(poi["lon"]),
            )
            # Soft distance penalty within ~15 km
            base -= 0.1 * min(dist / 5.0, 3.0)
        except Exception:
            pass
    return base


def rank_pois(
    pois: List[Dict[str, Any]],
    *,
    query: str = "",
    boost: Optional[Dict[str, float]] = None,
    center: Optional[Dict[str, Any]] = None,
    limit: int = 40,
) -> List[Dict[str, Any]]:
    scored: List[Dict[str, Any]] = []
    for p in pois:
        item = dict(p)
        item["_base_score"] = score_poi(item, query=query, boost=boost, center=center)
        scored.append(item)
    scored.sort(key=lambda x: (x["_base_score"], x.get("name", "")), reverse=True)
    out = scored[: max(1, min(limit, 60))]
    for p in out:
        p.pop("_base_score", None)
    return out
