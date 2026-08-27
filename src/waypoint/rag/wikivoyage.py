"""Wikivoyage article fetch."""
from __future__ import annotations

import html as html_lib
import re
from typing import Any, Dict, Optional

from waypoint.config import WIKIVOYAGE_API
from waypoint.http import request_json


def wikimedia_headers(user_agent: str) -> Dict[str, str]:
    ua = (user_agent or "").strip() or "WaypointTripPlanner/1.0 (+https://github.com/Mayank2504/waypoint-trip-planner)"
    return {"User-Agent": ua, "Accept": "application/json"}


def wikivoyage_resolve_title(city: str, user_agent: str) -> Optional[str]:
    params = {
        "action": "query",
        "list": "search",
        "srsearch": city,
        "srlimit": 1,
        "format": "json",
    }
    try:
        payload = request_json(
            "GET",
            WIKIVOYAGE_API,
            service="Wikivoyage",
            params=params,
            headers=wikimedia_headers(user_agent),
            timeout=(5, 15),
            attempts=2,
        )
        hits = (payload.get("query", {}) or {}).get("search") or []
        return hits[0].get("title") if hits else None
    except Exception:
        return None


def html_to_text(html: str) -> str:
    text = re.sub(r"<(script|style).*?>.*?</\1>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.I)
    text = re.sub(r"</h[1-6]\s*>", "\n\n", text, flags=re.I)
    text = re.sub(r"<li\s*>", "\n- ", text, flags=re.I)
    text = re.sub(r"<.*?>", " ", text, flags=re.S)
    text = html_lib.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def wikivoyage_plaintext(title: str, user_agent: str) -> str:
    params = {"action": "parse", "page": title, "prop": "text", "format": "json"}
    try:
        payload = request_json(
            "GET",
            WIKIVOYAGE_API,
            service="Wikivoyage",
            params=params,
            headers=wikimedia_headers(user_agent),
            timeout=(5, 20),
            attempts=2,
        )
        html = payload["parse"]["text"]["*"]
        return html_to_text(html)
    except Exception:
        return ""


def check_wikivoyage(user_agent: str) -> Dict[str, Any]:
    try:
        title = wikivoyage_resolve_title("Paris", user_agent)
        if not title:
            return {"ok": False, "detail": "403 or no search hits (RAG can stay off)"}
        return {"ok": True, "detail": f"Found article: {title}"}
    except Exception as e:
        return {"ok": False, "detail": str(e)}
