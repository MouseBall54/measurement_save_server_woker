from sqlalchemy import select

from app.db.models import MeasurementRawData
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
                "y_0": 0.2,
                "x_1": 0.3,
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
                "y_0": 0.3,
                "x_1": 0.4,
                "y_1": 0.5,
                "value": 2.34,
            },
        ],
    }

    process_message(db_session, payload)
    db_session.commit()

    raw = db_session.execute(select(MeasurementRawData)).scalars().all()
    assert len(raw) == 2
    values = sorted(item.value for item in raw)
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
                "y_0": 0.2,
                "x_1": 0.3,
                "y_1": 0.4,
                "value": 1.23,
            }
        ],
    }

    process_message(db_session, payload)
    process_message(db_session, payload)
    db_session.commit()

    raw = db_session.execute(select(MeasurementRawData)).scalars().all()
    assert len(raw) == 1
