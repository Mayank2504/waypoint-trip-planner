"""Wikivoyage article fetch."""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

import requests

from waypoint.config import WIKIVOYAGE_API


def wikimedia_headers(user_agent: str) -> Dict[str, str]:
    ua = (user_agent or "").strip() or "waypoint-trip-planner/1.0 (contact: unknown)"
    return {"User-Agent": ua, "Accept": "application/json"}


def wikivoyage_resolve_title(city: str, user_agent: str) -> Optional[str]:
    params = {
        "action": "query",
        "list": "search",
        "srsearch": city,
        "srlimit": 1,
        "format": "json",
    }
    r = requests.get(WIKIVOYAGE_API, params=params, headers=wikimedia_headers(user_agent), timeout=15)
    if r.status_code == 403:
        return None
    r.raise_for_status()
    hits = (r.json().get("query", {}) or {}).get("search") or []
    return hits[0]["title"] if hits else None


def html_to_text(html: str) -> str:
    text = re.sub(r"<(script|style).*?>.*?</\1>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.I)
    text = re.sub(r"</h[1-6]\s*>", "\n\n", text, flags=re.I)
    text = re.sub(r"<li\s*>", "\n- ", text, flags=re.I)
    text = re.sub(r"<.*?>", " ", text, flags=re.S)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def wikivoyage_plaintext(title: str, user_agent: str) -> str:
    params = {"action": "parse", "page": title, "prop": "text", "format": "json"}
    r = requests.get(WIKIVOYAGE_API, params=params, headers=wikimedia_headers(user_agent), timeout=20)
    if r.status_code == 403:
        return ""
    r.raise_for_status()
    html = r.json()["parse"]["text"]["*"]
    return html_to_text(html)


def check_wikivoyage(user_agent: str) -> Dict[str, Any]:
    try:
        title = wikivoyage_resolve_title("Paris", user_agent)
        if not title:
            return {"ok": False, "detail": "403 or no search hits (RAG can stay off)"}
        return {"ok": True, "detail": f"Found article: {title}"}
    except Exception as e:
        return {"ok": False, "detail": str(e)}
