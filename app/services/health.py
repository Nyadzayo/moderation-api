"""Health check service."""

import logging
import time
from typing import Dict

from app.config.settings import settings
from app.utils.redis_client import check_redis_health
from app.services.moderation import is_model_loaded, get_loaded_model_name, get_model_load_time
from app.services.image_moderation import is_image_model_loaded, get_loaded_image_model_name, get_image_model_load_time
from app.models.responses import ComponentStatus

logger = logging.getLogger(__name__)

# Track application start time
_start_time = time.time()


def get_uptime_seconds() -> float:
    """
    Get application uptime in seconds.

    Returns:
        float: Uptime in seconds
    """
    return time.time() - _start_time


async def check_health() -> tuple[str, Dict[str, ComponentStatus]]:
    """
    Check health of all components.

    Returns:
        tuple: (overall_status, component_statuses)
            - overall_status: "healthy" or "degraded"
            - component_statuses: Dict of component statuses
    """
    components = {}

    # Check API (always operational if we get here)
    components["api"] = ComponentStatus(status="operational")

    # Check Redis
    redis_healthy, redis_latency = await check_redis_health()
    if redis_healthy:
        components["redis"] = ComponentStatus(
            status="operational", latency_ms=redis_latency
        )
    else:
        components["redis"] = ComponentStatus(status="unavailable")

    # Check Text Model
    if is_model_loaded():
        model_name = get_loaded_model_name()
        load_time = get_model_load_time()
        components["text_model"] = ComponentStatus(
            status="loaded",
            name=model_name,
            load_time_seconds=round(load_time, 2) if load_time else None,
        )
    else:
        components["text_model"] = ComponentStatus(status="not_loaded")

    # Check Image Model
    if is_image_model_loaded():
        image_model_name = get_loaded_image_model_name()
        image_load_time = get_image_model_load_time()
        components["image_model"] = ComponentStatus(
            status="loaded",
            name=image_model_name,
            load_time_seconds=round(image_load_time, 2) if image_load_time else None,
        )
    else:
        components["image_model"] = ComponentStatus(status="not_loaded")

    # Determine overall status
    overall_status = "healthy"
    if not redis_healthy:
        overall_status = "degraded"
        logger.warning("Health check: Redis unavailable, running in degraded mode")

    return overall_status, components