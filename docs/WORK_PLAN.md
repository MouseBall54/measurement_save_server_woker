# Work Plan

## Source Schema Summary (from create_db.sql)
The schema file is `app/db/schema.sql` (copied from `create_db.sql`). It defines these tables and relationships:

- lot_wf: lot_name + wf_number unique, created_at; referenced by measurement_files.lot_wf_id
- spas_nodes: node master, unique name, is_active
- spas_modules: module master, unique name, is_active
- spas_sites: site master, unique name, is_active
- measurement_recipe: recipe name + version unique, created_at
- product_names: product master, unique name, is_active
- spas_references: composite of product/site/node/module; unique combo; referenced by measurement_files.reference_id
- measurement_files: file metadata; unique (file_path, recipe_id); references spas_references, lot_wf, measurement_recipe
- metric_types: metric name + unit + is_active
- measurement_items: class_name + measure_item + metric_type_id unique; references metric_types
- measurement_raw_data: fact table for points; unique (file_id, item_id, x_index, y_index); references measurement_files and measurement_items

Type notes (from SQLAlchemy Core docs via Context7):
- Use generic SQLAlchemy types where possible (String, Integer, BigInteger, Boolean, DateTime, Float/Double)
- MySQL-specific behavior is handled by the dialect; String(length) maps to VARCHAR(length)
- Boolean may map to BIT/SMALLINT on some backends; for MySQL, TINYINT(1) is typical

## Implementation Plan
1) Project scaffolding
   - Create `app/` package with `api/`, `queue/`, `worker/`, `db/` subpackages and `config.py`
   - Place the schema file under `app/db/schema.sql` (copy or move from `create_db.sql`)

2) Configuration
   - Read RabbitMQ and DB connection settings from environment variables
   - Provide sane defaults for local dev where possible

3) Database layer
   - Define SQLAlchemy models or explicit insert SQL aligned with the schema
   - Create DB session management in `app/db/session.py`
   - Provide helpers to resolve or insert master data (product/site/node/module/recipe) and return their IDs

4) Queue layer
   - Implement RabbitMQ client with durable queue and persistent messages
   - Serialize messages as JSON and include a correlation/message ID

5) FastAPI API
   - Implement `POST /ingest` that validates input and enqueues messages only
   - Return a `queued` response with an ID

6) Worker
   - Consume messages, parse JSON, insert into DB, and ACK on success
   - NACK on failure (with requeue) and log errors

7) Tests
   - Add pytest + pytest-asyncio
   - Unit tests for API enqueue behavior (mock publisher)
   - Unit tests for RabbitMQ publish behavior (mock channel)
   - Unit tests for worker message processing and DB insert logic (DB test session)

8) Documentation
   - README with environment variables, local run steps, and curl example
   - Optional docker-compose instructions
