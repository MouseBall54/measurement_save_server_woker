# Work Checklist

- [x] Add `app/` package structure with `api/`, `queue/`, `worker/`, `db/`
- [x] Place schema file at `app/db/schema.sql` (copy from `create_db.sql`)
- [x] Implement `app/config.py` environment settings
- [x] Implement `app/db/session.py` DB engine + session
- [x] Implement `app/db/models.py` (or SQL helpers) aligned to schema
- [x] Implement RabbitMQ client in `app/queue/rabbitmq.py`
- [x] Implement `POST /ingest` route and request schema
- [x] Implement worker consumer and DB insert logic
- [x] Add pytest fixtures in `tests/conftest.py`
- [x] Add `tests/test_api.py` with publisher mocks
- [x] Add `tests/test_queue.py` with publish unit test
- [x] Add `tests/test_worker.py` for message processing + DB insert
- [x] Add README with env vars, run steps, curl example
