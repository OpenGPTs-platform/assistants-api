from concurrent.futures import ThreadPoolExecutor
import pika
import os
from dotenv import load_dotenv
from run_executor.main import ExecuteRun
import json
import time

load_dotenv()

MAX_WORKERS = int(os.getenv("MAX_WORKERS", 4))
RABBITMQ_DEFAULT_USER = os.getenv("RABBITMQ_DEFAULT_USER")
RABBITMQ_DEFAULT_PASS = os.getenv("RABBITMQ_DEFAULT_PASS")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))


class RabbitMQConsumer:
    def __init__(self, max_workers=4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.connect()

    def connect(self):
        credentials = pika.PlainCredentials(
            RABBITMQ_DEFAULT_USER, RABBITMQ_DEFAULT_PASS
        )
        while True:
            try:
                self.connection = pika.BlockingConnection(
                    pika.ConnectionParameters(
                        host=RABBITMQ_HOST,
                        port=RABBITMQ_PORT,
                        credentials=credentials,
                        heartbeat=600,
                    )
                )
                self.channel = self.connection.channel()
                self.channel.basic_qos(prefetch_count=self.max_workers)
                break
            except pika.exceptions.AMQPConnectionError as e:
                print(f"Connection error: {e}, retrying in 5 seconds...")
                time.sleep(5)

    def process_message(self, body):
        try:
            message = body.decode("utf-8")
            data = json.loads(message)
            print(f"\n\nProcessing {data}")
            run = ExecuteRun(data["thread_id"], data["run_id"])
            run.execute()
        except json.JSONDecodeError as e:
            print(f"Failed to decode JSON: {e}")

    def callback(self, ch, method, properties, body):
        self.executor.submit(self.process_message_and_ack, body, ch, method)

    def process_message_and_ack(self, body, ch, method):
        try:
            self.process_message(body)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            print(f"Failed to process message {body}: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def start_consuming(self, queue_name):
        while True:
            try:
                self.channel.queue_declare(queue=queue_name, durable=True)
                self.channel.basic_consume(
                    queue=queue_name,
                    on_message_callback=self.callback,
                    auto_ack=False,
                )
                print("Waiting for messages. To exit press CTRL+C")
                self.channel.start_consuming()
            except pika.exceptions.ConnectionClosedByBroker:
                print("Connection closed by broker, reconnecting...")
                self.connect()
            except pika.exceptions.StreamLostError:
                print("Stream lost, reconnecting...")
                self.connect()
            except Exception as e:
                print(f"Exception in consuming: {e}")
                self.connect()


if __name__ == "__main__":
    consumer = RabbitMQConsumer(max_workers=MAX_WORKERS)
    consumer.start_consuming("runs_queue")
