from messaging import consume

def callback(body, message):
    print(f"Received from router: {body}")
    print(body)
    message.ack()


if __name__ == "__main__":
    consume(callback)
