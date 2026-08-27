from __future__ import annotations

import pytest


@pytest.fixture
def valid_itinerary():
    return {
        "title": "Test Trip",
        "city": "Test City",
        "days": [
            {
                "day": 1,
                "morning": [{"poi_id": "p1", "why": "Start here"}],
                "afternoon": [{"poi_id": "p2", "why": "Continue here"}],
                "evening": [],
                "notes": "",
                "sources": [],
            }
        ],
    }


@pytest.fixture
def allowed_pois():
    return {
        "p1": {"poi_id": "p1", "name": "One", "category": "museum", "lat": 10, "lon": 20, "url": ""},
        "p2": {"poi_id": "p2", "name": "Two", "category": "park", "lat": 10.01, "lon": 20.01, "url": ""},
    }
