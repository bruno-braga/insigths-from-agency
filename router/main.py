from messaging import consume

def callback(body, message):
    print(body)
    message.ack()


if __name__ == "__main__":
    consume(callback)