"""Redis-based response caching middleware."""

import logging
import json
import hashlib
import base64
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.config.settings import settings
from app.utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class CacheMiddleware(BaseHTTPMiddleware):
    """Middleware for Redis-based response caching."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Check cache before processing request, store response after.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response: Cached or fresh response
        """
        # Only cache GET requests to /v1/moderate (or POST with specific logic)
        # For moderation API, we'll cache POST requests based on content hash
        if request.method != "POST" or not request.url.path.startswith("/v1/moderate"):
            return await call_next(request)

        # Skip caching if disabled
        if not settings.cache_enabled:
            return await call_next(request)

        # Check for cache bypass header
        if request.headers.get("X-No-Cache") == "true":
            return await call_next(request)

        # Get Redis client
        redis_client = get_redis_client()

        # If Redis is unavailable, skip caching (graceful degradation)
        if redis_client is None:
            logger.debug("Redis unavailable, skipping cache")
            return await call_next(request)

        # Read request body
        body = await request.body()

        # IMPORTANT: We need to make the body available again for downstream handlers
        # by creating a new receive function that returns the body
        async def receive():
            return {"type": "http.request", "body": body}

        # Replace the request's receive with our custom one
        request._receive = receive

        try:
            # Create cache key from request body hash
            cache_key = _create_cache_key(body)

            # Try to get cached response
            cached_response = redis_client.get(cache_key)
            if cached_response:
                logger.info(f"[CACHE HIT] key: {cache_key}")
                # Parse cached response
                cached_data = json.loads(cached_response)
                # Decode base64-encoded body back to bytes
                response_body = base64.b64decode(cached_data["content"])
                response = Response(
                    content=response_body,
                    status_code=cached_data["status_code"],
                    headers=dict(cached_data["headers"]),
                    media_type=cached_data.get("media_type", "application/json"),
                )
                # Add cache header
                response.headers["X-Cache"] = "HIT"
                return response

            logger.info(f"[CACHE MISS] key: {cache_key}")

        except Exception as e:
            logger.error(f"Cache lookup error: {e}")

        # Process request
        response = await call_next(request)

        # Cache successful responses
        if response.status_code == 200:
            try:
                # Read response body
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk

                # Create cache key
                cache_key = _create_cache_key(body)

                # Store in cache (encode bytes as base64 to handle both text and gzipped responses)
                cache_data = {
                    "content": base64.b64encode(response_body).decode("utf-8"),
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "media_type": response.media_type,
                }
                redis_client.setex(
                    cache_key,
                    settings.cache_ttl_seconds,
                    json.dumps(cache_data),
                )
                logger.info(f"[CACHE STORED] key: {cache_key}, TTL: {settings.cache_ttl_seconds}s")

                # Return response with body
                new_response = Response(
                    content=response_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )
                # Add cache header
                new_response.headers["X-Cache"] = "MISS"
                return new_response

            except Exception as e:
                logger.error(f"Cache storage error: {e}")

        return response


def _create_cache_key(body: bytes) -> str:
    """
    Create cache key from request body.

    Args:
        body: Request body bytes

    Returns:
        str: Cache key
    """
    # Hash the body content
    body_hash = hashlib.sha256(body).hexdigest()[:16]
    return f"cache:moderate:{body_hash}"