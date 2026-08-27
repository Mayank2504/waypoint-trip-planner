"""Pydantic models for itineraries, POIs, and guide chunks."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class BlockItem(StrictModel):
    poi_id: str = Field(min_length=1)
    why: str = ""


class SourceRef(StrictModel):
    chunk_id: str = ""
    source: str = ""


class DayPlan(StrictModel):
    day: int
    morning: List[BlockItem] = Field(default_factory=list)
    afternoon: List[BlockItem] = Field(default_factory=list)
    evening: List[BlockItem] = Field(default_factory=list)
    notes: str = ""
    sources: List[SourceRef] = Field(default_factory=list)

    @field_validator("morning", "afternoon", "evening", mode="before")
    @classmethod
    def _coerce_items(cls, v: Any) -> Any:
        if v is None:
            return []
        return v


class Itinerary(StrictModel):
    title: str = Field(min_length=1)
    city: str = Field(min_length=1)
    days: List[DayPlan] = Field(..., min_length=1)

    @field_validator("days")
    @classmethod
    def _unique_ordered_days(cls, days: List[DayPlan]) -> List[DayPlan]:
        numbers = [day.day for day in days]
        if len(numbers) != len(set(numbers)):
            raise ValueError("Day numbers must be unique.")
        if numbers != list(range(1, len(numbers) + 1)):
            raise ValueError("Day numbers must be ordered and start at 1.")
        return days

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class POI(StrictModel):
    poi_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    category: str = "other"
    lat: float
    lon: float
    url: str = ""


class GuideChunk(StrictModel):
    chunk_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    text: str = Field(min_length=1)
    score: float = 0.0


ITINERARY_JSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["title", "city", "days"],
    "properties": {
        "title": {"type": "string"},
        "city": {"type": "string"},
        "days": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["day", "morning", "afternoon", "evening", "notes", "sources"],
                "properties": {
                    "day": {"type": "integer"},
                    "morning": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["poi_id", "why"],
                            "properties": {
                                "poi_id": {"type": "string"},
                                "why": {"type": "string"},
                            },
                        },
                    },
                    "afternoon": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["poi_id", "why"],
                            "properties": {
                                "poi_id": {"type": "string"},
                                "why": {"type": "string"},
                            },
                        },
                    },
                    "evening": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["poi_id", "why"],
                            "properties": {
                                "poi_id": {"type": "string"},
                                "why": {"type": "string"},
                            },
                        },
                    },
                    "notes": {"type": "string"},
                    "sources": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["chunk_id", "source"],
                            "properties": {
                                "chunk_id": {"type": "string"},
                                "source": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
    },
}


def constrained_itinerary_schema(
    poi_ids: Optional[List[str]] = None,
    chunk_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Return a per-run schema restricted to IDs actually returned by tools."""
    schema = deepcopy(ITINERARY_JSON_SCHEMA)
    day_properties = schema["properties"]["days"]["items"]["properties"]

    approved_pois = sorted({poi_id for poi_id in (poi_ids or []) if poi_id})
    if approved_pois:
        for block in ("morning", "afternoon", "evening"):
            day_properties[block]["items"]["properties"]["poi_id"]["enum"] = approved_pois

    approved_chunks = sorted({chunk_id for chunk_id in (chunk_ids or []) if chunk_id})
    if approved_chunks:
        day_properties["sources"]["items"]["properties"]["chunk_id"]["enum"] = approved_chunks
    return schema


def parse_itinerary(data: Any) -> Itinerary:
    if isinstance(data, Itinerary):
        return data
    if isinstance(data, str):
        import json

        data = json.loads(data)
    return Itinerary.model_validate(data)
