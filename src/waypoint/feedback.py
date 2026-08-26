"""Feedback JSONL storage and per-city POI boosts."""
from __future__ import annotations

import json
import time
from collections import Counter
from typing import Any, Dict, List, Optional

from waypoint.config import DOWNVOTE_BOOST, FEEDBACK_PATH, UPVOTE_BOOST
from waypoint.persistence import ensure_data_dir


def append_feedback(event: Dict[str, Any]) -> None:
    ensure_data_dir()
    payload = dict(event)
    payload.setdefault("ts", time.time())
    with FEEDBACK_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _iter_events() -> List[Dict[str, Any]]:
    if not FEEDBACK_PATH.exists():
        return []
    events: List[Dict[str, Any]] = []
    for line in FEEDBACK_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except Exception:
            continue
        if isinstance(e, dict):
            events.append(e)
    return events


def feedback_boost_map(city_key: str) -> Dict[str, float]:
    """+UPVOTE_BOOST per upvote, -DOWNVOTE_BOOST per downvote for this city."""
    pos: Dict[str, int] = {}
    neg: Dict[str, int] = {}
    key = (city_key or "").strip().lower()
    for e in _iter_events():
        if (e.get("city_key") or "").strip().lower() != key:
            continue
        poi_id = e.get("poi_id")
        if not poi_id:
            continue
        if e.get("vote") == "up":
            pos[poi_id] = pos.get(poi_id, 0) + 1
        elif e.get("vote") == "down":
            neg[poi_id] = neg.get(poi_id, 0) + 1

    boost: Dict[str, float] = {}
    for poi_id in set(pos) | set(neg):
        boost[poi_id] = UPVOTE_BOOST * pos.get(poi_id, 0) - DOWNVOTE_BOOST * neg.get(poi_id, 0)
    return boost


def feedback_stats(city_key: Optional[str] = None) -> Dict[str, Any]:
    events = _iter_events()
    if city_key:
        key = city_key.strip().lower()
        events = [e for e in events if (e.get("city_key") or "").strip().lower() == key]

    ups = sum(1 for e in events if e.get("vote") == "up")
    downs = sum(1 for e in events if e.get("vote") == "down")
    by_poi = Counter(e.get("poi_id") for e in events if e.get("poi_id"))
    top = by_poi.most_common(8)
    recent = events[-10:][::-1]
    return {
        "total": len(events),
        "ups": ups,
        "downs": downs,
        "top_pois": top,
        "recent": recent,
    }
