import json
import os
from typing import Any, Union

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.deepseek import DeepSeek
from agno.tools.memory import MemoryTools
from agno.tools.shell import ShellTools
from kombu import Connection

from messaging import RABBITMQ_URL, consume, publish_tui_event
from stream_events import iter_tui_events

# TUI dispatch only sends name/model/instructions; no separate user message.
_DEFAULT_RUN_MESSAGE = (
    "Proceed according to your instructions. Use tools when needed and summarize what you did."
)


def _normalize_instructions(raw: Any) -> Union[str, list[str]]:
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        return [str(x) for x in raw]
    return str(raw)


def _resolve_model(model_val: Any) -> Union[str, Any]:
    if not isinstance(model_val, str):
        return model_val
    if ":" in model_val:
        return model_val
    return DeepSeek(id=model_val)


def _specs_from_payload(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []


def _payload_from_body(body: Any) -> Any | None:
    if isinstance(body, (dict, list)):
        return body
    if isinstance(body, (bytes, bytearray)):
        body = body.decode()
    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return None
    return None


def _run_stream_to_tui(producer: Any, agent_name: str, response: Any) -> None:
    publish_tui_event(
        producer,
        {"kind": "run_start", "agent": agent_name, "text": ""},
    )
    try:
        it = iter(response)
    except TypeError:
        text = getattr(response, "content", None) or str(response)
        publish_tui_event(
            producer,
            {"kind": "assistant", "agent": agent_name, "text": text},
        )
        return
    for event in iter_tui_events(agent_name, it):
        publish_tui_event(producer, event)


def callback(body, message):
    payload = _payload_from_body(body)
    if payload is None:
        print(f"Unsupported or invalid message body type: {type(body).__name__}")
        message.ack()
        return

    specs = _specs_from_payload(payload)
    if not specs:
        print("Body must be a JSON object or a non-empty array of objects.")
        message.ack()
        return

    db = SqliteDb(db_file=os.environ.get("DB_PATH", "mysql_server_agno.db"))
    memory_tools = MemoryTools(db=db)

    with Connection(RABBITMQ_URL) as conn:
        with conn.Producer(serializer="json") as producer:
            for spec in specs:
                missing = [k for k in ("name", "instructions", "model") if k not in spec]
                if missing:
                    print(f"Skipping agent: missing {', '.join(missing)}")
                    continue

                name = str(spec["name"])
                agent = Agent(
                    name=name,
                    instructions=_normalize_instructions(spec["instructions"]),
                    model=_resolve_model(spec["model"]),
                    tools=[ShellTools(), memory_tools],
                    db=db,
                    stream=True,
                    user_id=spec.get("user_id") or spec.get("id") or name,
                )

                run_input = (
                    spec.get("input")
                    or spec.get("task")
                    or spec.get("message")
                    or spec.get("query")
                    or _DEFAULT_RUN_MESSAGE
                )
                print(f"Running agent name={name!r} (stream → tui-stream) …")
                response = agent.run(str(run_input), stream=True)
                _run_stream_to_tui(producer, name, response)

    message.ack()


if __name__ == "__main__":
    consume(callback)
