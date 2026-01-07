import json
import uuid

import pika

from app.config import get_settings


class RabbitMQClient:
    def __init__(self) -> None:
        settings = get_settings()
        credentials = pika.PlainCredentials(settings.rabbitmq_user, settings.rabbitmq_password)
        parameters = pika.ConnectionParameters(
            host=settings.rabbitmq_host,
            port=settings.rabbitmq_port,
            credentials=credentials,
        )
        self.queue_name = settings.rabbitmq_queue_name
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self.queue_name, durable=True)

    def publish(self, payload: dict) -> str:
        message_id = str(uuid.uuid4())
        body = json.dumps({"id": message_id, "payload": payload})
        properties = pika.BasicProperties(delivery_mode=2, content_type="application/json")
        self.channel.basic_publish(
            exchange="",
            routing_key=self.queue_name,
            body=body,
            properties=properties,
        )
        return message_id

    def close(self) -> None:
        if self.connection and self.connection.is_open:
            self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
