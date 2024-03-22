from broker import RabbitMQBroker


def enqueue_run(broker: RabbitMQBroker, queue_name: str, run_id: str):
    """Enqueue a run ID to a specified queue."""
    broker.publish(queue_name=queue_name, message=run_id)


# Add more actions as needed
