import os
import threading
from typing import Any

from kombu import Connection, Exchange, Queue

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@rabbitmq//")

default_exchange = Exchange("", type="direct")
router_queue = Queue("router", exchange=default_exchange, routing_key="router", durable=True)
tui_stream_queue = Queue("tui-stream", routing_key="tui-stream", durable=True)


def publish_agents(agents: list[dict]) -> None:
    with Connection(RABBITMQ_URL) as conn:
        producer = conn.Producer(serializer="json")
        producer.publish(
            agents,
            exchange=default_exchange,
            routing_key="router",
            declare=[router_queue],
        )


def run_tui_stream_loop(app: Any, stop_event: threading.Event) -> None:
    """Blocking loop: forward `tui-stream` messages to the Textual app (daemon thread)."""

    def callback(body: Any, message: Any) -> None:
        try:
            if isinstance(body, dict):
                app.call_from_thread(app._on_stream_event, body)
        finally:
            message.ack()

    with Connection(RABBITMQ_URL) as connection:
        with connection.Consumer(tui_stream_queue, callbacks=[callback]):
            while not stop_event.is_set():
                try:
                    connection.drain_events(timeout=0.5)
                except Exception:
                    pass
