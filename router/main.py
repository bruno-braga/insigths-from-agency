from messaging import consume, publish

def callback(body, message):
    print(f"Routing to mysql-server: {body}")
    publish("mysql-server", body)
    message.ack()


if __name__ == "__main__":
    consume(callback)