"""GET /v1/health endpoint implementation."""

import logging
from fastapi import APIRouter, Response as FastAPIResponse

from app.models.responses import HealthResponse
from app.services.health import check_health, get_uptime_seconds
from app.config.settings import settings
from app.utils.timing import get_current_timestamp_iso

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    response_model_exclude_none=True,
    responses={
        200: {"description": "All systems operational"},
        503: {"description": "One or more critical components unavailable"},
    },
    summary="Health check",
    description="Check the health status of the API and its components",
    tags=["Health"],
)
async def health(response: FastAPIResponse) -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        HealthResponse: Health status of all components

    Sets:
        response.status_code: 200 for healthy, 503 for degraded
    """
    try:
        # Check health of all components
        overall_status, components = await check_health()

        # Set status code based on health
        if overall_status == "degraded":
            response.status_code = 503

        # Create response
        health_response = HealthResponse(
            status=overall_status,
            timestamp=get_current_timestamp_iso(),
            uptime_seconds=round(get_uptime_seconds(), 2),
            components=components,
            version=settings.api_version,
        )

        return health_response

    except Exception as e:
        logger.error(f"Error in health endpoint: {e}")
        response.status_code = 503

        # Return minimal degraded response
        from app.models.responses import ComponentStatus

        return HealthResponse(
            status="unhealthy",
            timestamp=get_current_timestamp_iso(),
            uptime_seconds=round(get_uptime_seconds(), 2),
            components={
                "api": ComponentStatus(status="error"),
            },
            version=settings.api_version,
        )