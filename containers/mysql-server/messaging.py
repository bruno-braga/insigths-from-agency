import os
from typing import Any, Callable

from kombu import Connection, Exchange, Message, Queue

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@rabbitmq//")

default_exchange = Exchange("", type="direct")

queue = Queue("mysql-server", routing_key="mysql-server", durable=True)

tui_stream_queue = Queue("tui-stream", routing_key="tui-stream", durable=True)


def consume(callback: Callable[[bytes, Message], None]) -> None:
    with Connection(RABBITMQ_URL) as connection:
        with connection.Consumer(queue, callbacks=[callback]):
            while True:
                connection.drain_events()


def publish_tui_event(producer: Any, event: dict) -> None:
    producer.publish(
        event,
        exchange=default_exchange,
        routing_key="tui-stream",
        serializer="json",
        declare=[tui_stream_queue],
    )
