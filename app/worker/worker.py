import json
import logging

import pika
from sqlalchemy import select
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


def process_message(session, payload: dict) -> None:
    product = get_or_create(session, ProductName, name=payload["product_name"])
    site = get_or_create(session, SpasSite, name=payload["site_name"])
    node = get_or_create(session, SpasNode, name=payload["node_name"])
    module = get_or_create(session, SpasModule, name=payload["module_name"])
    recipe = get_or_create(
        session,
        MeasurementRecipe,
        name=payload["recipe_name"],
        version=payload["recipe_version"],
    )
    reference = get_or_create(
        session,
        SpasReference,
        product_id=product.id,
        site_id=site.id,
        node_id=node.id,
        module_id=module.id,
    )

    lot_name = payload.get("lot_name")
    wf_number = payload.get("wf_number")
    lot_wf = None
    if lot_name is not None and wf_number is not None:
        lot_wf = get_or_create(session, LotWf, lot_name=lot_name, wf_number=wf_number)

    measurement_file = get_or_create(
        session,
        MeasurementFile,
        file_path=payload["file_path"],
        recipe_id=recipe.id,
        defaults={
            "file_name": payload["file_name"],
            "reference_id": reference.id,
            "lot_wf_id": lot_wf.id if lot_wf else None,
        },
    )

    measurements = payload.get("measurements", [])
    for measurement in measurements:
        metric_type = get_or_create(
            session,
            MetricType,
            name=measurement["metric_name"],
            defaults={"unit": measurement.get("metric_unit")},
        )

        measurement_item = get_or_create(
            session,
            MeasurementItem,
            class_name=measurement["class_name"],
            measure_item=measurement["measure_item"],
            metric_type_id=metric_type.id,
        )

        existing = session.execute(
            select(MeasurementRawData).filter_by(
                file_id=measurement_file.id,
                item_id=measurement_item.id,
                x_index=measurement["x_index"],
                y_index=measurement["y_index"],
            )
        ).scalar_one_or_none()

        if existing:
            continue

        raw = MeasurementRawData(
            file_id=measurement_file.id,
            item_id=measurement_item.id,
            measurable=measurement.get("measurable", True),
            x_index=measurement["x_index"],
            y_index=measurement["y_index"],
            x_0=measurement["x_0"],
            y_0=measurement["y_0"],
            x_1=measurement["x_1"],
            y_1=measurement["y_1"],
            value=measurement["value"],
        )
        session.add(raw)


def main() -> None:
    settings = get_settings()
    credentials = pika.PlainCredentials(settings.rabbitmq_user, settings.rabbitmq_password)
    parameters = pika.ConnectionParameters(
        host=settings.rabbitmq_host,
        port=settings.rabbitmq_port,
        credentials=credentials,
    )

    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    channel.queue_declare(queue=settings.rabbitmq_queue_name, durable=True)
    channel.basic_qos(prefetch_count=1)

    def callback(ch, method, properties, body):
        session = SessionLocal()
        try:
            message = json.loads(body)
            payload = message.get("payload", {})
            process_message(session, payload)
            session.commit()
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except (json.JSONDecodeError, SQLAlchemyError, KeyError) as exc:
            session.rollback()
            logger.exception("Failed to process message: %s", exc)
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
