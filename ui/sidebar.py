"""Sidebar settings for Waypoint."""
from __future__ import annotations

import os
from typing import Any, Dict

import streamlit as st

from ui.health import render_health_panel
from waypoint.config import (
    DEFAULT_MODEL,
    MAX_TOOL_STEPS_FAST,
    MAX_TOOL_STEPS_FULL,
    PLACEHOLDER_EMAILS,
)
from waypoint.osm.geocode import build_user_agent
from waypoint.persistence import clear_app_state_file, is_cloud_runtime, save_app_state


def render_sidebar() -> Dict[str, Any]:
    with st.sidebar:
        st.header("Settings")

        st.subheader("OpenAI (BYO key)")
        env_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
        if env_key and not st.session_state.get("user_openai_key"):
            st.session_state["user_openai_key"] = env_key
            st.caption("Loaded key from OPENAI_API_KEY env.")

        st.text_input(
            "OpenAI API key",
            type="password",
            key="user_openai_key",
            help="Starts with sk-… Stored only in this session's memory.",
        )
        st.checkbox("Remember for this session", value=True, key="remember_key")
        if st.button("Clear key"):
            st.session_state["user_openai_key"] = ""
            st.toast("Cleared key")

        st.subheader("Persistence")
        cloud_runtime = is_cloud_runtime()
        if cloud_runtime:
            st.session_state["autosave_enabled"] = False
            st.caption("Cloud mode: itinerary and feedback stay in this browser session only.")
            clear_clicked = st.button("Clear session")
        else:
            st.checkbox(
                "Autosave itinerary locally (data/app_state.json)",
                value=True,
                key="autosave_enabled",
            )
            c1, c2 = st.columns(2)
            if c1.button("Save now"):
                save_app_state(
                    {
                        "itinerary": st.session_state.get("itinerary"),
                        "allowed_pois": st.session_state.get("allowed_pois"),
                        "allowed_chunks": st.session_state.get("allowed_chunks"),
                        "center": st.session_state.get("center"),
                        "city_key": st.session_state.get("city_key"),
                        "start_date": st.session_state.get("start_date"),
                    },
                    enabled=True,
                )
                st.toast("Saved.")
            clear_clicked = c2.button("Clear saved")
        if clear_clicked:
            for k in (
                "itinerary",
                "allowed_pois",
                "allowed_chunks",
                "center",
                "city_key",
                "itinerary_prev",
                "routes",
                "weather",
                "_feedback_events",
            ):
                st.session_state.pop(k, None)
            clear_app_state_file()
            st.toast("Cleared.")

        st.subheader("Speed / agent")
        fast_mode = st.checkbox("Fast mode (fewer tool calls)", value=True, key="fast_mode")
        rag_enabled = st.checkbox(
            "Enable Wikivoyage RAG (slower, may 403)",
            value=False,
            key="rag_enabled",
        )
        show_trace = st.checkbox("Show execution trace", value=True, key="show_trace")
        model = st.text_input("Model", value=DEFAULT_MODEL, key="model_name")
        default_steps = MAX_TOOL_STEPS_FAST if fast_mode else MAX_TOOL_STEPS_FULL
        if "max_steps" not in st.session_state:
            st.session_state["max_steps"] = default_steps
        max_steps = st.slider(
            "Max tool steps",
            min_value=3,
            max_value=12,
            key="max_steps",
        )

        st.subheader("External API etiquette")
        user_agent_email = st.text_input(
            "User-Agent contact email",
            value="your-email@example.com",
            key="ua_email",
            help="Used in User-Agent for Nominatim + Wikivoyage. Use a real email.",
        )
        if user_agent_email.strip().lower() in PLACEHOLDER_EMAILS:
            st.info("Using the project GitHub URL as User-Agent until you enter a real email.")
        user_agent = build_user_agent(user_agent_email)

        st.subheader("Map")
        dark_map = st.checkbox("Dark map style", value=False, key="dark_map")
        routing_enabled = st.checkbox(
            "Walking routes (OSRM)",
            value=True,
            key="routing_enabled",
            help="Uses the public FOSSGIS walking router; failures fall back to straight lines.",
        )
        weather_enabled = st.checkbox(
            "Daily weather (Open-Meteo)",
            value=True,
            key="weather_enabled",
            help="Forecast enrichment is optional and never blocks itinerary generation.",
        )

        render_health_panel(user_agent)

        st.caption(
            "Respect [Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/) "
            "(1 req/s, identifying User-Agent)."
        )

    return {
        "fast_mode": fast_mode,
        "rag_enabled": rag_enabled,
        "show_trace": show_trace,
        "model": model,
        "max_steps": max_steps,
        "user_agent": user_agent,
        "dark_map": dark_map,
        "routing_enabled": routing_enabled,
        "weather_enabled": weather_enabled,
    }
