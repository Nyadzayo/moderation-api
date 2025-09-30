"""Redis-based rate limiting middleware."""

import logging
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time

from app.config.settings import settings
from app.utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for Redis-based rate limiting with sliding window."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Check rate limits before processing request.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response: Response from next middleware

        Raises:
            HTTPException: 429 if rate limit exceeded
        """
        # Skip rate limiting if disabled
        if not settings.rate_limit_enabled:
            return await call_next(request)

        # Get Redis client
        redis_client = get_redis_client()

        # If Redis is unavailable, skip rate limiting (graceful degradation)
        if redis_client is None:
            logger.warning("Redis unavailable, skipping rate limit check")
            return await call_next(request)

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Create rate limit key
        endpoint = request.url.path
        rate_limit_key = f"rate_limit:{client_ip}:{endpoint}"

        try:
            # Get current timestamp
            current_time = int(time.time())
            window_start = current_time - settings.rate_limit_window_seconds

            # Remove old entries outside the window
            redis_client.zremrangebyscore(rate_limit_key, 0, window_start)

            # Count requests in current window
            request_count = redis_client.zcard(rate_limit_key)

            # Debug logging
            logger.debug(f"[RATE LIMIT CHECK] IP: {client_ip}, Count: {request_count}/{settings.rate_limit_requests}")

            # Check if limit exceeded
            if request_count >= settings.rate_limit_requests:
                # Calculate retry after
                oldest_request = redis_client.zrange(rate_limit_key, 0, 0, withscores=True)
                if oldest_request:
                    oldest_time = int(oldest_request[0][1])
                    retry_after = (
                        oldest_time + settings.rate_limit_window_seconds - current_time
                    )
                else:
                    retry_after = settings.rate_limit_window_seconds

                logger.warning(
                    f"[RATE LIMIT] Exceeded for {client_ip} on {endpoint}. "
                    f"Count: {request_count}/{settings.rate_limit_requests}"
                )

                # Return 429 response directly
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"},
                    headers={"Retry-After": str(max(1, retry_after))},
                )

            # Add current request to window (use unique ID with timestamp)
            import uuid
            unique_id = f"{current_time}_{uuid.uuid4().hex[:8]}"
            redis_client.zadd(rate_limit_key, {unique_id: current_time})

            # Set expiry on key (cleanup)
            redis_client.expire(rate_limit_key, settings.rate_limit_window_seconds + 10)

        except Exception as e:
            # If rate limiting fails, log and continue (graceful degradation)
            logger.error(f"Rate limiting error: {e}")

        # Process request
        return await call_next(request)