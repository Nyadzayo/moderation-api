"""Response schemas for the moderation API."""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    """Model metadata information."""

    text_model: str = Field(..., description="Text moderation model name")
    version: str = Field(..., description="API version")


class ModerationResult(BaseModel):
    """Single moderation result for one input."""

    request_id: str = Field(..., description="UUID for tracking/debugging")
    flagged: bool = Field(..., description="Whether any category exceeded threshold")
    categories: Dict[str, bool] = Field(..., description="Boolean flags per category")
    category_scores: Optional[Dict[str, float]] = Field(
        None,
        description="Float scores (0.0-1.0) per category",
    )
    model_info: ModelInfo = Field(..., description="Model metadata")
    processing_time_ms: int = Field(..., description="Processing time for this input")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "req_abc123xyz",
                "flagged": True,
                "categories": {
                    "sexual": False,
                    "harassment": True,
                    "hate": True,
                    "violence": False,
                    "spam": False,
                    "profanity": True,
                },
                "category_scores": {
                    "sexual": 0.12,
                    "harassment": 0.85,
                    "hate": 0.92,
                    "violence": 0.15,
                    "spam": 0.05,
                    "profanity": 0.78,
                },
                "model_info": {
                    "text_model": "unitary/toxic-bert",
                    "version": "1.0.0",
                },
                "processing_time_ms": 150,
                "timestamp": "2025-09-29T22:10:05.123Z",
            }
        }


class ModerationResponse(BaseModel):
    """Response schema for POST /v1/moderate endpoint."""

    results: List[ModerationResult] = Field(
        ...,
        description="Array containing one entry per input item",
    )
    total_items: int = Field(..., description="Count of inputs processed")
    processing_time_ms: int = Field(..., description="Total request processing time")

    class Config:
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "request_id": "req_abc123xyz",
                        "flagged": True,
                        "categories": {
                            "sexual": False,
                            "harassment": True,
                            "hate": True,
                            "violence": False,
                            "spam": False,
                            "profanity": True,
                        },
                        "category_scores": {
                            "sexual": 0.12,
                            "harassment": 0.85,
                            "hate": 0.92,
                            "violence": 0.15,
                            "spam": 0.05,
                            "profanity": 0.78,
                        },
                        "model_info": {
                            "text_model": "unitary/toxic-bert",
                            "version": "1.0.0",
                        },
                        "processing_time_ms": 150,
                        "timestamp": "2025-09-29T22:10:05.123Z",
                    }
                ],
                "total_items": 2,
                "processing_time_ms": 285,
            }
        }


class ComponentStatus(BaseModel):
    """Status information for a single component."""

    status: str = Field(..., description="Component status")
    latency_ms: Optional[int] = Field(None, description="Component latency in milliseconds")
    name: Optional[str] = Field(None, description="Component name")
    load_time_seconds: Optional[float] = Field(None, description="Load time in seconds")

    model_config = {"exclude_none": True}


class HealthResponse(BaseModel):
    """Response schema for GET /v1/health endpoint."""

    status: str = Field(..., description="Overall system status")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")
    uptime_seconds: float = Field(..., description="API uptime in seconds")
    components: Dict[str, ComponentStatus] = Field(..., description="Component statuses")
    version: str = Field(..., description="API version")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-09-29T22:10:05.123Z",
                "uptime_seconds": 3600,
                "components": {
                    "api": {"status": "operational"},
                    "redis": {"status": "operational", "latency_ms": 2},
                    "model": {
                        "status": "loaded",
                        "name": "unitary/toxic-bert",
                        "load_time_seconds": 12.5,
                    },
                },
                "version": "1.0.0",
            }
        }