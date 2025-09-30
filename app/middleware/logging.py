"""Structured request/response logging middleware."""

import logging
import json
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.utils.ids import generate_request_id

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request/response logging."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Log request and response metadata.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response: Response from next middleware
        """
        # Generate request ID if not present
        request_id = generate_request_id()
        request.state.request_id = request_id

        # Start timer
        start_time = time.perf_counter()

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Process request
        try:
            response = await call_next(request)
            end_time = time.perf_counter()
            processing_time_ms = int((end_time - start_time) * 1000)

            # Log request/response metadata (structured JSON)
            log_data = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "processing_time_ms": processing_time_ms,
                "user_ip": client_ip,
            }

            # Log at appropriate level
            if response.status_code >= 500:
                logger.error(json.dumps(log_data))
            elif response.status_code >= 400:
                logger.warning(json.dumps(log_data))
            else:
                logger.info(json.dumps(log_data))

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            end_time = time.perf_counter()
            processing_time_ms = int((end_time - start_time) * 1000)

            # Log error
            log_data = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "processing_time_ms": processing_time_ms,
                "user_ip": client_ip,
                "error": str(e),
            }
            logger.error(json.dumps(log_data))

            raise