"""PyDeck map for itinerary POIs and day paths."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pydeck as pdk
import streamlit as st

from waypoint.config import MAP_STYLE_DARK, MAP_STYLE_LIGHT

DAY_COLORS = [
    [11, 110, 79, 200],
    [0, 120, 255, 200],
    [230, 126, 34, 200],
    [155, 89, 182, 200],
    [231, 76, 60, 200],
    [52, 152, 219, 200],
    [46, 204, 113, 200],
]


def itinerary_points(
    itin: Dict[str, Any],
    allowed: Dict[str, Any],
    day_filter: Optional[int] = None,
) -> List[Dict[str, Any]]:
    pts: List[Dict[str, Any]] = []
    for day in itin.get("days", []) or []:
        dnum = int(day.get("day", -1))
        if day_filter is not None and dnum != day_filter:
            continue
        color = DAY_COLORS[(dnum - 1) % len(DAY_COLORS)]
        for block in ("morning", "afternoon", "evening"):
            for item in day.get(block, []) or []:
                pid = item.get("poi_id")
                if not pid:
                    continue
                p = allowed.get(pid)
                if not p:
                    continue
                try:
                    lat, lon = float(p["lat"]), float(p["lon"])
                except Exception:
                    continue
                pts.append(
                    {
                        "day": dnum,
                        "block": block,
                        "poi_id": pid,
                        "name": p.get("name", pid),
                        "category": p.get("category", ""),
                        "lat": lat,
                        "lon": lon,
                        "color": color,
                    }
                )
    return pts


def itinerary_paths(
    itin: Dict[str, Any],
    allowed: Dict[str, Any],
    day_filter: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Connect ALL stops in temporal order (morning→afternoon→evening items)."""
    out: List[Dict[str, Any]] = []
    for day in itin.get("days", []) or []:
        dnum = int(day.get("day", -1))
        if day_filter is not None and dnum != day_filter:
            continue
        coords: List[List[float]] = []
        for block in ("morning", "afternoon", "evening"):
            for item in day.get(block, []) or []:
                pid = item.get("poi_id")
                p = allowed.get(pid) if pid else None
                if p and p.get("lat") is not None and p.get("lon") is not None:
                    coords.append([float(p["lon"]), float(p["lat"])])
        if len(coords) >= 2:
            color = DAY_COLORS[(dnum - 1) % len(DAY_COLORS)]
            out.append({"day": dnum, "path": coords, "color": color})
    return out


def _approx_zoom(points: List[Dict[str, Any]]) -> int:
    lats = [p["lat"] for p in points]
    lons = [p["lon"] for p in points]
    span = max(max(lats) - min(lats), max(lons) - min(lons))
    if span < 0.01:
        return 14
    if span < 0.03:
        return 13
    if span < 0.08:
        return 12
    if span < 0.18:
        return 11
    if span < 0.35:
        return 10
    return 9


def render_map(
    points: List[Dict[str, Any]],
    paths: List[Dict[str, Any]],
    center: Dict[str, Any],
    dark: bool,
) -> None:
    if not points:
        st.info("No mappable POIs yet.")
        return

    clat = center.get("lat")
    clon = center.get("lon")
    if clat is None or clon is None:
        clat = float(np.mean([p["lat"] for p in points]))
        clon = float(np.mean([p["lon"] for p in points]))

    zoom = _approx_zoom(points)
    view_state = pdk.ViewState(latitude=float(clat), longitude=float(clon), zoom=zoom, pitch=0)

    point_layer = pdk.Layer(
        "ScatterplotLayer",
        data=points,
        get_position="[lon, lat]",
        get_radius=35,
        radius_min_pixels=3,
        radius_max_pixels=10,
        get_fill_color="color",
        get_line_color=[255, 255, 255, 220],
        line_width_min_pixels=1,
        pickable=True,
    )
    layers = [point_layer]
    if paths:
        layers.append(
            pdk.Layer(
                "PathLayer",
                data=paths,
                get_path="path",
                get_color="color",
                width_min_pixels=2,
                width_max_pixels=4,
                pickable=False,
            )
        )

    deck = pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        tooltip={"text": "{name}\nDay {day} • {block}\n{category}\n{poi_id}"},
        map_style=(MAP_STYLE_DARK if dark else MAP_STYLE_LIGHT),
    )
    st.pydeck_chart(deck, use_container_width=True)
    st.caption("Map data © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors")
