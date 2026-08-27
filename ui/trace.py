"""Execution trace rendering."""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List

import streamlit as st


def reset_trace() -> None:
    st.session_state["trace"] = []


def append_trace(event: Dict[str, Any]) -> None:
    st.session_state.setdefault("trace", []).append(event)


def render_trace() -> None:
    with st.expander("Execution trace", expanded=False):
        trace: List[Dict[str, Any]] = st.session_state.get("trace", [])
        if not trace:
            st.caption("No trace yet.")
            return
        for ev in trace:
            ts = time.strftime("%H:%M:%S", time.localtime(ev.get("ts", time.time())))
            kind = ev.get("kind")
            if kind == "model_call":
                st.markdown(f"**{ts}** model_call — step **{ev.get('step')}**")
            elif kind == "model_result":
                st.markdown(
                    f"**{ts}** model_result — step **{ev.get('step')}** "
                    f"in **{ev.get('elapsed_s')}s**"
                )
            elif kind == "tool_call":
                st.markdown(f"**{ts}** tool_call `{ev.get('name')}`")
                st.code(json.dumps(ev.get("args", {}), indent=2), language="json")
            elif kind == "tool_result":
                st.markdown(
                    f"**{ts}** tool_result `{ev.get('name')}` in **{ev.get('elapsed_s')}s**"
                )
            elif kind == "tool_error":
                st.markdown(
                    f"**{ts}** tool_error `{ev.get('name')}` in **{ev.get('elapsed_s')}s**"
                )
                st.code(ev.get("error", ""))
            elif kind == "note":
                st.markdown(f"**{ts}** {ev.get('message')}")
            elif kind == "run_complete":
                st.markdown(f"**{ts}** run complete in **{ev.get('elapsed_s')}s**")
