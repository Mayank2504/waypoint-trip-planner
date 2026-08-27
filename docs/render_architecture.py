"""Render the factual Waypoint architecture diagram as a PNG."""
from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "AI-trip-planner-architecture-diagram.png"
WIDTH, HEIGHT = 2400, 1350


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


TITLE = font(48, True)
SUBTITLE = font(24)
HEADER = font(25, True)
BOX_TITLE = font(22, True)
BODY = font(18)
FOOTER = font(18)

columns = [
    (
        "1. User and UI",
        "#EAF2FF",
        "#2663A8",
        [
            ("Traveler", "Destination, dates, pace, interests and constraints"),
            ("Streamlit UI", "BYO OpenAI key, trip form, settings and progress"),
            ("Secure key handling", "Password input; session memory only; never persisted"),
        ],
    ),
    (
        "2. Request validation",
        "#EDF8EF",
        "#2D7A45",
        [
            ("Input validation", "City, trip length, radius, dates and constraints"),
            ("Prompt builder", "Plan, whole-trip refine, protected single-day regenerate"),
            ("Actionable errors", "Previous valid itinerary survives every failed request"),
        ],
    ),
    (
        "3. Agent orchestration",
        "#F3EEFF",
        "#6542A6",
        [
            ("Responses API agent", "GPT-4.1-mini with GPT-4o-mini model fallback"),
            ("Bounded agent loop", "Strict tools, maximum steps and total time budget"),
            ("Tool dispatcher", "search_pois and retrieve_guides with exact schemas"),
            ("Execution trace", "Model/tool timings, arguments and provider errors"),
        ],
    ),
    (
        "4. Live providers",
        "#FFF7E7",
        "#A56B13",
        [
            ("Geocoding", "Nominatim with Open-Meteo and Photon fallbacks"),
            ("Live POIs", "Overpass nodes, ways and relations; cached and ranked"),
            ("Travel-guide RAG", "Wikivoyage text, TF-IDF and cosine similarity"),
            ("Walking routes", "FOSSGIS OSRM; one cached multi-stop route per day"),
            ("Daily weather", "Open-Meteo forecast aligned to trip dates"),
        ],
    ),
    (
        "5. Guardrails and state",
        "#EAF8F8",
        "#16747A",
        [
            ("Tool state", "Approved POIs, guide chunks and resolved city center"),
            ("Response validation", "Pydantic schema, day count, POI/source IDs, duplicates"),
            ("Private session state", "Cloud sessions isolated; atomic local JSON only"),
            ("Safe enrichment", "OSRM and weather are optional; straight-path fallback"),
            ("Feedback ranking", "City-scoped +0.25 up / -0.35 down boost"),
        ],
    ),
    (
        "6. User outputs",
        "#EEF4FF",
        "#315D9A",
        [
            ("Itinerary overview", "Day-by-day morning, afternoon and evening cards"),
            ("Interactive map", "POIs, routed paths, tooltips and day filters"),
            ("Trip context", "Walking time, distance and daily weather summaries"),
            ("Refine and feedback", "Whole-trip/day changes, votes and statistics"),
            ("Exports", "Validated itinerary JSON and Unicode-aware PDF"),
        ],
    ),
]


def wrapped(draw: ImageDraw.ImageDraw, text: str, box, text_font, fill, max_chars: int, spacing: int = 5):
    x1, y1, x2, y2 = box
    lines = textwrap.wrap(text, width=max_chars) or [text]
    line_height = text_font.size + spacing
    total = len(lines) * line_height
    y = y1 + max(0, (y2 - y1 - total) / 2)
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=text_font)
        x = x1 + (x2 - x1 - (bbox[2] - bbox[0])) / 2
        draw.text((x, y), line, font=text_font, fill=fill)
        y += line_height


image = Image.new("RGB", (WIDTH, HEIGHT), "white")
draw = ImageDraw.Draw(image)

title = "Waypoint — AI Trip Planner Architecture"
title_box = draw.textbbox((0, 0), title, font=TITLE)
draw.text(((WIDTH - (title_box[2] - title_box[0])) / 2, 28), title, font=TITLE, fill="#14213D")

subtitle = "Agentic itinerary generation with live POIs, RAG, validation, routing, weather, feedback and isolated state"
subtitle_box = draw.textbbox((0, 0), subtitle, font=SUBTITLE)
draw.text(((WIDTH - (subtitle_box[2] - subtitle_box[0])) / 2, 92), subtitle, font=SUBTITLE, fill="#4F5D75")

margin, gap = 24, 24
top, bottom = 150, 1200
column_width = (WIDTH - 2 * margin - 5 * gap) / 6
header_height = 72

column_centers = []
for index, (heading, bg, accent, boxes) in enumerate(columns):
    x1 = margin + index * (column_width + gap)
    x2 = x1 + column_width
    column_centers.append((x1 + x2) / 2)
    draw.rounded_rectangle((x1, top, x2, bottom), radius=18, fill=bg, outline=accent, width=2)
    wrapped(draw, heading, (x1 + 8, top + 4, x2 - 8, top + header_height), HEADER, accent, 24)

    content_top = top + header_height + 10
    available = bottom - content_top - 12
    box_gap = 14
    box_height = (available - box_gap * (len(boxes) - 1)) / len(boxes)
    for box_index, (box_title, description) in enumerate(boxes):
        by1 = content_top + box_index * (box_height + box_gap)
        by2 = by1 + box_height
        draw.rounded_rectangle(
            (x1 + 14, by1, x2 - 14, by2),
            radius=14,
            fill="white",
            outline=accent,
            width=2,
        )
        wrapped(draw, box_title, (x1 + 24, by1 + 8, x2 - 24, by1 + 53), BOX_TITLE, accent, 26)
        wrapped(draw, description, (x1 + 25, by1 + 48, x2 - 25, by2 - 8), BODY, "#263238", 35)

# Primary left-to-right flow.
arrow_y = 128
for left, right in zip(column_centers, column_centers[1:]):
    start = left + column_width / 2 - 8
    end = right - column_width / 2 + 8
    draw.line((start, arrow_y, end - 10, arrow_y), fill="#263238", width=3)
    draw.polygon([(end - 10, arrow_y - 7), (end, arrow_y), (end - 10, arrow_y + 7)], fill="#263238")

footer_y = 1240
draw.rounded_rectangle((margin, footer_y, WIDTH - margin, HEIGHT - 24), radius=14, fill="#F6F8FA", outline="#BCC5D0", width=2)
footer = (
    "Implemented stack: OpenAI Responses API  |  Nominatim + Overpass  |  Wikivoyage TF-IDF RAG  |  "
    "FOSSGIS OSRM  |  Open-Meteo  |  Streamlit + PyDeck  |  JSON/PDF export"
)
wrapped(draw, footer, (margin + 20, footer_y + 8, WIDTH - margin - 20, HEIGHT - 32), FOOTER, "#344054", 155)

image.save(OUTPUT, optimize=True)
print(f"Rendered {OUTPUT} ({WIDTH}x{HEIGHT})")
