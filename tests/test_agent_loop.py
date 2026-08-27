from __future__ import annotations

from types import SimpleNamespace

import pytest

from waypoint.agent import loop


class Item(SimpleNamespace):
    def model_dump(self, exclude_none=True):
        return dict(self.__dict__)


class Responses:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


def response(output, text=""):
    return SimpleNamespace(output=output, output_text=text)


def test_agent_forces_search_then_returns_structured_text(monkeypatch):
    tool_call = Item(
        type="function_call",
        name="search_pois",
        arguments='{"city":"Paris","interests":[],"radius_km":5,"limit":10,"query":""}',
        call_id="call-1",
    )
    client = SimpleNamespace(
        responses=Responses(
            [
                response([tool_call]),
                response([], '{"title":"T","city":"Paris","days":[]}'),
            ]
        )
    )
    monkeypatch.setattr(
        loop,
        "call_tool",
        lambda *_args, **_kwargs: '{"pois":[]}',
    )
    raw, _state = loop.run_trip_agent(
        client,
        model="gpt-4.1-mini",
        user_prompt="plan",
        user_agent="ua",
        max_steps=3,
        rag_enabled=False,
    )
    assert raw.startswith("{")
    first = client.responses.calls[0]
    assert first["tool_choice"]["name"] == "search_pois"
    assert first["text"]["format"]["type"] == "json_schema"
    second_input = client.responses.calls[1]["input"]
    assert any(item.get("type") == "function_call_output" for item in second_input if isinstance(item, dict))


def test_malformed_arguments_return_error_to_model():
    tool_call = Item(
        type="function_call",
        name="search_pois",
        arguments="{bad",
        call_id="call-1",
    )
    client = SimpleNamespace(
        responses=Responses([response([tool_call]), response([], "{}")])
    )
    loop.run_trip_agent(
        client,
        model="gpt-4o-mini",
        user_prompt="plan",
        user_agent="ua",
        max_steps=3,
        rag_enabled=False,
    )
    outputs = [
        item
        for item in client.responses.calls[1]["input"]
        if isinstance(item, dict) and item.get("type") == "function_call_output"
    ]
    assert "Invalid JSON" in outputs[0]["output"]


def test_agent_deadline_stops_before_request():
    client = SimpleNamespace(responses=Responses([]))
    with pytest.raises(TimeoutError):
        loop.run_trip_agent(
            client,
            model="gpt-4o-mini",
            user_prompt="plan",
            user_agent="ua",
            max_steps=3,
            rag_enabled=False,
            total_timeout_s=0,
        )


def test_max_steps_is_bounded(monkeypatch):
    tool = Item(type="function_call", name="search_pois", arguments="{}", call_id="c")
    client = SimpleNamespace(responses=Responses([response([tool]), response([tool])]))
    monkeypatch.setattr(loop, "call_tool", lambda *_args, **_kwargs: "{}")
    with pytest.raises(RuntimeError, match="max_steps"):
        loop.run_trip_agent(
            client,
            model="gpt-4o-mini",
            user_prompt="plan",
            user_agent="ua",
            max_steps=2,
            rag_enabled=False,
        )


def test_call_tool_accumulates_state_and_trace(monkeypatch):
    monkeypatch.setattr(
        loop,
        "tool_search_pois",
        lambda **_kwargs: {
            "city_key": "city",
            "display_name": "City",
            "center": {"lat": 1, "lon": 2},
            "pois": [{"poi_id": "p1", "name": "Place"}],
            "error": "",
        },
    )
    state = {"pois": {}, "chunks": {}, "center": {}}
    trace = []
    output = loop.call_tool(
        "search_pois",
        {"city": "City", "interests": [], "radius_km": 5, "limit": 10, "query": ""},
        user_agent="ua",
        tool_state=state,
        rag_enabled=False,
        on_trace=trace.append,
    )
    assert '"p1"' in output
    assert state["pois"]["p1"]["name"] == "Place"
    assert [event["kind"] for event in trace] == ["tool_call", "tool_result"]


def test_call_tool_unknown_and_exception(monkeypatch):
    state = {"pois": {}, "chunks": {}, "center": {}}
    assert "Unknown tool" in loop.call_tool(
        "missing",
        {},
        user_agent="ua",
        tool_state=state,
        rag_enabled=False,
    )
    monkeypatch.setattr(
        loop,
        "tool_search_pois",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    trace = []
    output = loop.call_tool(
        "search_pois",
        {"city": "City"},
        user_agent="ua",
        tool_state=state,
        rag_enabled=False,
        on_trace=trace.append,
    )
    assert "offline" in output
    assert trace[-1]["kind"] == "tool_error"


def test_model_fallback_and_trace(monkeypatch):
    final = response([], "{}")

    class FallbackResponses:
        def __init__(self):
            self.calls = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            if kwargs["model"] == "gpt-4.1-mini":
                raise RuntimeError("model not found")
            return final

    responses = FallbackResponses()
    client = SimpleNamespace(responses=responses)
    trace = []
    loop.run_trip_agent(
        client,
        model="gpt-4.1-mini",
        user_prompt="plan",
        user_agent="ua",
        max_steps=2,
        rag_enabled=False,
        on_trace=trace.append,
    )
    assert responses.calls[-1]["model"] == "gpt-4o-mini"
    assert any(event["kind"] == "run_complete" for event in trace)


def test_output_text_fallback_from_message():
    message = Item(
        type="message",
        content=[Item(type="output_text", text="hello")],
    )
    assert loop._output_text(response([message], "")) == "hello"


def test_sdk_item_helpers_cover_dict_and_plain_object():
    assert loop._item_get({"value": 1}, "value") == 1
    payload = {"type": "message"}
    assert loop._to_input_item(payload) is payload
    plain = SimpleNamespace(type="message")
    assert loop._to_input_item(plain) is plain


def test_retrieve_tool_accumulates_chunks(monkeypatch):
    monkeypatch.setattr(
        loop,
        "tool_retrieve_guides",
        lambda **_kwargs: {
            "hits": [{"chunk_id": "c1", "source": "Guide", "text": "Text", "score": 0.9}],
            "note": "",
        },
    )
    state = {"pois": {}, "chunks": {}, "center": {}}
    output = loop.call_tool(
        "retrieve_guides",
        {"city": "City", "query": "q", "k": 1},
        user_agent="ua",
        tool_state=state,
        rag_enabled=True,
    )
    assert "c1" in output
    assert state["chunks"]["c1"]["source"] == "Guide"


def test_repair_itinerary_uses_constrained_json_schema():
    client = SimpleNamespace(responses=Responses([response([], '{"title":"T"}')]))
    assert loop.repair_itinerary_json(
        client,
        "gpt-4o-mini",
        '{"poi_id":"invented"}',
        allowed_pois={
            "poi-1": {"name": "Museum", "category": "tourism:museum"}
        },
        allowed_chunks={"chunk-1": {"source": "Guide"}},
        expected_days=3,
    ) == '{"title":"T"}'
    call = client.responses.calls[0]
    assert call["text"]["format"]["strict"] is True
    properties = call["text"]["format"]["schema"]["properties"]["days"]["items"][
        "properties"
    ]
    assert properties["morning"]["items"]["properties"]["poi_id"]["enum"] == ["poi-1"]
    assert properties["sources"]["items"]["properties"]["chunk_id"]["enum"] == [
        "chunk-1"
    ]
    assert "exactly 3" in call["input"][0]["content"]


def test_final_agent_schema_is_constrained_after_tool_result(monkeypatch):
    tool_call = Item(
        type="function_call",
        name="search_pois",
        arguments='{"city":"Paris","interests":[],"radius_km":5,"limit":10,"query":""}',
        call_id="call-1",
    )
    client = SimpleNamespace(
        responses=Responses([response([tool_call]), response([], "{}")])
    )

    def fake_call_tool(_name, _args, *, tool_state, **_kwargs):
        tool_state["pois"]["approved-poi"] = {"name": "Approved"}
        return '{"pois":[{"poi_id":"approved-poi"}]}'

    monkeypatch.setattr(loop, "call_tool", fake_call_tool)
    loop.run_trip_agent(
        client,
        model="gpt-4o-mini",
        user_prompt="plan",
        user_agent="ua",
        max_steps=2,
        rag_enabled=False,
    )
    schema = client.responses.calls[1]["text"]["format"]["schema"]
    properties = schema["properties"]["days"]["items"]["properties"]
    for block in ("morning", "afternoon", "evening"):
        assert properties[block]["items"]["properties"]["poi_id"]["enum"] == [
            "approved-poi"
        ]
