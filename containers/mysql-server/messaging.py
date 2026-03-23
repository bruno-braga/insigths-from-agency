import os
from typing import Callable
from kombu import Connection, Queue, Message

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@rabbitmq//")

queue = Queue("mysql-server", routing_key="mysql-server", durable=True)

def consume(callback: Callable[[bytes, Message], None]) -> None:
    with Connection(RABBITMQ_URL) as connection:
        with connection.Consumer(queue, callbacks=[callback]):
            while True:
                connection.drain_events()
