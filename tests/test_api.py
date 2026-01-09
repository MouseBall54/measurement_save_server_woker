import app.api.routes as routes


def test_ingest_queues_message(client, monkeypatch):
    class DummyClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def publish(self, payload):
            assert payload["product_name"] == "P1"
            return "msg-123"

    monkeypatch.setattr(routes, "RabbitMQClient", DummyClient)

    response = client.post(
        "/ingest",
        json={
            "product_name": "P1",
            "site_name": "HC",
            "node_name": "2NM",
            "module_name": "PC",
            "recipe_name": "RCP",
            "recipe_version": "1.0",
            "file_path": "/data/measurements/measure1.csv",
            "file_name": "measure1.csv",
            "lot_name": "LOT001",
            "wf_number": 12,
            "measurements": [
                {
                    "metric_name": "THK",
                    "metric_unit": "nm",
                    "class_name": "CLASS_A",
                    "measure_item": "ITEM_1",
                    "measurable": True,
                    "x_index": 0,
                    "y_index": 0,
                    "x_0": 0.1,
                    "y_0": 0.2,
                    "x_1": 0.3,
                    "y_1": 0.4,
                    "value": 1.23,
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "queued", "id": "msg-123"}


def test_ingest_validation_error(client):
    response = client.post("/ingest", json={"product_name": "P1"})
    assert response.status_code == 422


def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_ok(client, monkeypatch):
    monkeypatch.setattr(routes, "check_db", lambda: True)
    monkeypatch.setattr(routes, "check_rabbitmq", lambda: True)
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_ready_not_ok(client, monkeypatch):
    monkeypatch.setattr(routes, "check_db", lambda: False)
    monkeypatch.setattr(routes, "check_rabbitmq", lambda: True)
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "details": {"db": False, "rabbitmq": True},
    }
