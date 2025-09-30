"""Request schemas for the moderation API."""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field, field_validator


class ModerationInput(BaseModel):
    """Single input item for moderation."""

    text: str = Field(..., description="Text content to moderate", min_length=1)


class ModerationRequest(BaseModel):
    """Request schema for POST /v1/moderate endpoint."""

    inputs: List[ModerationInput] = Field(
        ...,
        description="Array of objects for batch moderation",
        min_length=1,
    )
    model: Optional[str] = Field(
        None,
        description="Model identifier; defaults to config value if not provided",
    )
    thresholds: Optional[Dict[str, float]] = Field(
        None,
        description="Per-category threshold overrides (0.0-1.0)",
    )
    return_scores: bool = Field(
        True,
        description="Include raw probability scores in response",
    )

    @field_validator("thresholds")
    @classmethod
    def validate_thresholds(cls, v: Optional[Dict[str, float]]) -> Optional[Dict[str, float]]:
        """Validate threshold values are between 0.0 and 1.0."""
        if v is not None:
            for category, threshold in v.items():
                if not 0.0 <= threshold <= 1.0:
                    raise ValueError(f"Threshold for {category} must be between 0.0 and 1.0")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "inputs": [
                    {"text": "Hello, world!"},
                    {"text": "You are an awful person."},
                ],
                "model": "unitary/toxic-bert",
                "thresholds": {
                    "harassment": 0.7,
                    "hate": 0.7,
                    "profanity": 0.6,
                    "sexual": 0.7,
                    "spam": 0.8,
                    "violence": 0.6,
                },
                "return_scores": True,
            }
        }