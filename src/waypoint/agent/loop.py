"""OpenAI Responses API agent loop with tool calling and tracing."""
from __future__ import annotations

import json
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from openai import OpenAI

from waypoint.agent.schemas_openai import TOOLS
from waypoint.agent.tools import tool_retrieve_guides, tool_search_pois


TraceCallback = Callable[[Dict[str, Any]], None]


def _item_get(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


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
                city=args["city"],
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
            out = json.dumps(result, ensure_ascii=False)

        elif name == "retrieve_guides":
            result = tool_retrieve_guides(
                city=args["city"],
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
    input_items: List[Dict[str, Any]] = [{"role": "user", "content": user_prompt}]
    tool_state: Dict[str, Any] = {"pois": {}, "chunks": {}, "center": {}}

    for step in range(1, max_steps + 1):
        if on_trace:
            on_trace({"kind": "model_call", "step": step, "ts": time.time()})
        if on_status:
            on_status(f"Model step {step}/{max_steps}")

        resp = client.responses.create(
            model=model,
            tools=TOOLS,
            input=input_items,
            store=False,
        )
        input_items += resp.output

        tool_calls = [it for it in resp.output if _item_get(it, "type") == "function_call"]
        if not tool_calls:
            text = getattr(resp, "output_text", None) or ""
            if not text:
                # Fallback: gather text from output items
                parts = []
                for it in resp.output:
                    if _item_get(it, "type") == "message":
                        content = _item_get(it, "content") or []
                        for c in content:
                            if _item_get(c, "type") in ("output_text", "text"):
                                parts.append(_item_get(c, "text", ""))
                text = "\n".join(parts)
            return text, tool_state

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
