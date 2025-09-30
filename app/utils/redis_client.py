"""Redis connection management."""

import logging
from typing import Optional
import redis
from redis.connection import ConnectionPool

from app.config.settings import settings

logger = logging.getLogger(__name__)

# Global connection pool
_redis_pool: Optional[ConnectionPool] = None
_redis_client: Optional[redis.Redis] = None
_redis_available: bool = False


def init_redis_pool() -> None:
    """
    Initialize Redis connection pool.

    This should be called on application startup.
    """
    global _redis_pool, _redis_client, _redis_available

    try:
        _redis_pool = ConnectionPool(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            max_connections=settings.redis_max_connections,
            socket_timeout=settings.redis_socket_timeout,
            socket_connect_timeout=settings.redis_socket_connect_timeout,
            retry_on_timeout=settings.redis_retry_on_timeout,
            decode_responses=True,
        )

        _redis_client = redis.Redis(connection_pool=_redis_pool)

        # Test connection
        _redis_client.ping()
        _redis_available = True
        logger.info("[REDIS] Connection pool initialized successfully")

    except Exception as e:
        logger.warning(f"Failed to initialize Redis: {e}. Running in degraded mode.")
        _redis_available = False


def get_redis_client() -> Optional[redis.Redis]:
    """
    Get Redis client instance.

    Returns:
        Optional[redis.Redis]: Redis client or None if unavailable
    """
    if not _redis_available or _redis_client is None:
        return None
    return _redis_client


def is_redis_available() -> bool:
    """
    Check if Redis is available.

    Returns:
        bool: True if Redis is available, False otherwise
    """
    return _redis_available


def close_redis_pool() -> None:
    """
    Close Redis connection pool.

    This should be called on application shutdown.
    """
    global _redis_pool, _redis_client, _redis_available

    if _redis_pool is not None:
        _redis_pool.disconnect()
        logger.info("Redis connection pool closed")

    _redis_pool = None
    _redis_client = None
    _redis_available = False


async def check_redis_health() -> tuple[bool, Optional[int]]:
    """
    Check Redis health and measure latency.

    Returns:
        tuple[bool, Optional[int]]: (is_healthy, latency_ms)
    """
    client = get_redis_client()
    if client is None:
        return False, None

    try:
        import time

        start = time.perf_counter()
        client.ping()
        end = time.perf_counter()
        latency_ms = int((end - start) * 1000)
        return True, latency_ms
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False, None