from __future__ import annotations

from waypoint.rag import retrieve
from waypoint.rag.retrieve import chunk_text
from waypoint.rag import wikivoyage
from waypoint.rag.wikivoyage import html_to_text


def test_html_cleanup_decodes_entities_and_preserves_paragraphs():
    text = html_to_text("<p>Food &amp; drink.</p><p>Second paragraph.</p>")
    assert "Food & drink." in text
    assert "\n\n" in text


def test_chunk_hard_max_for_long_sentence():
    chunks = chunk_text("word " * 1000, max_chars=200, min_chars=40)
    assert len(chunks) > 1
    assert all(0 < len(chunk) <= 200 for chunk in chunks)


def test_chunk_keeps_short_trailing_text():
    text = ("First sentence is useful. " * 20) + "\n\nTail."
    chunks = chunk_text(text, max_chars=160, min_chars=40)
    assert chunks
    assert chunks[-1].endswith("Tail.")


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []


def test_tfidf_retrieval_ranks_matching_chunk(monkeypatch):
    retrieve.clear_rag_cache()
    monkeypatch.setattr(
        retrieve,
        "cached_wikivoyage_text",
        lambda *_args: {
            "title": "Paris",
            "text": (
                "Museums and galleries include the Louvre and many art collections. "
                "Visitors interested in paintings can spend a full day here.\n\n"
                "Parks and gardens offer quiet walks, trees, lawns and outdoor picnics. "
                "These green spaces are best on sunny afternoons."
            ),
        },
    )
    hits = retrieve.rag_retrieve("Paris", "art museum paintings", "ua", k=1)
    assert hits and hits[0]["source"] == "Paris"
    assert "museum" in hits[0]["text"].lower()


def test_empty_article_is_not_cached(monkeypatch):
    retrieve.clear_rag_cache()
    calls = {"count": 0}

    def empty(*_args):
        calls["count"] += 1
        return {"title": "", "text": ""}

    monkeypatch.setattr(retrieve, "cached_wikivoyage_text", empty)
    retrieve.get_city_rag_index("Missing", "ua")
    retrieve.get_city_rag_index("Missing", "ua")
    assert calls["count"] == 2


def test_wikivoyage_fetch_parses_and_degrades(monkeypatch):
    monkeypatch.setattr(
        wikivoyage,
        "request_json",
        lambda *_args, **_kwargs: {"query": {"search": [{"title": "Paris"}]}},
    )
    assert wikivoyage.wikivoyage_resolve_title("Paris", "ua") == "Paris"

    monkeypatch.setattr(
        wikivoyage,
        "request_json",
        lambda *_args, **_kwargs: {"parse": {"text": {"*": "<p>Hello &amp; welcome.</p>"}}},
    )
    assert wikivoyage.wikivoyage_plaintext("Paris", "ua") == "Hello & welcome."

    monkeypatch.setattr(
        wikivoyage,
        "request_json",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("blocked")),
    )
    assert wikivoyage.wikivoyage_resolve_title("Paris", "ua") is None
    assert wikivoyage.wikivoyage_plaintext("Paris", "ua") == ""
