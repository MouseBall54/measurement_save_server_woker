import time

from prometheus_client import Counter, Histogram, make_asgi_app
from starlette.middleware.base import BaseHTTPMiddleware

http_requests = Counter(
    "http_requests_total",
    "HTTP requests",
    ["method", "endpoint", "status"],
)
http_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start

        http_requests.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
        ).inc()
        http_duration.labels(
            method=request.method,
            endpoint=request.url.path,
        ).observe(duration)
        return response


def metrics_app():
    return make_asgi_app()
