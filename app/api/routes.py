from fastapi import APIRouter, HTTPException

from app.queue.rabbitmq import RabbitMQClient
from app.schemas import IngestRequest, IngestResponse

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
def ingest(payload: IngestRequest) -> IngestResponse:
    try:
        with RabbitMQClient() as client:
            message_id = client.publish(payload.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Queue unavailable") from exc
    return IngestResponse(status="queued", id=message_id)
