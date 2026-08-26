"""Prompt builders for plan / refine / regen."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def _tool_rules(fast_mode: bool, city: str, interests: List[str], radius_km: float, poi_limit: int, rag_k: int) -> str:
    if fast_mode:
        return f"""
Tooling rules (FAST):
- Call search_pois ONCE at the start with:
  city="{city}", interests={interests}, radius_km={radius_km}, limit={poi_limit}, query=""
- Only call search_pois again if you cannot satisfy a specific slot (keep total calls <= 2).
- If RAG is enabled, call retrieve_guides once with a helpful query (k={rag_k}). If disabled or empty, proceed with sources=[].
"""
    return f"""
Tooling rules:
- Call search_pois at least 2 times with different queries (keep total calls <= 4).
  Use city="{city}", interests={interests}, radius_km={radius_km}, limit={poi_limit}.
- If RAG is enabled, call retrieve_guides at least once (k={rag_k}). If disabled or empty, proceed with sources=[].
"""


JSON_SCHEMA_HINT = """
JSON schema (output MUST match):
{
  "title": str,
  "city": str,
  "days": [
    {
      "day": int,
      "morning": [{"poi_id": str, "why": str}],
      "afternoon": [{"poi_id": str, "why": str}],
      "evening": [{"poi_id": str, "why": str}],
      "notes": str,
      "sources": [{"chunk_id": str, "source": str}]
    }
  ]
}
"""


def plan_prompt(
    *,
    city: str,
    days: int,
    pace: str,
    interests: List[str],
    constraints: str,
    notes: str,
    radius_km: float,
    fast_mode: bool,
    poi_limit: int,
    rag_k: int = 4,
) -> str:
    return f"""
You are Waypoint, a careful trip-planning assistant.

Create a {days}-day itinerary for: {city}
Pace: {pace}
Interests: {interests}
Constraints: {constraints}
Notes: {notes}

Hard rules:
1) You MUST ONLY use POIs returned by search_pois, referencing them by poi_id.
2) Prefer geographic coherence within each day (cluster nearby places).
3) Avoid repeating the same poi_id across the trip.
4) Output MUST be valid JSON only (no markdown fences, no commentary).
5) Keep each block (morning/afternoon/evening) to 1–2 items. Keep "why" concise.

{_tool_rules(fast_mode, city, interests, radius_km, poi_limit, rag_k)}

{JSON_SCHEMA_HINT}
""".strip()


def refine_prompt(
    *,
    itin: Dict[str, Any],
    request: str,
    fast_mode: bool,
) -> str:
    city = itin.get("city", "")
    calls = "<= 2" if fast_mode else "<= 4"
    return f"""
You will edit an existing itinerary JSON for: {city}.

Hard rules:
- Keep the same JSON schema.
- You MUST ONLY use poi_id values obtained via search_pois.
- If you need alternatives, call search_pois (keep total calls {calls}).
- If RAG enabled, you may call retrieve_guides once; if empty/disabled, sources=[] is fine.
- Avoid duplicate poi_ids across the trip.
- Output JSON only.

Refinement request: {request}

Existing JSON:
{json.dumps(itin, ensure_ascii=False)}
""".strip()


def regen_day_prompt(
    *,
    itin: Dict[str, Any],
    target_day: int,
    request: str,
    fast_mode: bool,
) -> str:
    city = itin.get("city", "")
    calls = "<= 2" if fast_mode else "<= 4"
    return f"""
You will edit an existing itinerary JSON for: {city}.

Goal: ONLY modify the content of day == {target_day}. All other days must remain EXACTLY unchanged.
If you need alternatives, call search_pois (keep total calls {calls}).
If RAG enabled, you may call retrieve_guides once; if empty/disabled, sources=[] is fine.

Hard rules:
- Keep the same JSON schema.
- You MUST ONLY use poi_id values obtained via search_pois.
- Output JSON only.

Day-specific request: {request}

Existing JSON:
{json.dumps(itin, ensure_ascii=False)}
""".strip()
