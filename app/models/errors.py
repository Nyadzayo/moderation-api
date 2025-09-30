"""Error schemas for the moderation API."""

from typing import List, Optional
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Detailed error information for validation errors."""

    field: str = Field(..., description="Field name that caused the error")
    issue: str = Field(..., description="Description of the issue")


class ErrorResponse(BaseModel):
    """Standardized error response schema."""

    type: str = Field(..., description="Error category")
    message: str = Field(..., description="Human-readable error description")
    details: Optional[List[ErrorDetail]] = Field(
        None,
        description="Array of specific issues (for validation errors)",
    )
    request_id: str = Field(..., description="UUID for tracking")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "validation_error",
                "message": "Invalid input format",
                "details": [
                    {
                        "field": "inputs[0].text",
                        "issue": "Field required",
                    }
                ],
                "request_id": "req_error_xyz",
                "timestamp": "2025-09-29T22:10:05.123Z",
            }
        }


class ErrorResponseWrapper(BaseModel):
    """Wrapper for error responses."""

    error: ErrorResponse = Field(..., description="Error information")

    class Config:
        json_schema_extra = {
            "example": {
                "error": {
                    "type": "validation_error",
                    "message": "Invalid input format",
                    "details": [
                        {
                            "field": "inputs[0].text",
                            "issue": "Field required",
                        }
                    ],
                    "request_id": "req_error_xyz",
                    "timestamp": "2025-09-29T22:10:05.123Z",
                }
            }
        }