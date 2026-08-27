"""Schema and chunking / PDF smoke tests."""
from __future__ import annotations

import pytest

from waypoint.export.pdf import build_itinerary_pdf
from waypoint.rag.retrieve import chunk_text
from waypoint.schemas import Itinerary, parse_itinerary


def test_parse_itinerary():
    data = {
        "title": "Weekend",
        "city": "Santa Fe, NM",
        "days": [
            {
                "day": 1,
                "morning": [{"poi_id": "osm_1", "why": "Iconic"}],
                "afternoon": [],
                "evening": [],
                "notes": "",
                "sources": [],
            }
        ],
    }
    itin = parse_itinerary(data)
    assert isinstance(itin, Itinerary)
    assert itin.days[0].morning[0].poi_id == "osm_1"


def test_schema_rejects_missing_days():
    with pytest.raises(Exception):
        parse_itinerary({"title": "X", "city": "Y"})


def test_schema_rejects_extra_fields_and_blank_ids():
    data = {
        "title": "Trip",
        "city": "City",
        "days": [
            {
                "day": 1,
                "morning": [{"poi_id": "", "why": ""}],
                "afternoon": [],
                "evening": [],
                "notes": "",
                "sources": [],
                "unexpected": True,
            }
        ],
    }
    with pytest.raises(Exception):
        parse_itinerary(data)


def test_schema_rejects_nonsequential_days():
    data = {
        "title": "Trip",
        "city": "City",
        "days": [
            {"day": 2, "morning": [], "afternoon": [], "evening": [], "notes": "", "sources": []}
        ],
    }
    with pytest.raises(Exception):
        parse_itinerary(data)


def test_chunk_respects_max():
    paras = ["Sentence one. " * 20, "Sentence two. " * 20, "Sentence three. " * 20]
    text = "\n\n".join(paras)
    chunks = chunk_text(text, max_chars=400, min_chars=50)
    assert chunks
    assert all(len(c) <= 450 for c in chunks)  # small slack for last merge edge


def test_pdf_bytes():
    itin = {
        "title": "Test Trip",
        "city": "Kyōto",
        "days": [
            {
                "day": 1,
                "morning": [{"poi_id": "p1", "why": "Temple visit"}],
                "afternoon": [{"poi_id": "p2", "why": "Garden"}],
                "evening": [],
                "notes": "Walk slowly",
                "sources": [{"chunk_id": "Kyoto__0", "source": "Kyoto"}],
            }
        ],
    }
    allowed = {
        "p1": {"name": "清水寺", "category": "tourism:attraction", "lat": 35.0, "lon": 135.0},
        "p2": {"name": "Garden", "category": "leisure:garden", "lat": 35.01, "lon": 135.01},
    }
    pdf = build_itinerary_pdf(itin, allowed, pace="relaxed", interests=["history"])
    assert isinstance(pdf, (bytes, bytearray))
    assert len(pdf) > 100
    assert pdf[:4] == b"%PDF"
