"""Itinerary rendering helpers."""
from __future__ import annotations

from typing import Any, Dict

import streamlit as st


def format_poi(pid: str, allowed: Dict[str, Any]) -> str:
    p = allowed.get(pid) or {}
    name = p.get("name") or pid
    cat = p.get("category") or ""
    return f"{name} ({cat})" if cat else name


def render_itinerary(itin: Dict[str, Any], allowed: Dict[str, Any]) -> None:
    st.subheader(itin.get("title") or "Itinerary")
    st.caption(itin.get("city", ""))

    for day in itin.get("days", []) or []:
        dnum = day.get("day")
        st.markdown(f"### Day {dnum}")
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
