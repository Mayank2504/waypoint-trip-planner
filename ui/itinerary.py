"""Itinerary rendering helpers."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, Optional

import streamlit as st


def format_poi(pid: str, allowed: Dict[str, Any]) -> str:
    p = allowed.get(pid) or {}
    name = p.get("name") or pid
    cat = p.get("category") or ""
    return f"{name} ({cat})" if cat else name


def render_itinerary(
    itin: Dict[str, Any],
    allowed: Dict[str, Any],
    routes: Optional[Dict[int, Dict[str, Any]]] = None,
    weather: Optional[Dict[str, Dict[str, Any]]] = None,
    start_date: Optional[str] = None,
) -> None:
    st.subheader(itin.get("title") or "Itinerary")
    st.caption(itin.get("city", ""))

    for day in itin.get("days", []) or []:
        dnum = day.get("day")
        st.markdown(f"### Day {dnum}")
        if weather and start_date:
            forecast_date = date.fromisoformat(start_date) + timedelta(days=int(dnum) - 1)
            forecast = (weather.get("by_date") or {}).get(forecast_date.isoformat()) or {}
            if forecast.get("available"):
                temp_unit = forecast.get("temperature_unit", "°C")
                precipitation = forecast.get("precipitation_probability")
                precipitation_text = (
                    f" · Rain {precipitation}%"
                    if precipitation is not None
                    else ""
                )
                st.caption(
                    f"{forecast_date.strftime('%a, %d %b')} · {forecast.get('label')} · "
                    f"{forecast.get('temperature_min')}–{forecast.get('temperature_max')}{temp_unit}"
                    f"{precipitation_text}"
                )
            else:
                st.caption(f"{forecast_date.strftime('%a, %d %b')} · Forecast not available yet")
        cols = st.columns(3)
        for i, block in enumerate(("morning", "afternoon", "evening")):
            with cols[i]:
                st.markdown(f"**{block.title()}**")
                items = day.get(block, []) or []
                if not items:
                    st.caption("—")
                for item in items[:4]:
                    pid = item.get("poi_id", "")
                    why = (item.get("why") or "").strip()
                    st.markdown(f"- **{format_poi(pid, allowed)}**  \n  {why}")

        notes = (day.get("notes") or "").strip()
        if notes:
            st.caption(notes)

        route = (routes or {}).get(int(dnum))
        if route and not route.get("error") and route.get("legs"):
            st.caption(
                f"Walking: {route.get('distance_km', 0):.1f} km · "
                f"about {route.get('duration_min', 0)} min"
            )
            with st.expander(f"Walking legs — Day {dnum}", expanded=False):
                for leg in route["legs"]:
                    st.markdown(
                        f"- **{leg['from_name']} → {leg['to_name']}**: "
                        f"{leg['distance_km']:.1f} km, about {leg['duration_min']} min"
                    )
        elif route and route.get("error"):
            st.caption("Walking route unavailable; the map uses straight-line connections.")

        sources = day.get("sources") or []
        if sources:
            with st.expander(f"Sources (RAG) — Day {dnum}", expanded=False):
                for s in sources[:6]:
                    st.markdown(f"- `{s.get('chunk_id', '')}` — **{s.get('source', '')}**")


def render_before_after(prev: Dict[str, Any], curr: Dict[str, Any]) -> None:
    with st.expander("Before / after comparison", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Before**")
            st.json(prev)
        with c2:
            st.markdown("**After**")
            st.json(curr)
