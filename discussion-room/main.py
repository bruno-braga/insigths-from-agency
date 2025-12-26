import pika

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host="rabbitmq")
)

channel = connection.channel()
channel.queue_declare(queue="discussion-room")


def callback(ch, method, properties, body):
    print("entering discussion-room")

    print(body.decode())


if __name__ == "__main__":
    channel.basic_consume(
        queue="discussion-room",
        on_message_callback=callback,
        auto_ack=True
    )

    channel.start_consuming()
