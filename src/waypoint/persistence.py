"""Session / disk persistence for itineraries."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from waypoint.config import APP_STATE_PATH, DATA_DIR


def is_cloud_runtime() -> bool:
    """Streamlit Community Cloud sets these; prefer session-only persistence there."""
    return bool(
        os.environ.get("STREAMLIT_SHARING_MODE")
        or os.environ.get("STREAMLIT_SERVER_HEADLESS")
        and os.environ.get("HOSTNAME", "").startswith("streamlit")
    )


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def save_app_state(state: Dict[str, Any], *, enabled: bool = True) -> None:
    if not enabled:
        return
    if not state.get("itinerary") or not state.get("allowed_pois"):
        return
    # On Cloud, disk is shared/ephemeral — still write for single-demo convenience,
    # but callers should treat session_state as source of truth.
    ensure_data_dir()
    payload = {
        "itinerary": state.get("itinerary"),
        "allowed_pois": state.get("allowed_pois"),
        "center": state.get("center") or {},
        "city_key": state.get("city_key") or "",
    }
    APP_STATE_PATH.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def load_app_state() -> Optional[Dict[str, Any]]:
    if not APP_STATE_PATH.exists():
        return None
    try:
        data = json.loads(APP_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    if not data.get("itinerary") or not data.get("allowed_pois"):
        return None
    return data


def clear_app_state_file() -> None:
    if APP_STATE_PATH.exists():
        try:
            APP_STATE_PATH.unlink()
        except Exception:
            pass
