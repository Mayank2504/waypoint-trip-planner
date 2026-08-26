"""API health checks UI."""
from __future__ import annotations

import streamlit as st

from waypoint.osm.geocode import check_nominatim
from waypoint.osm.overpass import check_overpass
from waypoint.rag.wikivoyage import check_wikivoyage


def render_health_panel(user_agent: str) -> None:
    st.subheader("API health")
    c1, c2, c3 = st.columns(3)
    if c1.button("Nominatim"):
        with st.spinner("Checking Nominatim…"):
            r = check_nominatim(user_agent)
        (st.success if r["ok"] else st.error)(f"Nominatim: {r['detail']}")
    if c2.button("Overpass"):
        with st.spinner("Checking Overpass…"):
            r = check_overpass(user_agent)
        (st.success if r["ok"] else st.error)(f"Overpass: {r['detail']}")
    if c3.button("Wikivoyage"):
        with st.spinner("Checking Wikivoyage…"):
            r = check_wikivoyage(user_agent)
        if r["ok"]:
            st.success(f"Wikivoyage: {r['detail']}")
        else:
            st.warning(f"Wikivoyage: {r['detail']} — keep RAG off if blocked.")
