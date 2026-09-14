import logging
import sys
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import uuid

# Configure standard logging format
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"

def setup_logging(level: str = "INFO") -> None:
    """Initialize structured application logging."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format=LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ],
        force=True
    )
    # Suppress overly chatty external loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


logger = logging.getLogger("solar_sentry")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request tracing and execution timing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        start_time = time.perf_counter()
        try:
            response = await call_next(request)
            process_time = (time.perf_counter() - start_time) * 1000
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"

            # Only log detailed requests for non-frequent polling or errors
            if request.url.path not in ["/api/v1/observatory/health", "/docs", "/openapi.json"]:
                logger.info(
                    f"[{request_id[:8]}] {request.method} {request.url.path} -> "
                    f"{response.status_code} ({process_time:.2f}ms)"
                )
            return response
        except Exception as e:
            process_time = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"[{request_id[:8]}] {request.method} {request.url.path} FAILED: {str(e)} "
                f"({process_time:.2f}ms)",
                exc_info=True
            )
            raise
