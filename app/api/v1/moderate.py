"""POST /v1/moderate endpoint implementation."""

import asyncio
import logging
import hashlib
import json
from typing import List
from fastapi import APIRouter, HTTPException, Request

from app.models.requests import ModerationRequest
from app.models.responses import (
    ModerationResponse,
    ModerationResult,
    ModelInfo,
)
from app.models.errors import ErrorResponse, ErrorResponseWrapper, ErrorDetail
from app.services.moderation import moderate_text, apply_thresholds
from app.services.image_moderation import moderate_image
from app.config.settings import settings
from app.utils.ids import generate_request_id, generate_error_request_id
from app.utils.timing import timer, get_current_timestamp_iso
from app.utils.redis_client import get_redis_client

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

            # Extract requested categories from thresholds
            # If thresholds provided, only return those categories
            # If no thresholds, return all categories (backward compatible)
            requested_categories = None
            if moderation_request.thresholds:
                requested_categories = list(moderation_request.thresholds.keys())

            # Process each input
            for input_item in moderation_request.inputs:
                with timer() as item_timer:
                    try:
                        # OPTIMIZATION 1: Parallel text + image processing
                        text_task = moderate_text(
                            text=input_item.text,
                            model_name=model_name,
                            custom_thresholds=moderation_request.thresholds,
                            requested_categories=requested_categories,
                        )

                        # Run image moderation in parallel if provided
                        image_task = None
                        image_model_name = None
                        cache_key = None

                        if input_item.image:
                            # OPTIMIZATION 2: Hash-first caching (check before downloading)
                            redis_client = get_redis_client()
                            cache_key = f"cache:image:{hashlib.sha256(input_item.image.encode()).hexdigest()[:16]}"

                            cached_result = redis_client.get(cache_key) if redis_client else None
                            if cached_result:
                                # Cache hit - no need to process
                                image_scores = json.loads(cached_result)
                                logger.debug(f"[IMAGE CACHE HIT] {cache_key}")
                            else:
                                # Cache miss - create task for parallel processing
                                image_task = moderate_image(input_item.image)

                        # Wait for both tasks to complete
                        if image_task:
                            # Run text and image in parallel
                            text_result, image_result = await asyncio.gather(
                                text_task, image_task
                            )

                            # Unpack results
                            flagged, category_flags, scores = text_result
                            image_scores, image_hash = image_result

                            # Cache the image result
                            if redis_client and cache_key:
                                redis_client.setex(
                                    cache_key,
                                    settings.cache_ttl_seconds,
                                    json.dumps(image_scores)
                                )
                            logger.info(f"[IMAGE PROCESSED] hash:{image_hash}")
                            image_model_name = settings.default_image_model

                        elif input_item.image and cached_result:
                            # Text only (image was cached)
                            flagged, category_flags, scores = await text_task
                            image_model_name = settings.default_image_model
                        else:
                            # Text only (no image)
                            flagged, category_flags, scores = await text_task
                            image_scores = None

                        # Merge scores if we have image results
                        if input_item.image and (image_task or cached_result):
                            try:
                                # Merge image scores into text scores
                                for category, score in image_scores.items():
                                    if category in scores:
                                        # Take maximum score if both text and image detect same category
                                        scores[category] = max(scores[category], score)
                                    elif requested_categories is None or category in requested_categories:
                                        # Add image-only category if not filtered
                                        scores[category] = score

                                # Re-apply thresholds with merged scores (only once)
                                flagged, category_flags = apply_thresholds(
                                    scores, moderation_request.thresholds
                                )

                                # Filter based on requested categories
                                if requested_categories is not None:
                                    scores = {cat: scores[cat] for cat in requested_categories if cat in scores}
                                    category_flags = {cat: category_flags[cat] for cat in requested_categories if cat in category_flags}

                            except Exception as e:
                                logger.error(f"Image score merging failed: {e}")
                                # Continue with text-only results (graceful degradation)

                        # Create result
                        result = ModerationResult(
                            request_id=generate_request_id(),
                            flagged=flagged,
                            categories=category_flags,
                            category_scores=scores if moderation_request.return_scores else None,
                            model_info=ModelInfo(
                                text_model=model_name,
                                image_model=image_model_name,
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