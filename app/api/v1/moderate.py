"""POST /v1/moderate endpoint implementation."""

import logging
from typing import List
from fastapi import APIRouter, HTTPException, Request

from app.models.requests import ModerationRequest
from app.models.responses import (
    ModerationResponse,
    ModerationResult,
    ModelInfo,
)
from app.models.errors import ErrorResponse, ErrorResponseWrapper, ErrorDetail
from app.services.moderation import moderate_text
from app.config.settings import settings
from app.utils.ids import generate_request_id, generate_error_request_id
from app.utils.timing import timer, get_current_timestamp_iso

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/moderate",
    response_model=ModerationResponse,
    responses={
        400: {"model": ErrorResponseWrapper, "description": "Validation error"},
        429: {"description": "Rate limit exceeded"},
        500: {"model": ErrorResponseWrapper, "description": "Internal server error"},
    },
    summary="Moderate text content",
    description="Perform content moderation on batch text inputs with customizable thresholds",
    tags=["Moderation"],
)
async def moderate(request: Request, moderation_request: ModerationRequest) -> ModerationResponse:
    """
    Moderate text content with batch support.

    Args:
        request: FastAPI request object
        moderation_request: Moderation request payload

    Returns:
        ModerationResponse: Moderation results

    Raises:
        HTTPException: On validation or processing errors
    """
    try:
        # Start timer for total processing time
        with timer() as total_timer:
            results: List[ModerationResult] = []

            # Get model name (use default if not provided)
            model_name = moderation_request.model or settings.default_model

            # Process each input
            for input_item in moderation_request.inputs:
                with timer() as item_timer:
                    try:
                        # Run moderation
                        flagged, category_flags, scores = await moderate_text(
                            text=input_item.text,
                            model_name=model_name,
                            custom_thresholds=moderation_request.thresholds,
                        )

                        # Create result
                        result = ModerationResult(
                            request_id=generate_request_id(),
                            flagged=flagged,
                            categories=category_flags,
                            category_scores=scores if moderation_request.return_scores else None,
                            model_info=ModelInfo(
                                text_model=model_name,
                                version=settings.api_version,
                            ),
                            processing_time_ms=item_timer["elapsed_ms"],
                            timestamp=get_current_timestamp_iso(),
                        )

                        results.append(result)

                    except Exception as e:
                        logger.error(f"Error processing input: {e}")
                        # Create error result
                        error_id = generate_error_request_id()
                        raise HTTPException(
                            status_code=500,
                            detail={
                                "error": {
                                    "type": "processing_error",
                                    "message": f"Failed to process input: {str(e)}",
                                    "request_id": error_id,
                                    "timestamp": get_current_timestamp_iso(),
                                }
                            },
                        )

            # Create response
            response = ModerationResponse(
                results=results,
                total_items=len(moderation_request.inputs),
                processing_time_ms=total_timer["elapsed_ms"],
            )

            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in moderate endpoint: {e}")
        error_id = generate_error_request_id()
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "type": "internal_error",
                    "message": "An unexpected error occurred",
                    "request_id": error_id,
                    "timestamp": get_current_timestamp_iso(),
                }
            },
        )