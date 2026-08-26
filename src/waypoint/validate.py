"""Itinerary validation helpers."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple


def validate_itinerary_poi_ids(itin: Dict[str, Any], allowed_pois: Dict[str, Any]) -> List[str]:
    valid = set(allowed_pois.keys())
    bad: List[str] = []
    for day in itin.get("days", []) or []:
        for block in ("morning", "afternoon", "evening"):
            for item in day.get(block, []) or []:
                pid = item.get("poi_id")
                if pid and pid not in valid:
                    bad.append(pid)
    return sorted(set(bad))


def find_duplicate_poi_ids(itin: Dict[str, Any]) -> List[str]:
    seen = set()
    dups = set()
    for day in itin.get("days", []) or []:
        for block in ("morning", "afternoon", "evening"):
            for item in day.get(block, []) or []:
                pid = item.get("poi_id")
                if not pid:
                    continue
                if pid in seen:
                    dups.add(pid)
                else:
                    seen.add(pid)
    return sorted(dups)


def other_days_unchanged(
    old_itin: Dict[str, Any],
    new_itin: Dict[str, Any],
    target_day: int,
) -> Tuple[bool, List[int]]:
    old_days = {int(d.get("day")): d for d in (old_itin.get("days") or []) if d.get("day") is not None}
    new_days = {int(d.get("day")): d for d in (new_itin.get("days") or []) if d.get("day") is not None}

    changed: List[int] = []
    for day_num, old_d in old_days.items():
        if day_num == target_day:
            continue
        new_d = new_days.get(day_num)
        if new_d is None:
            changed.append(day_num)
            continue
        if json.dumps(old_d, sort_keys=True) != json.dumps(new_d, sort_keys=True):
            changed.append(day_num)
    return (len(changed) == 0), sorted(changed)


def extract_json_object(text: str) -> Dict[str, Any]:
    """Best-effort extract of a JSON object from model text."""
    if not text or not text.strip():
        raise ValueError("Empty model output.")
    text = text.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model output.")
    return json.loads(text[start : end + 1])


def validate_plan_inputs(city: str, days: int, radius_km: float) -> List[str]:
    errors: List[str] = []
    if not (city or "").strip():
        errors.append("Destination city is required.")
    if days < 1 or days > 7:
        errors.append("Trip length must be between 1 and 7 days.")
    if radius_km < 1 or radius_km > 50:
        errors.append("POI search radius must be between 1 and 50 km.")
    return errors
