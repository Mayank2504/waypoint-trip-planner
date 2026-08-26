"""TF-IDF retrieval over Wikivoyage chunks."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from waypoint.rag.wikivoyage import wikivoyage_plaintext, wikivoyage_resolve_title

# Module-level cache for vectorizers (not picklable via st.cache_data)
_RAG_CACHE: Dict[str, Dict[str, Any]] = {}


def chunk_text(text: str, max_chars: int = 900, min_chars: int = 240) -> List[str]:
    """Paragraph-aware chunking; avoid mid-sentence splits when possible."""
    raw = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not raw:
        # Fall back to sentence-ish splits
        raw = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]

    chunks: List[str] = []
    buf = ""
    for p in raw:
        candidate = (buf + "\n\n" + p).strip() if buf else p
        if len(candidate) <= max_chars:
            buf = candidate
            continue
        if len(buf) >= min_chars:
            chunks.append(buf)
            buf = p
        else:
            # buf too small — split long paragraph on sentences
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", p) if s.strip()]
            for s in sentences:
                cand2 = (buf + " " + s).strip() if buf else s
                if len(cand2) <= max_chars:
                    buf = cand2
                else:
                    if buf:
                        chunks.append(buf)
                    buf = s
    if buf and len(buf) >= min_chars:
        chunks.append(buf)
    elif buf and not chunks:
        chunks.append(buf)
    return chunks


def get_city_rag_index(city: str, user_agent: str) -> Dict[str, Any]:
    key = city.strip().lower()
    if key in _RAG_CACHE:
        return _RAG_CACHE[key]

    title = wikivoyage_resolve_title(city, user_agent=user_agent)
    if not title:
        _RAG_CACHE[key] = {"title": None, "chunks": [], "vectorizer": None, "X": None}
        return _RAG_CACHE[key]

    text = wikivoyage_plaintext(title, user_agent=user_agent)
    chunks = chunk_text(text) if text else []
    if not chunks:
        _RAG_CACHE[key] = {"title": title, "chunks": [], "vectorizer": None, "X": None}
        return _RAG_CACHE[key]

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
