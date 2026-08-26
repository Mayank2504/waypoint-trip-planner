"""Pydantic models for itineraries, POIs, and guide chunks."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class BlockItem(BaseModel):
    poi_id: str
    why: str = ""


class SourceRef(BaseModel):
    chunk_id: str = ""
    source: str = ""


class DayPlan(BaseModel):
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


class Itinerary(BaseModel):
    title: str
    city: str
    days: List[DayPlan] = Field(..., min_length=1)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class POI(BaseModel):
    poi_id: str
    name: str
    category: str = "other"
    lat: float
    lon: float
    url: str = ""


class GuideChunk(BaseModel):
    chunk_id: str
    source: str
    text: str
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


def parse_itinerary(data: Any) -> Itinerary:
    if isinstance(data, Itinerary):
        return data
    if isinstance(data, str):
        import json

        data = json.loads(data)
    return Itinerary.model_validate(data)
