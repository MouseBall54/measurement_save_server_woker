# Measurement Save Server Worker

## Environment Variables

- `RABBITMQ_HOST` (default: `localhost`)
- `RABBITMQ_PORT` (default: `5672`)
- `RABBITMQ_USER` (default: `guest`)
- `RABBITMQ_PASSWORD` (default: `guest`)
- `RABBITMQ_QUEUE_NAME` (default: `measurement_ingest`)
- `DATABASE_URL` (default: `mysql+pymysql://user:password@localhost:3306/measure_system_3`)

## Local Run

1) Start RabbitMQ and MySQL
2) Initialize DB schema

```bash
mysql -u <user> -p < app/db/schema.sql
```

3) Start the API server

```bash
uvicorn app.main:app --reload
```

4) Start the worker

```bash
python -m app.worker.worker
```

5) Send an ingest request

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
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
    "metric_name": "THK",
    "metric_unit": "nm",
    "class_name": "CLASS_A",
    "measure_item": "ITEM_1",
    "measurable": true,
    "x_index": 0,
    "y_index": 0,
    "x_0": 0.1,
    "y_0": 0.2,
    "x_1": 0.3,
    "y_1": 0.4,
    "value": 1.23
  }'
```

## Tests

```bash
pytest -q
```
