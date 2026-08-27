"""OpenAI Responses API agent loop with tool calling and tracing."""
from __future__ import annotations

import json
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from openai import OpenAI

from waypoint.agent.schemas_openai import TOOLS
from waypoint.agent.tools import tool_retrieve_guides, tool_search_pois
from waypoint.schemas import ITINERARY_JSON_SCHEMA


TraceCallback = Callable[[Dict[str, Any]], None]


def _item_get(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _to_input_item(item: Any) -> Any:
    """Serialize SDK output objects so they can be sent back as input."""
    if isinstance(item, dict):
        return item
    if hasattr(item, "model_dump"):
        return item.model_dump(exclude_none=True)
    return item


def _output_text(resp: Any) -> str:
    text = getattr(resp, "output_text", None) or ""
    if text:
        return text
    parts: List[str] = []
    for it in getattr(resp, "output", []) or []:
        if _item_get(it, "type") != "message":
            continue
        content = _item_get(it, "content") or []
        for c in content:
            if _item_get(c, "type") in ("output_text", "text"):
                parts.append(_item_get(c, "text", "") or "")
    return "\n".join(parts)


def call_tool(
    name: str,
    args: Dict[str, Any],
    *,
    user_agent: str,
    tool_state: Dict[str, Any],
    rag_enabled: bool,
    on_trace: Optional[TraceCallback] = None,
) -> str:
    t0 = time.time()
    if on_trace:
        on_trace({"kind": "tool_call", "name": name, "args": args, "ts": time.time()})

    try:
        if name == "search_pois":
            result = tool_search_pois(
                city=args.get("city") or "",
                interests=args.get("interests") or [],
                radius_km=float(args.get("radius_km", 8)),
                limit=int(args.get("limit", 40)),
                query=args.get("query") or "",
                user_agent=user_agent,
            )
            for p in result.get("pois", []):
                tool_state.setdefault("pois", {})[p["poi_id"]] = p
            tool_state["city_key"] = result.get("city_key", tool_state.get("city_key", ""))
            tool_state["display_name"] = result.get("display_name", tool_state.get("display_name", ""))
            tool_state["center"] = result.get("center", tool_state.get("center", {}))
            if result.get("error"):
                tool_state["last_search_error"] = result["error"]
            out = json.dumps(result, ensure_ascii=False)

        elif name == "retrieve_guides":
            result = tool_retrieve_guides(
                city=args.get("city") or "",
                query=args.get("query") or "",
                k=int(args.get("k", 4)),
                user_agent=user_agent,
                enabled=rag_enabled,
            )
            for h in result.get("hits", []):
                tool_state.setdefault("chunks", {})[h["chunk_id"]] = {
                    "source": h.get("source", ""),
                    "text": h.get("text", ""),
                    "score": h.get("score", 0.0),
                }
            out = json.dumps(result, ensure_ascii=False)
        else:
            out = json.dumps({"error": f"Unknown tool: {name}"}, ensure_ascii=False)

        if on_trace:
            on_trace(
                {
                    "kind": "tool_result",
                    "name": name,
                    "elapsed_s": round(time.time() - t0, 3),
                    "ts": time.time(),
                }
            )
        return out

    except Exception as e:
        if on_trace:
            on_trace(
                {
                    "kind": "tool_error",
                    "name": name,
                    "elapsed_s": round(time.time() - t0, 3),
                    "error": str(e),
                    "ts": time.time(),
                }
            )
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def _create_response(client: OpenAI, **kwargs: Any) -> Any:
    try:
        return client.responses.create(**kwargs)
    except TypeError:
        kwargs.pop("parallel_tool_calls", None)
        kwargs.pop("tool_choice", None)
        return client.responses.create(**kwargs)


def run_trip_agent(
    client: OpenAI,
    *,
    model: str,
    user_prompt: str,
    user_agent: str,
    max_steps: int,
    rag_enabled: bool,
    on_trace: Optional[TraceCallback] = None,
    on_status: Optional[Callable[[str], None]] = None,
) -> Tuple[str, Dict[str, Any]]:
    # store=False: do not persist chats on OpenAI. That means we must resend
    # the full input list (not previous_response_id).
    input_items: List[Any] = [{"role": "user", "content": user_prompt}]
    tool_state: Dict[str, Any] = {"pois": {}, "chunks": {}, "center": {}}
    current_model = model

    for step in range(1, max_steps + 1):
        if on_trace:
            on_trace({"kind": "model_call", "step": step, "ts": time.time()})
        if on_status:
            on_status(f"Model step {step}/{max_steps}")

        kwargs: Dict[str, Any] = {
            "model": current_model,
            "tools": TOOLS,
            "input": input_items,
            "store": False,
            "parallel_tool_calls": False,
        }
        if step == 1:
            kwargs["tool_choice"] = {"type": "function", "name": "search_pois"}
        else:
            kwargs["tool_choice"] = "auto"

        try:
            resp = _create_response(client, **kwargs)
        except Exception as e:
            msg = str(e).lower()
            if current_model == "gpt-4.1-mini" and any(
                s in msg for s in ("model", "404", "not found", "does not exist", "invalid")
            ):
                if on_trace:
                    on_trace(
                        {
                            "kind": "note",
                            "message": f"{current_model} failed ({e}); retrying gpt-4o-mini",
                            "ts": time.time(),
                        }
                    )
                current_model = "gpt-4o-mini"
                kwargs["model"] = current_model
                resp = _create_response(client, **kwargs)
            else:
                raise

        input_items.extend(_to_input_item(it) for it in resp.output)

        tool_calls = [it for it in resp.output if _item_get(it, "type") == "function_call"]
        if not tool_calls:
            return _output_text(resp), tool_state

        for tc in tool_calls:
            name = _item_get(tc, "name", "")
            if on_status:
                on_status(f"Tool: {name}")
            try:
                args = json.loads(_item_get(tc, "arguments") or "{}")
            except Exception:
                args = {}
            output_str = call_tool(
                name,
                args,
                user_agent=user_agent,
                tool_state=tool_state,
                rag_enabled=rag_enabled,
                on_trace=on_trace,
            )
            input_items.append(
                {
                    "type": "function_call_output",
                    "call_id": _item_get(tc, "call_id"),
                    "output": output_str,
                }
            )

    raise RuntimeError(
        "Agent hit max_steps without a final itinerary. "
        "Enable Fast mode, reduce constraints, or raise max steps."
    )


def repair_itinerary_json(client: OpenAI, model: str, raw: str) -> str:
    """One extra call to coerce messy model text into itinerary JSON."""
    resp = client.responses.create(
        model=model,
        store=False,
        input=[
            {
                "role": "user",
                "content": (
                    "Convert the following into a single itinerary JSON object. "
                    "Output JSON only, no markdown.\n\n" + (raw or "")[:12000]
                ),
            }
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "itinerary",
                "strict": True,
                "schema": ITINERARY_JSON_SCHEMA,
            }
        },
    )
    return _output_text(resp)
