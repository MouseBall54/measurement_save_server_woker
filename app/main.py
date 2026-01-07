from fastapi import FastAPI

from app.api.routes import router as api_router
from app.logging_config import setup_logging
from app.metrics import MetricsMiddleware, metrics_app

setup_logging()

app = FastAPI()
app.include_router(api_router)
app.add_middleware(MetricsMiddleware)
app.mount("/metrics", metrics_app())
