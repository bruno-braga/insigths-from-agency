from __future__ import annotations

import json
from typing import Any, Iterator

from agno.run.agent import (
    IntermediateRunContentEvent,
    RunCompletedEvent,
    RunContentEvent,
    RunErrorEvent,
    ToolCallCompletedEvent,
    ToolCallStartedEvent,
)


def _trunc(obj: Any, n: int = 600) -> str:
    s = obj if isinstance(obj, str) else json.dumps(obj, default=str)
    return s if len(s) <= n else s[: n - 1] + "…"


def iter_tui_events(agent_name: str, stream: Iterator[Any]) -> Iterator[dict[str, str]]:
    """Turn Agno run stream into JSON-serializable dicts for the TUI."""
    content_buf: list[str] = []

    for ev in stream:
        if isinstance(ev, (RunContentEvent, IntermediateRunContentEvent)):
            c = ev.content
            if c is None:
                continue
            piece = c if isinstance(c, str) else str(c)
            if piece:
                content_buf.append(piece)
            continue

        if content_buf:
            text = "".join(content_buf)
            content_buf = []
            if text.strip():
                yield {"kind": "assistant", "agent": agent_name, "text": text}

        if isinstance(ev, ToolCallStartedEvent):
            t = ev.tool
            if t is None:
                continue
            name = getattr(t, "tool_name", "?")
            args = getattr(t, "tool_args", None)
            yield {
                "kind": "tool_start",
                "agent": agent_name,
                "text": f"{name}({_trunc(args, 400)})",
            }
        elif isinstance(ev, ToolCallCompletedEvent):
            t = ev.tool
            name = getattr(t, "tool_name", "?") if t else "?"
            raw = ev.content if ev.content is not None else getattr(t, "result", None)
            yield {
                "kind": "tool_done",
                "agent": agent_name,
                "text": f"{name} → {_trunc(raw, 800)}",
            }
        elif isinstance(ev, RunErrorEvent):
            msg = ev.content or ev.error_type or "error"
            yield {"kind": "error", "agent": agent_name, "text": str(msg)}
        elif isinstance(ev, RunCompletedEvent):
            yield {"kind": "done", "agent": agent_name, "text": ""}

    if content_buf:
        text = "".join(content_buf)
        if text.strip():
            yield {"kind": "assistant", "agent": agent_name, "text": text}
