import logging

from fastapi import FastAPI

from app.api.routes import check_db, check_rabbitmq, router as api_router
from app.logging_config import setup_logging
from app.metrics import MetricsMiddleware, metrics_app

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI()
app.include_router(api_router)
app.add_middleware(MetricsMiddleware)
app.mount("/metrics", metrics_app())


@app.on_event("startup")
def startup_log() -> None:
    logger.info("Server starting", extra={"event": "server_start"})
    db_ok = check_db()
    mq_ok = check_rabbitmq()
    logger.info(
        "Server dependencies",
        extra={"event": "server_deps", "db": db_ok, "rabbitmq": mq_ok},
    )
