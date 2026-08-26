"""Strict OpenAI tool schemas for Responses API."""
from __future__ import annotations

from typing import Any, Dict, List

TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "name": "search_pois",
        "description": (
            "Find POIs near a city using OpenStreetMap. "
            "Returns poi_id, name, category, lat/lon, url. "
            "You MUST use only these poi_id values in the itinerary."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string"},
                "interests": {"type": "array", "items": {"type": "string"}},
                "radius_km": {"type": "number", "minimum": 1, "maximum": 50},
                "limit": {"type": "integer", "minimum": 1, "maximum": 60},
                "query": {"type": "string"},
            },
            "required": ["city", "interests", "radius_km", "limit", "query"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "retrieve_guides",
        "description": (
            "Retrieve relevant Wikivoyage snippets for the city (RAG). "
            "Returns chunk_id, source, text, score. If empty, proceed with sources=[]."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string"},
                "query": {"type": "string"},
                "k": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": ["city", "query", "k"],
            "additionalProperties": False,
        },
    },
]
