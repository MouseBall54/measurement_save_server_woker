import json
import logging
import os
from datetime import datetime

import pika
from sqlalchemy import func, select, text
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.config import get_settings
from app.db.models import (
    LotWf,
    MeasurementFile,
    MeasurementItem,
    MeasurementRawData,
    MeasurementRecipe,
    MetricType,
    ProductName,
    SpasModule,
    SpasNode,
    SpasReference,
    SpasSite,
)
from app.db.session import SessionLocal
from app.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)
WORKER_ID = os.getenv("WORKER_ID")


def get_or_create(session, model, defaults=None, **filters):
    instance = session.execute(select(model).filter_by(**filters)).scalar_one_or_none()
    if instance:
        return instance
    params = dict(filters)
    if defaults:
        params.update(defaults)
    instance = model(**params)
    session.add(instance)
    nested = session.begin_nested()
    try:
        session.flush()
        nested.commit()
    except IntegrityError:
        nested.rollback()
        session.expire_all()
        instance = session.execute(select(model).filter_by(**filters)).scalar_one()
    return instance


def upsert_and_get_id(session, model, values: dict, update_fields: dict, lookup_filters: dict):
    if session.bind.dialect.name == "mysql":
        stmt = mysql_insert(model).values(**values)
        if update_fields:
            stmt = stmt.on_duplicate_key_update(**update_fields)
        else:
            stmt = stmt.prefix_with("IGNORE")
        session.execute(stmt)
        return session.execute(select(model).filter_by(**lookup_filters)).scalar_one()

    instance = session.execute(select(model).filter_by(**lookup_filters)).scalar_one_or_none()
    if instance:
        for key, value in update_fields.items():
            setattr(instance, key, value)
        return instance
    instance = model(**values)
    session.add(instance)
    session.flush()
    return instance


def process_message(session, payload: dict) -> dict:
    product = upsert_and_get_id(
        session,
        ProductName,
        values={"name": payload["product_name"], "is_active": True},
        update_fields={"is_active": True},
        lookup_filters={"name": payload["product_name"]},
    )
    site = upsert_and_get_id(
        session,
        SpasSite,
        values={"name": payload["site_name"], "is_active": True},
        update_fields={"is_active": True},
        lookup_filters={"name": payload["site_name"]},
    )
    node = upsert_and_get_id(
        session,
        SpasNode,
        values={"name": payload["node_name"], "is_active": True},
        update_fields={"is_active": True},
        lookup_filters={"name": payload["node_name"]},
    )
    module = upsert_and_get_id(
        session,
        SpasModule,
        values={"name": payload["module_name"], "is_active": True},
        update_fields={"is_active": True},
        lookup_filters={"name": payload["module_name"]},
    )
    recipe = upsert_and_get_id(
        session,
        MeasurementRecipe,
        values={
            "name": payload["recipe_name"],
            "version": payload["recipe_version"],
        },
        update_fields={},
        lookup_filters={
            "name": payload["recipe_name"],
            "version": payload["recipe_version"],
        },
    )

    reference = upsert_and_get_id(
        session,
        SpasReference,
        values={
            "product_id": product.id,
            "site_id": site.id,
            "node_id": node.id,
            "module_id": module.id,
        },
        update_fields={},
        lookup_filters={
            "product_id": product.id,
            "site_id": site.id,
            "node_id": node.id,
            "module_id": module.id,
        },
    )

    lot_name = payload.get("lot_name")
    wf_number = payload.get("wf_number")
    lot_wf = None
    if lot_name is not None and wf_number is not None:
        lot_wf = upsert_and_get_id(
            session,
            LotWf,
            values={"lot_name": lot_name, "wf_number": wf_number},
            update_fields={},
            lookup_filters={"lot_name": lot_name, "wf_number": wf_number},
        )

    desired_lot_wf_id = lot_wf.id if lot_wf else None
    measurement_file = upsert_and_get_id(
        session,
        MeasurementFile,
        values={
            "file_path": payload["file_path"],
            "recipe_id": recipe.id,
            "file_name": payload["file_name"],
            "reference_id": reference.id,
            "lot_wf_id": desired_lot_wf_id,
        },
        update_fields={
            "file_name": payload["file_name"],
            "reference_id": reference.id,
            "lot_wf_id": desired_lot_wf_id,
        },
        lookup_filters={
            "file_path": payload["file_path"],
            "recipe_id": recipe.id,
        },
    )

    measurements = payload.get("measurements", [])
    inserted = 0
    for measurement in measurements:
        metric_unit = measurement.get("metric_unit")
        metric_type = upsert_and_get_id(
            session,
            MetricType,
            values={"name": measurement["metric_name"], "unit": metric_unit, "is_active": True},
            update_fields={"unit": metric_unit, "is_active": True},
            lookup_filters={"name": measurement["metric_name"]},
        )

        measurement_item = upsert_and_get_id(
            session,
            MeasurementItem,
            values={
                "class_name": measurement["class_name"],
                "measure_item": measurement["measure_item"],
                "metric_type_id": metric_type.id,
                "is_active": True,
            },
            update_fields={"is_active": True},
            lookup_filters={
                "class_name": measurement["class_name"],
                "measure_item": measurement["measure_item"],
                "metric_type_id": metric_type.id,
            },
        )

        raw_values = {
            "file_id": measurement_file.id,
            "item_id": measurement_item.id,
            "measurable": measurement.get("measurable", True),
            "x_index": measurement["x_index"],
            "y_index": measurement["y_index"],
            "x_0": measurement["x_0"],
            "y_0": measurement["y_0"],
            "x_1": measurement["x_1"],
            "y_1": measurement["y_1"],
            "value": measurement["value"],
        }
        raw_updates = {
            "measurable": measurement.get("measurable", True),
            "x_0": measurement["x_0"],
            "y_0": measurement["y_0"],
            "x_1": measurement["x_1"],
            "y_1": measurement["y_1"],
            "value": measurement["value"],
        }
        if session.bind.dialect.name == "mysql":
            raw_stmt = mysql_insert(MeasurementRawData).values(**raw_values)
            raw_stmt = raw_stmt.on_duplicate_key_update(**raw_updates)
            session.execute(raw_stmt)
        else:
            existing = session.execute(
                select(MeasurementRawData).filter_by(
                    file_id=measurement_file.id,
                    item_id=measurement_item.id,
                    x_index=measurement["x_index"],
                    y_index=measurement["y_index"],
                )
            ).scalar_one_or_none()
            if existing:
                for key, value in raw_updates.items():
                    setattr(existing, key, value)
            else:
                session.add(MeasurementRawData(**raw_values))
        inserted += 1

    measurement_file.updated_at = func.now()

    return {
        "file_path": payload.get("file_path"),
        "measurement_count": len(measurements),
        "inserted_count": inserted,
    }


def main() -> None:
    settings = get_settings()
    credentials = pika.PlainCredentials(settings.rabbitmq_user, settings.rabbitmq_password)
    parameters = pika.ConnectionParameters(
        host=settings.rabbitmq_host,
        port=settings.rabbitmq_port,
        credentials=credentials,
    )

    logger.info("Worker starting", extra={"event": "worker_start"})

    try:
        connection = pika.BlockingConnection(parameters)
        logger.info("RabbitMQ connected", extra={"event": "rabbitmq_connected"})
    except Exception as exc:
        logger.exception("RabbitMQ connection failed: %s", exc, extra={"event": "rabbitmq_error"})
        raise

    channel = connection.channel()
    channel.queue_declare(queue=settings.rabbitmq_queue_name, durable=True)
    channel.basic_qos(prefetch_count=1)

    try:
        session = SessionLocal()
        session.execute(text("SELECT 1"))
        session.close()
        logger.info("DB connected", extra={"event": "db_connected"})
    except Exception as exc:
        logger.exception("DB connection failed: %s", exc, extra={"event": "db_error"})
        connection.close()
        raise

    def callback(ch, method, properties, body):
        session = SessionLocal()
        try:
            message = json.loads(body)
            payload = message.get("payload", {})
            worker_id = WORKER_ID or f"pid:{os.getpid()}"
            logger.info(
                "Worker received message",
                extra={
                    "event": "received",
                    "file_path": payload.get("file_path"),
                    "message_id": message.get("id"),
                    "worker_id": worker_id,
                },
            )
            result = process_message(session, payload)
            session.commit()
            logger.info(
                "Worker processed message",
                extra={
                    "event": "processed",
                    "file_path": result["file_path"],
                    "measurement_count": result["measurement_count"],
                    "inserted_count": result["inserted_count"],
                    "message_id": message.get("id"),
                    "worker_id": worker_id,
                },
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except (json.JSONDecodeError, SQLAlchemyError, KeyError) as exc:
            session.rollback()
            logger.exception(
                "Failed to process message: %s",
                exc,
                extra={"event": "error", "file_path": payload.get("file_path")},
            )
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        finally:
            session.close()

    channel.basic_consume(queue=settings.rabbitmq_queue_name, on_message_callback=callback)
    logger.info("Worker started. Waiting for messages...")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("Worker stopping...")
        channel.stop_consuming()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
