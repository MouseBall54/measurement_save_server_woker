from app.queue import rabbitmq


def test_publish_persists_message(monkeypatch):
    class DummyChannel:
        def __init__(self):
            self.published = None

        def queue_declare(self, queue, durable):
            self.queue = queue
            self.durable = durable

        def basic_publish(self, exchange, routing_key, body, properties):
            self.published = {
                "exchange": exchange,
                "routing_key": routing_key,
                "body": body,
                "properties": properties,
            }

    class DummyConnection:
        def __init__(self, parameters):
            self.parameters = parameters
            self._channel = DummyChannel()
            self.is_open = True

        def channel(self):
            return self._channel

        def close(self):
            self.is_open = False

    monkeypatch.setattr(rabbitmq.pika, "BlockingConnection", DummyConnection)

    client = rabbitmq.RabbitMQClient()
    message_id = client.publish({"key": "value"})

    assert message_id
    published = client.channel.published
    assert published["exchange"] == ""
    assert published["routing_key"] == client.queue_name
    assert published["properties"].delivery_mode == 2
    assert published["properties"].content_type == "application/json"
