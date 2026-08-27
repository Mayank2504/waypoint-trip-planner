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
        if service == "Overpass" and result.get("mirrors"):
            mirrors = result["mirrors"]
            healthy = sum(1 for mirror in mirrors if mirror["ok"])
            if healthy:
                st.success(f"Overpass: {healthy}/{len(mirrors)} mirrors available")
            else:
                st.error("Overpass: no configured mirror is currently available")
            with st.expander("Overpass mirror details", expanded=False):
                for mirror in mirrors:
                    state = "available" if mirror["ok"] else "unavailable"
                    st.caption(f"{mirror['host']}: {state} — {mirror['detail']}")
            continue
        if result["ok"]:
            st.success(f"{service}: {result['detail']}")
        elif service == "Wikivoyage":
            st.warning(f"{service}: {result['detail']} — keep RAG off if blocked.")
        else:
            st.error(f"{service}: {result['detail']}")
