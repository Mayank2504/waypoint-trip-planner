"""TF-IDF retrieval over Wikivoyage chunks."""
from __future__ import annotations

import re
from typing import Any, Dict, List

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from waypoint.cache_utils import cached_wikivoyage_text

# Module-level cache for vectorizers (not picklable via st.cache_data)
_RAG_CACHE: Dict[str, Dict[str, Any]] = {}


def _hard_split(text: str, max_chars: int) -> List[str]:
    pieces: List[str] = []
    remaining = text.strip()
    while len(remaining) > max_chars:
        split_at = remaining.rfind(" ", 0, max_chars + 1)
        if split_at < max_chars // 2:
            split_at = max_chars
        pieces.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        pieces.append(remaining)
    return pieces


def chunk_text(text: str, max_chars: int = 900, min_chars: int = 240) -> List[str]:
    """Paragraph/sentence-aware chunks with a strict maximum and no dropped tail."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text or "") if p.strip()]
    units: List[str] = []
    for paragraph in paragraphs:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", paragraph) if s.strip()]
        for sentence in sentences or [paragraph]:
            units.extend(_hard_split(sentence, max_chars))

    chunks: List[str] = []
    current = ""
    for unit in units:
        candidate = f"{current} {unit}".strip() if current else unit
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = unit
    if current:
        if chunks and len(current) < min_chars and len(chunks[-1]) + 1 + len(current) <= max_chars:
            chunks[-1] = f"{chunks[-1]} {current}"
        else:
            chunks.append(current)
    return chunks


def get_city_rag_index(city: str, user_agent: str) -> Dict[str, Any]:
    key = city.strip().lower()
    if key in _RAG_CACHE:
        return _RAG_CACHE[key]

    article = cached_wikivoyage_text(city, user_agent)
    title = article.get("title") or ""
    text = article.get("text") or ""
    chunks = chunk_text(text) if text else []
    if not title or not chunks:
        return {"title": title or None, "chunks": [], "vectorizer": None, "X": None}

    vectorizer = TfidfVectorizer(stop_words="english", max_features=30000)
    X = vectorizer.fit_transform(chunks)
    _RAG_CACHE[key] = {"title": title, "chunks": chunks, "vectorizer": vectorizer, "X": X}
    return _RAG_CACHE[key]


def rag_retrieve(city: str, query: str, user_agent: str, k: int = 4) -> List[Dict[str, Any]]:
    idx = get_city_rag_index(city, user_agent=user_agent)
    if not idx.get("title") or idx.get("vectorizer") is None or idx.get("X") is None:
        return []

    vectorizer: TfidfVectorizer = idx["vectorizer"]
    X = idx["X"]
    q = vectorizer.transform([query or city])
    sims = cosine_similarity(q, X).ravel()
    topk = np.argsort(-sims)[: max(1, min(k, 8))]
    return [
        {
            "chunk_id": f"{idx['title']}__{int(j)}",
            "source": idx["title"],
            "text": idx["chunks"][int(j)],
            "score": float(sims[int(j)]),
        }
        for j in topk
    ]


def clear_rag_cache() -> None:
    _RAG_CACHE.clear()
