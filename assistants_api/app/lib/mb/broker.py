import pika
import os

RABBITMQ_DEFAULT_USER = os.getenv("RABBITMQ_DEFAULT_USER")
RABBITMQ_DEFAULT_PASS = os.getenv("RABBITMQ_DEFAULT_PASS")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_PORT = os.getenv("RABBITMQ_PORT")


class RabbitMQBroker:
    def __init__(self):
        credentials = pika.PlainCredentials(
            RABBITMQ_DEFAULT_USER, RABBITMQ_DEFAULT_PASS
        )
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                credentials=credentials,
                heartbeat=30,
            )
        )
        self.channel = self.connection.channel()

    def publish(self, queue_name: str, message: str):
        self.channel.queue_declare(queue=queue_name, durable=True)
        self.channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=message,
            properties=pika.BasicProperties(
                delivery_mode=1,
            ),
        )

    def close_connection(self):
        self.connection.close()


def get_broker():
    return RabbitMQBroker()
