from sqlalchemy import select

from app.db.models import (
    MeasurementFile,
    MeasurementItem,
    MeasurementRawDataCurrent,
    MeasurementRawDataHistory,
    MetricType,
)
from app.worker import worker
from app.worker.worker import process_message


def test_process_message_inserts_raw_data(db_session):
    payload = {
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
                "x_1": 0.3,
                "y_0": 0.2,
                "y_1": 0.4,
                "value": 1.23,
            },
            {
                "metric_name": "THK",
                "metric_unit": "nm",
                "class_name": "CLASS_A",
                "measure_item": "ITEM_1",
                "measurable": True,
                "x_index": 1,
                "y_index": 0,
                "x_0": 0.2,
                "x_1": 0.4,
                "y_0": 0.3,
                "y_1": 0.5,
                "value": 2.34,
            },
        ],
    }

    process_message(db_session, payload)
    db_session.commit()

    current = db_session.execute(select(MeasurementRawDataCurrent)).scalars().all()
    history = db_session.execute(select(MeasurementRawDataHistory)).scalars().all()
    assert len(current) == 2
    assert len(history) == 2
    values = sorted(item.value for item in current)
    assert values == [1.23, 2.34]


def test_process_message_idempotent(db_session):
    payload = {
        "product_name": "P1",
        "site_name": "HC",
        "node_name": "2NM",
        "module_name": "PC",
        "recipe_name": "RCP",
        "recipe_version": "1.0",
        "file_path": "/data/measurements/measure1.csv",
        "file_name": "measure1.csv",
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
                "x_1": 0.3,
                "y_0": 0.2,
                "y_1": 0.4,
                "value": 1.23,
            }
        ],
    }

    process_message(db_session, payload)
    process_message(db_session, payload)
    db_session.commit()

    current = db_session.execute(select(MeasurementRawDataCurrent)).scalars().all()
    history = db_session.execute(select(MeasurementRawDataHistory)).scalars().all()
    assert len(current) == 1
    assert len(history) == 2


def test_process_message_updates_existing(db_session):
    payload = {
        "product_name": "P1",
        "site_name": "HC",
        "node_name": "2NM",
        "module_name": "PC",
        "recipe_name": "RCP",
        "recipe_version": "1.0",
        "file_path": "/data/measurements/measure1.csv",
        "file_name": "old.csv",
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
                "x_1": 0.3,
                "y_0": 0.2,
                "y_1": 0.4,
                "value": 1.23,
            }
        ],
    }

    process_message(db_session, payload)
    db_session.commit()

    update_payload = {
        **payload,
        "file_name": "new.csv",
        "measurements": [
            {
                "metric_name": "THK",
                "metric_unit": "nm",
                "class_name": "CLASS_A",
                "measure_item": "ITEM_1",
                "measurable": False,
                "x_index": 0,
                "y_index": 0,
                "x_0": 1.1,
                "x_1": 1.3,
                "y_0": 1.2,
                "y_1": 1.4,
                "value": 9.99,
            }
        ],
    }

    process_message(db_session, update_payload)
    db_session.commit()

    file_row = db_session.execute(select(MeasurementFile)).scalar_one()
    assert file_row.file_name == "new.csv"

    current = db_session.execute(select(MeasurementRawDataCurrent)).scalar_one()
    assert current.measurable is False
    assert current.value == 9.99


def test_process_message_reactivates_measurement_item(db_session):
    metric_type = MetricType(name="THK", unit="nm", is_active=True)
    db_session.add(metric_type)
    db_session.flush()

    item = MeasurementItem(
        class_name="CLASS_A",
        measure_item="ITEM_1",
        metric_type_id=metric_type.id,
        is_active=False,
    )
    db_session.add(item)
    db_session.commit()

    payload = {
        "product_name": "P1",
        "site_name": "HC",
        "node_name": "2NM",
        "module_name": "PC",
        "recipe_name": "RCP",
        "recipe_version": "1.0",
        "file_path": "/data/measurements/measure1.csv",
        "file_name": "measure1.csv",
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
                "x_1": 0.3,
                "y_0": 0.2,
                "y_1": 0.4,
                "value": 1.23,
            }
        ],
    }

    process_message(db_session, payload)
    db_session.commit()

    updated_item = db_session.get(MeasurementItem, item.id)
    assert updated_item.is_active is True


def test_process_message_updates_metric_type(db_session):
    metric_type = MetricType(name="THK", unit="um", is_active=False)
    db_session.add(metric_type)
    db_session.commit()

    payload = {
        "product_name": "P1",
        "site_name": "HC",
        "node_name": "2NM",
        "module_name": "PC",
        "recipe_name": "RCP",
        "recipe_version": "1.0",
        "file_path": "/data/measurements/measure1.csv",
        "file_name": "measure1.csv",
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
                "x_1": 0.3,
                "y_0": 0.2,
                "y_1": 0.4,
                "value": 1.23,
            }
        ],
    }

    process_message(db_session, payload)
    db_session.commit()

    updated_type = db_session.get(MetricType, metric_type.id)
    assert updated_type.unit == "nm"
    assert updated_type.is_active is True


def test_process_message_dedupes_measurement_items(db_session, monkeypatch):
    counts = {"metric_type": 0, "measurement_item": 0}
    original_upsert = worker.upsert_and_get_id

    def wrapped_upsert(session, model, values, update_fields, lookup_filters):
        if model is MetricType:
            counts["metric_type"] += 1
        if model is MeasurementItem:
            counts["measurement_item"] += 1
        return original_upsert(session, model, values, update_fields, lookup_filters)

    monkeypatch.setattr(worker, "upsert_and_get_id", wrapped_upsert)

    payload = {
        "product_name": "P1",
        "site_name": "HC",
        "node_name": "2NM",
        "module_name": "PC",
        "recipe_name": "RCP",
        "recipe_version": "1.0",
        "file_path": "/data/measurements/measure1.csv",
        "file_name": "measure1.csv",
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
                "x_1": 0.3,
                "y_0": 0.2,
                "y_1": 0.4,
                "value": 1.23,
            },
            {
                "metric_name": "THK",
                "metric_unit": "nm",
                "class_name": "CLASS_A",
                "measure_item": "ITEM_1",
                "measurable": True,
                "x_index": 1,
                "y_index": 0,
                "x_0": 0.2,
                "x_1": 0.4,
                "y_0": 0.3,
                "y_1": 0.5,
                "value": 2.34,
            },
        ],
    }

    process_message(db_session, payload)
    db_session.commit()

    assert counts["metric_type"] == 1
    assert counts["measurement_item"] == 1
