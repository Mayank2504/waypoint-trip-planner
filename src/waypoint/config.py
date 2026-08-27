"""Waypoint trip planner — shared configuration."""
from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
APP_STATE_PATH = DATA_DIR / "app_state.json"
FEEDBACK_PATH = DATA_DIR / "feedback.jsonl"
ASSETS_DIR = ROOT_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.osm.ch/api/interpreter",
]
WIKIVOYAGE_API = "https://en.wikivoyage.org/w/api.php"

DEFAULT_MODEL = "gpt-4.1-mini"
MAX_TOOL_STEPS_FAST = 5
MAX_TOOL_STEPS_FULL = 8
POI_LIMIT_FAST = 40
POI_LIMIT_FULL = 30

UPVOTE_BOOST = 0.25
DOWNVOTE_BOOST = 0.35

MAP_STYLE_LIGHT = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
MAP_STYLE_DARK = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"

PLACEHOLDER_EMAILS = {
    "your-email@example.com",
    "you@example.com",
    "email@example.com",
    "contact@example.com",
}

APP_NAME = "Waypoint"
APP_VERSION = "1.0"
USER_AGENT_TEMPLATE = "waypoint-trip-planner/{version} (contact: {email})"
