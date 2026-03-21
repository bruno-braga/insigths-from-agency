import json
import os

from kombu import Connection, Exchange, Queue

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@rabbitmq//")

default_exchange = Exchange("", type="direct")
router_queue = Queue("router", exchange=default_exchange, routing_key="router", durable=False)


def publish_agents(agents: list[dict]) -> None:
    with Connection(RABBITMQ_URL) as conn:
        producer = conn.Producer(serializer="json")
        producer.publish(
            agents,
            exchange=default_exchange,
            routing_key="router",
            declare=[router_queue],
        )
