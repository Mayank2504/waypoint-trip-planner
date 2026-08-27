"""
Waypoint — AI Trip Planner Capstone

Streamlit entrypoint: UI wiring only. Business logic lives in src/waypoint/.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import streamlit as st
from openai import OpenAI

# Ensure src/ is importable when running `streamlit run app.py`
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ui.itinerary import render_before_after, render_itinerary
from ui.map import itinerary_paths, itinerary_points, render_map

try:
    # A stale Streamlit module cache can briefly expose the previous ui.map during deploy.
    from ui.map import routed_paths
except ImportError:
    def routed_paths(_routes, _day_filter=None):
        return []
from ui.sidebar import render_sidebar
from ui.trace import append_trace, render_trace, reset_trace
from waypoint.agent.loop import repair_itinerary_json, run_trip_agent
from waypoint.agent.prompts import plan_prompt, refine_prompt, regen_day_prompt
from waypoint.config import APP_NAME, POI_LIMIT_FAST, POI_LIMIT_FULL
from waypoint.export.pdf import build_itinerary_pdf
from waypoint.feedback import append_feedback, feedback_stats
from waypoint.osm.tags import ALL_INTERESTS
from waypoint.persistence import ensure_data_dir, load_app_state, save_app_state
from waypoint.routing import route_itinerary, route_warnings
from waypoint.schemas import parse_itinerary
from waypoint.weather import fetch_daily_forecast
from waypoint.validate import (
    extract_json_object,
    find_duplicate_poi_ids,
    other_days_unchanged,
    validate_day_count,
    validate_itinerary_poi_ids,
    validate_plan_inputs,
    validate_source_ids,
)


st.set_page_config(page_title=f"{APP_NAME} Trip Planner", layout="wide", page_icon="🗺️")


def _init_state() -> None:
    ensure_data_dir()
    if st.session_state.get("_loaded_app_state"):
        return
    st.session_state["_loaded_app_state"] = True
    if st.session_state.get("itinerary"):
        return
    saved = load_app_state()
    if not saved:
        return
    st.session_state["itinerary"] = saved["itinerary"]
    st.session_state["allowed_pois"] = saved["allowed_pois"]
    st.session_state["allowed_chunks"] = saved.get("allowed_chunks") or {}
    st.session_state["center"] = saved.get("center") or {}
    st.session_state["city_key"] = saved.get("city_key") or ""
    if saved.get("start_date"):
        try:
            st.session_state["start_date_input"] = date.fromisoformat(saved["start_date"])
        except (TypeError, ValueError):
            pass


def get_openai_client() -> OpenAI:
    key = (st.session_state.get("user_openai_key") or "").strip()
    if not key:
        st.error("Enter your OpenAI API key in the sidebar.")
        st.stop()
    # Keep each model call below the agent's overall 90-second budget.
    return OpenAI(api_key=key, timeout=30.0, max_retries=0)


def explain_agent_error(error: Exception) -> str:
    message = str(error)
    lowered = message.lower()
    if "connection" in lowered or "timed out" in lowered:
        return (
            "Could not reach the OpenAI API. Check your internet connection, VPN, "
            "proxy, or corporate firewall, then retry."
        )
    if "401" in lowered or "authentication" in lowered or "api key" in lowered:
        return "OpenAI rejected the API key. Clear it in the sidebar and enter a valid key."
    if "429" in lowered or "quota" in lowered or "billing" in lowered:
        return "OpenAI quota or billing limit reached. Check billing and usage limits."
    if "model" in lowered and ("not found" in lowered or "access" in lowered):
        return "This API key cannot access the selected model. Try `gpt-4o-mini`."
    return message


def maybe_clear_key() -> None:
    if not st.session_state.get("remember_key", True):
        st.session_state["user_openai_key"] = ""


def persist_current() -> None:
    selected_date = st.session_state.get("start_date_input")
    save_app_state(
        {
            "itinerary": st.session_state.get("itinerary"),
            "allowed_pois": st.session_state.get("allowed_pois"),
            "allowed_chunks": st.session_state.get("allowed_chunks"),
            "center": st.session_state.get("center"),
            "city_key": st.session_state.get("city_key"),
            "start_date": selected_date.isoformat() if hasattr(selected_date, "isoformat") else selected_date,
        },
        enabled=st.session_state.get("autosave_enabled", True),
    )


def apply_itinerary(itin: dict, allowed: dict, tool_state: dict, *, keep_prev: bool = True) -> None:
    if keep_prev and st.session_state.get("itinerary"):
        st.session_state["itinerary_prev"] = st.session_state["itinerary"]
    st.session_state["itinerary"] = itin
    st.session_state["allowed_pois"] = allowed
    previous_chunks = st.session_state.get("allowed_chunks") or {}
    st.session_state["allowed_chunks"] = {
        **previous_chunks,
        **(tool_state.get("chunks") or {}),
    }
    st.session_state["center"] = tool_state.get("center") or st.session_state.get("center") or {}
    st.session_state["city_key"] = tool_state.get("city_key") or st.session_state.get("city_key") or ""
    st.session_state.pop("_route_signature", None)
    st.session_state.pop("routes", None)
    st.session_state.pop("_weather_signature", None)
    st.session_state.pop("weather", None)
    persist_current()


def parse_and_validate(
    raw: str,
    allowed: dict,
    *,
    expected_days: int,
    allowed_chunks: dict,
) -> dict:
    data = extract_json_object(raw)
    itin_model = parse_itinerary(data)
    itin = itin_model.to_dict()
    bad = validate_itinerary_poi_ids(itin, allowed)
    if bad:
        raise ValueError(f"Itinerary referenced unknown poi_id(s): {bad}")
    day_errors = validate_day_count(itin, expected_days)
    if day_errors:
        raise ValueError(" ".join(day_errors))
    unknown_sources = validate_source_ids(itin, allowed_chunks)
    if unknown_sources:
        raise ValueError(f"Itinerary referenced unknown RAG source chunk(s): {unknown_sources}")
    duplicates = find_duplicate_poi_ids(itin)
    if duplicates:
        raise ValueError(f"Itinerary repeated POI(s): {duplicates}")
    if not allowed:
        raise ValueError("No POIs were returned by tools. The model may not have called search_pois.")
    return itin


_init_state()
settings = render_sidebar()

st.title(f"{APP_NAME}")
st.caption(
    "Plan a multi-day trip with an OpenAI agent, live OpenStreetMap POIs, "
    "optional Wikivoyage grounding, interactive maps, and a feedback loop."
)

# ---- Plan form ----
st.header("Plan")
colA, colB = st.columns(2)
with colA:
    city = st.text_input("Destination city", value="Santa Fe, NM", key="city_input")
    days = st.slider("Trip length (days)", 1, 7, 3, key="days_input")
    start_date = st.date_input("Trip start date", value=date.today(), key="start_date_input")
    pace = st.selectbox("Pace", ["relaxed", "balanced", "packed"], index=1, key="pace_input")
    radius_km = st.slider("POI search radius (km)", 1, 30, 8, key="radius_input")
with colB:
    interests = st.multiselect(
        "Interests (drives POI tags)",
        ALL_INTERESTS,
        default=["outdoors", "food"],
        key="interests_input",
    )
    constraints = st.text_area(
        "Constraints",
        value="No early mornings. Prefer 1–2 big activities per day.",
        key="constraints_input",
    )
    notes = st.text_area(
        "Extra notes",
        value="Include at least one iconic highlight and one hidden gem.",
        key="notes_input",
    )

generate_clicked = st.button("Generate itinerary", type="primary")

if generate_clicked:
    errors = validate_plan_inputs(city, days, float(radius_km))
    if errors:
        for e in errors:
            st.error(e)
        st.stop()

    reset_trace()
    client = get_openai_client()
    raw = ""
    tool_state: dict = {}
    fast_mode = settings["fast_mode"]
    poi_limit = POI_LIMIT_FAST if fast_mode else POI_LIMIT_FULL
    prompt = plan_prompt(
        city=city,
        days=days,
        pace=pace,
        interests=interests,
        constraints=constraints,
        notes=notes,
        radius_km=float(radius_km),
        fast_mode=fast_mode,
        poi_limit=poi_limit,
    )

    status = st.status("Planning…", expanded=True) if settings["show_trace"] else None

    def _status(msg: str) -> None:
        if status is not None:
            status.write(msg)

    try:
        with st.spinner("Calling agent…"):
            raw, tool_state = run_trip_agent(
                client,
                model=settings["model"],
                user_prompt=prompt,
                user_agent=settings["user_agent"],
                max_steps=int(settings["max_steps"]),
                rag_enabled=settings["rag_enabled"],
                on_trace=append_trace,
                on_status=_status,
            )
    except Exception as e:
        st.error(f"Agent failed: {explain_agent_error(e)}")
        maybe_clear_key()
        if settings["show_trace"]:
            render_trace()
        st.stop()
    finally:
        maybe_clear_key()
        if status is not None:
            status.update(label="Done", state="complete")

    try:
        allowed = dict(tool_state.get("pois", {}))
        if not allowed:
            extra = tool_state.get("last_search_error") or "search_pois returned no places"
            st.error(
                f"Could not build a plan because no POIs were found. {extra} "
                "Set a real User-Agent email, try a well-known city (e.g. Santa Fe, NM), "
                "or widen the radius."
            )
            with st.expander("Raw model output"):
                st.code(raw or "(empty)")
            st.stop()
        try:
            itin = parse_and_validate(
                raw,
                allowed,
                expected_days=days,
                allowed_chunks=tool_state.get("chunks") or {},
            )
        except Exception as parse_err:
            if status is not None:
                status.write("Repairing itinerary JSON…")
            try:
                raw = repair_itinerary_json(
                    client,
                    settings["model"],
                    raw or "",
                    allowed_pois=allowed,
                    allowed_chunks=tool_state.get("chunks") or {},
                    expected_days=days,
                )
                itin = parse_and_validate(
                    raw,
                    allowed,
                    expected_days=days,
                    allowed_chunks=tool_state.get("chunks") or {},
                )
            except Exception:
                raise parse_err
        apply_itinerary(itin, allowed, tool_state, keep_prev=False)
        st.success("Itinerary saved.")
    except Exception as e:
        st.error(f"Could not parse/validate itinerary: {e}")
        with st.expander("Raw model output"):
            st.code(raw if raw else "(empty)")

# ---- Always render saved itinerary (outside button handler) ----
itin = st.session_state.get("itinerary")
allowed = st.session_state.get("allowed_pois") or {}
center = st.session_state.get("center") or {}

if itin and allowed:
    routes: dict = {}
    if settings["routing_enabled"]:
        route_signature = json.dumps(
            {"itinerary": itin, "allowed_pois": allowed},
            ensure_ascii=False,
            sort_keys=True,
        )
        if st.session_state.get("_route_signature") != route_signature:
            with st.spinner("Calculating walking routes…"):
                st.session_state["routes"] = route_itinerary(
                    itin,
                    allowed,
                    settings["user_agent"],
                    mode="foot",
                )
            st.session_state["_route_signature"] = route_signature
        routes = st.session_state.get("routes") or {}

    weather: dict = {}
    if (
        settings["weather_enabled"]
        and center.get("lat") is not None
        and center.get("lon") is not None
    ):
        selected_date = st.session_state.get("start_date_input") or date.today()
        weather_signature = (
            round(float(center["lat"]), 3),
            round(float(center["lon"]), 3),
            selected_date.isoformat(),
            len(itin.get("days") or []),
        )
        if st.session_state.get("_weather_signature") != weather_signature:
            with st.spinner("Loading daily weather…"):
                st.session_state["weather"] = fetch_daily_forecast(
                    float(center["lat"]),
                    float(center["lon"]),
                    selected_date,
                    len(itin.get("days") or []),
                )
            st.session_state["_weather_signature"] = weather_signature
        weather = st.session_state.get("weather") or {}

    st.divider()
    st.header("Itinerary")
    render_itinerary(
        itin,
        allowed,
        routes=routes,
        weather=weather,
        start_date=(st.session_state.get("start_date_input") or date.today()).isoformat(),
    )
    for warning in route_warnings(routes, st.session_state.get("pace_input", "balanced")):
        st.warning(warning)
    if weather:
        st.caption(
            f"Weather data by [Open-Meteo.com](https://open-meteo.com/) · "
            f"Timezone: {weather.get('timezone') or 'unavailable'}"
        )
    if st.session_state.get("itinerary_prev"):
        render_before_after(st.session_state["itinerary_prev"], itin)

    st.subheader("Map")
    day_options = ["All"] + [d.get("day") for d in itin.get("days", []) if d.get("day") is not None]
    if "map_day_filter" in st.session_state and st.session_state["map_day_filter"] not in day_options:
        del st.session_state["map_day_filter"]
    day_filter = st.selectbox("Show day", options=day_options, index=0, key="map_day_filter")
    df = None if day_filter == "All" else int(day_filter)
    pts = itinerary_points(itin, allowed, df)
    fallback_paths = itinerary_paths(itin, allowed, df)
    osrm_paths = routed_paths(routes, df)
    routed_days = {path["day"] for path in osrm_paths}
    paths = osrm_paths + [path for path in fallback_paths if path["day"] not in routed_days]
    render_map(pts, paths, center, dark=settings["dark_map"])

    d1, d2 = st.columns(2)
    with d1:
        st.download_button(
            "Download itinerary.json",
            data=json.dumps(itin, ensure_ascii=False, indent=2),
            file_name="itinerary.json",
            mime="application/json",
        )
    with d2:
        try:
            pdf_bytes = build_itinerary_pdf(
                itin,
                allowed,
                pace=st.session_state.get("pace_input", ""),
                interests=st.session_state.get("interests_input") or [],
            )
            st.download_button(
                "Download itinerary.pdf",
                data=pdf_bytes,
                file_name="itinerary.pdf",
                mime="application/pdf",
            )
        except Exception as e:
            st.warning(f"PDF export unavailable: {e}")

    with st.expander("Raw JSON", expanded=False):
        st.json(itin)

    # ---- Improve ----
    st.divider()
    st.header("Improve")
    left, right = st.columns(2)

    with left:
        st.markdown("### Refine entire itinerary")
        refine_text = st.text_input(
            "Refinement request",
            value="Make it more outdoorsy, keep evenings chill, and reduce walking.",
            key="refine_text",
        )
        if st.button("Apply refinement"):
            reset_trace()
            client = get_openai_client()
            status = st.status("Refining…", expanded=True) if settings["show_trace"] else None

            def _s(msg: str) -> None:
                if status is not None:
                    status.write(msg)

            try:
                with st.spinner("Refining…"):
                    raw2, tool_state2 = run_trip_agent(
                        client,
                        model=settings["model"],
                        user_prompt=refine_prompt(
                            itin=itin,
                            request=refine_text,
                            fast_mode=settings["fast_mode"],
                        ),
                        user_agent=settings["user_agent"],
                        max_steps=int(settings["max_steps"]),
                        rag_enabled=settings["rag_enabled"],
                        on_trace=append_trace,
                        on_status=_s,
                    )
            except Exception as e:
                st.error(f"Refine failed: {e}")
                maybe_clear_key()
                st.stop()
            finally:
                maybe_clear_key()
                if status is not None:
                    status.update(label="Done", state="complete")

            try:
                merged = dict(allowed)
                merged.update(tool_state2.get("pois", {}))
                chunks2 = {
                    **(st.session_state.get("allowed_chunks") or {}),
                    **(tool_state2.get("chunks") or {}),
                }
                try:
                    itin2 = parse_and_validate(
                        raw2,
                        merged,
                        expected_days=len(itin.get("days") or []),
                        allowed_chunks=chunks2,
                    )
                except Exception as parse_err:
                    try:
                        raw2 = repair_itinerary_json(
                            client,
                            settings["model"],
                            raw2 or "",
                            allowed_pois=merged,
                            allowed_chunks=chunks2,
                            expected_days=len(itin.get("days") or []),
                        )
                        itin2 = parse_and_validate(
                            raw2,
                            merged,
                            expected_days=len(itin.get("days") or []),
                            allowed_chunks=chunks2,
                        )
                    except Exception:
                        raise parse_err
                apply_itinerary(itin2, merged, tool_state2)
                st.success("Itinerary updated.")
                st.rerun()
            except Exception as e:
                st.error(f"Could not parse/validate refined JSON: {e}")
                with st.expander("Raw output"):
                    st.code(raw2)

    with right:
        st.markdown("### Regenerate one day")
        day_nums = [int(d.get("day")) for d in (itin.get("days") or []) if d.get("day") is not None]
        if not day_nums:
            st.info("No day numbers found.")
        else:
            target_day = st.selectbox("Which day?", options=sorted(day_nums), key="regen_day")
            day_request = st.text_area(
                "Day-specific request",
                value="Swap in a different afternoon activity and add a cozy dinner option.",
                height=100,
                key="regen_request",
            )
            if st.button("Regenerate day"):
                reset_trace()
                client = get_openai_client()
                status = st.status("Regenerating…", expanded=True) if settings["show_trace"] else None

                def _s2(msg: str) -> None:
                    if status is not None:
                        status.write(msg)

                try:
                    with st.spinner(f"Regenerating Day {target_day}…"):
                        raw3, tool_state3 = run_trip_agent(
                            client,
                            model=settings["model"],
                            user_prompt=regen_day_prompt(
                                itin=itin,
                                target_day=int(target_day),
                                request=day_request,
                                fast_mode=settings["fast_mode"],
                            ),
                            user_agent=settings["user_agent"],
                            max_steps=int(settings["max_steps"]),
                            rag_enabled=settings["rag_enabled"],
                            on_trace=append_trace,
                            on_status=_s2,
                        )
                except Exception as e:
                    st.error(f"Day regen failed: {e}")
                    maybe_clear_key()
                    st.stop()
                finally:
                    maybe_clear_key()
                    if status is not None:
                        status.update(label="Done", state="complete")

                try:
                    merged = dict(allowed)
                    merged.update(tool_state3.get("pois", {}))
                    chunks3 = {
                        **(st.session_state.get("allowed_chunks") or {}),
                        **(tool_state3.get("chunks") or {}),
                    }
                    try:
                        itin3 = parse_and_validate(
                            raw3,
                            merged,
                            expected_days=len(itin.get("days") or []),
                            allowed_chunks=chunks3,
                        )
                    except Exception as parse_err:
                        try:
                            raw3 = repair_itinerary_json(
                                client,
                                settings["model"],
                                raw3 or "",
                                allowed_pois=merged,
                                allowed_chunks=chunks3,
                                expected_days=len(itin.get("days") or []),
                            )
                            itin3 = parse_and_validate(
                                raw3,
                                merged,
                                expected_days=len(itin.get("days") or []),
                                allowed_chunks=chunks3,
                            )
                        except Exception:
                            raise parse_err
                    ok, changed = other_days_unchanged(itin, itin3, target_day=int(target_day))
                    if not ok:
                        st.error(f"Model changed other day(s): {changed}. Not applying.")
                        st.stop()
                    apply_itinerary(itin3, merged, tool_state3)
                    st.success(f"Updated Day {target_day}.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not parse/validate day-regenerated JSON: {e}")
                    with st.expander("Raw output"):
                        st.code(raw3)

    # ---- Votes ----
    st.divider()
    st.header("Votes")
    st.caption("Upvoted POIs get boosted in future search_pois results for this destination.")
    city_key = st.session_state.get("city_key", "")
    referenced = []
    for day in itin.get("days", []) or []:
        for block in ("morning", "afternoon", "evening"):
            for item in day.get(block, []) or []:
                if item.get("poi_id"):
                    referenced.append(item["poi_id"])
    referenced = list(dict.fromkeys(referenced))

    for pid in referenced:
        p = allowed.get(pid, {})
        name = p.get("name", pid)
        cat = p.get("category", "")
        url = p.get("url", "")
        cols = st.columns([5, 1, 1])
        with cols[0]:
            line = f"**{name}**  \n`{pid}`  \n{cat}"
            if url:
                line += f"  \n{url}"
            st.markdown(line)
        if cols[1].button("Up", key=f"up_{pid}"):
            append_feedback({"city_key": city_key, "poi_id": pid, "vote": "up", "name": name})
            st.toast(f"Upvoted: {name}")
        if cols[2].button("Down", key=f"down_{pid}"):
            append_feedback({"city_key": city_key, "poi_id": pid, "vote": "down", "name": name})
            st.toast(f"Downvoted: {name}")

    with st.expander("Feedback stats", expanded=False):
        stats = feedback_stats(city_key)
        st.write(
            f"Total votes: **{stats['total']}** — ups **{stats['ups']}**, downs **{stats['downs']}**"
        )
        if stats["top_pois"]:
            st.markdown("Most voted POIs:")
            for poi_id, count in stats["top_pois"]:
                st.markdown(f"- `{poi_id}` × {count}")
        if stats["recent"]:
            st.markdown("Recent events:")
            st.json(stats["recent"][:5])

else:
    st.info("No saved itinerary yet. Fill in the form above and click **Generate itinerary**.")

if settings["show_trace"] and st.session_state.get("trace"):
    render_trace()
