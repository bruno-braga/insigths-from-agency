import pika
import json
import sqlite3

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host="rabbitmq")
)

conn = sqlite3.connect('router.db')

channel = connection.channel()
channel.queue_declare(queue="router")


def callback(ch, method, properties, body):
    print("sending to discussion-room")

    channel.queue_declare(queue="discussion-room")
    channel.basic_publish(
        exchange="",
        routing_key="discussion-room",
        body=body.decode()
    )


if __name__ == "__main__":
    channel.basic_consume(
        queue="router",
        on_message_callback=callback,
        auto_ack=True
    )

    channel.start_consuming()
