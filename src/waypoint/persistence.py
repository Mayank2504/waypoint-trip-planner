"""Session / disk persistence for itineraries."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from waypoint.config import APP_STATE_PATH, DATA_DIR


def is_cloud_runtime() -> bool:
    """Return whether shared/ephemeral Cloud storage must not hold user state."""
    explicit = os.environ.get("WAYPOINT_RUNTIME", "").strip().lower()
    if explicit:
        return explicit == "cloud"
    runtime = os.environ.get("STREAMLIT_RUNTIME_ENVIRONMENT", "").strip().lower()
    hostname = os.environ.get("HOSTNAME", "").strip().lower()
    home = os.environ.get("HOME", "").strip()
    return bool(
        os.environ.get("STREAMLIT_SHARING_MODE")
        or runtime in {"cloud", "community-cloud"}
        or hostname.endswith(".streamlit.app")
        or hostname.startswith("streamlit-")
        or home == "/home/adminuser"
        or Path("/mount/src").exists()
    )


def ensure_data_dir() -> None:
    if is_cloud_runtime():
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def save_app_state(state: Dict[str, Any], *, enabled: bool = True) -> None:
    if not enabled or is_cloud_runtime():
        return
    if not state.get("itinerary") or not state.get("allowed_pois"):
        return
    ensure_data_dir()
    payload = {
        "itinerary": state.get("itinerary"),
        "allowed_pois": state.get("allowed_pois"),
        "allowed_chunks": state.get("allowed_chunks") or {},
        "center": state.get("center") or {},
        "city_key": state.get("city_key") or "",
        "start_date": state.get("start_date"),
    }
    serialized = json.dumps(payload, ensure_ascii=False)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{APP_STATE_PATH.name}.",
        suffix=".tmp",
        dir=str(APP_STATE_PATH.parent),
        text=True,
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        tmp_path.replace(APP_STATE_PATH)
    finally:
        tmp_path.unlink(missing_ok=True)


def load_app_state() -> Optional[Dict[str, Any]]:
    if is_cloud_runtime():
        return None
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
    if is_cloud_runtime():
        return
    if APP_STATE_PATH.exists():
        try:
            APP_STATE_PATH.unlink()
        except Exception:
            pass
