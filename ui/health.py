"""API health checks UI."""
from __future__ import annotations

import streamlit as st

from waypoint.osm.geocode import check_nominatim
from waypoint.osm.overpass import check_overpass
from waypoint.rag.wikivoyage import check_wikivoyage


def render_health_panel(user_agent: str) -> None:
    st.subheader("API health")
    results = st.session_state.setdefault("_health_results", {})
    c1, c2, c3 = st.columns(3)
    if c1.button("Nominatim"):
        with st.spinner("Checking Nominatim…"):
            results["Nominatim"] = check_nominatim(user_agent)
    if c2.button("Overpass"):
        with st.spinner("Checking Overpass…"):
            results["Overpass"] = check_overpass(user_agent)
    if c3.button("Wikivoyage"):
        with st.spinner("Checking Wikivoyage…"):
            results["Wikivoyage"] = check_wikivoyage(user_agent)

    for service in ("Nominatim", "Overpass", "Wikivoyage"):
        result = results.get(service)
        if not result:
            continue
        if result["ok"]:
            st.success(f"{service}: {result['detail']}")
        elif service == "Wikivoyage":
            st.warning(f"{service}: {result['detail']} — keep RAG off if blocked.")
        else:
            st.error(f"{service}: {result['detail']}")
