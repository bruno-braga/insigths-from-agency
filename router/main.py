import json
import pika
import os

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models.agents import Agents, Base


engine = create_engine("sqlite:///router.db")

connection = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq"))
channel = connection.channel()

channel.queue_declare(queue="router")


def callback(ch, method, properties, body):
    print(f"Received {body.decode()}")

    print("sending to classroom2")
    channel.queue_declare(queue="classroom2")
    channel.basic_publish(exchange="", routing_key="classroom2", body=body.decode())
    # data = json.loads(body.decode())

    # print(data)
    # Base.metadata.create_all(engine)

    # with Session(engine) as session:
    #     for item in data:
    #         agent = Agents(model_id="student", memory=item["memory"])
    #         session.add_all([agent])
    #         session.commit()


if __name__ == "__main__":
    print("consuming")
    channel.basic_consume(queue="router", on_message_callback=callback, auto_ack=True)
    channel.start_consuming()
