import os
from typing import Callable
from kombu import Connection, Exchange, Queue, Message

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@rabbitmq//")

default_exchange = Exchange("", type="direct")

queue = Queue("router", routing_key="router", durable=True)

def consume(callback: Callable[[bytes, Message], None]) -> None:
    with Connection(RABBITMQ_URL) as connection:
        with connection.Consumer(queue, callbacks=[callback]):
            while True:
                connection.drain_events()

def publish(routing_key: str, body) -> None:
    with Connection(RABBITMQ_URL) as connection:
        with connection.Producer() as producer:
            producer.publish(
                body,
                routing_key=routing_key,
                exchange=default_exchange,
                serializer="json",
                declare=[Queue(routing_key, routing_key=routing_key, durable=True)],
            )