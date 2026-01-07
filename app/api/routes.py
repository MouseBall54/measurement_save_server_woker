from fastapi import APIRouter, HTTPException
from sqlalchemy import text
import pika

from app.config import get_settings
from app.db.session import engine
from app.queue.rabbitmq import RabbitMQClient
from app.schemas import IngestRequest, IngestResponse

router = APIRouter()


def check_db() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def check_rabbitmq() -> bool:
    settings = get_settings()
    credentials = pika.PlainCredentials(settings.rabbitmq_user, settings.rabbitmq_password)
    parameters = pika.ConnectionParameters(
        host=settings.rabbitmq_host,
        port=settings.rabbitmq_port,
        credentials=credentials,
        connection_attempts=1,
        retry_delay=0,
        socket_timeout=2,
        blocked_connection_timeout=2,
    )
    try:
        connection = pika.BlockingConnection(parameters)
        connection.close()
        return True
    except Exception:
        return False


@router.post("/ingest", response_model=IngestResponse)
def ingest(payload: IngestRequest) -> IngestResponse:
    try:
        with RabbitMQClient() as client:
            message_id = client.publish(payload.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Queue unavailable") from exc
    return IngestResponse(status="queued", id=message_id)


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
def ready() -> tuple[dict, int]:
    db_ok = check_db()
    mq_ok = check_rabbitmq()
    if db_ok and mq_ok:
        return {"status": "ready"}, 200
    return {"status": "not_ready", "details": {"db": db_ok, "rabbitmq": mq_ok}}, 503
