"""Tests for rate limiting middleware."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app


class TestRateLimiting:
    """Test cases for rate limiting."""

    def test_rate_limit_not_exceeded(self, client, mock_redis):
        """Test request when rate limit is not exceeded."""
        mock_redis.zcard.return_value = 50  # Below limit (100)

        with patch("app.api.v1.moderate.moderate_text", new_callable=AsyncMock) as mock_moderate:
            mock_moderate.return_value = (
                False,
                {
                    "harassment": False,
                    "hate": False,
                    "profanity": False,
                    "sexual": False,
                    "spam": False,
                    "violence": False,
                },
                {
                    "harassment": 0.1,
                    "hate": 0.05,
                    "profanity": 0.02,
                    "sexual": 0.01,
                    "spam": 0.03,
                    "violence": 0.04,
                },
            )

            response = client.post(
                "/v1/moderate",
                json={"inputs": [{"text": "Hello"}], "return_scores": True},
            )

            assert response.status_code == 200

    def test_rate_limit_exceeded(self, client, mock_redis):
        """Test request when rate limit is exceeded."""
        # Ensure Redis client returns the mock, not None
        with patch("app.middleware.rate_limit.get_redis_client", return_value=mock_redis):
            mock_redis.zcard.return_value = 150  # Above limit (100)
            mock_redis.zrange.return_value = [(str(1234567890), 1234567890)]

            response = client.post(
                "/v1/moderate",
                json={"inputs": [{"text": "Hello"}], "return_scores": True},
            )

            assert response.status_code == 429
            assert "Retry-After" in response.headers

    def test_rate_limit_disabled(self, client, mock_redis):
        """Test that rate limiting can be disabled."""
        with patch("app.config.settings.settings.rate_limit_enabled", False):
            with patch("app.api.v1.moderate.moderate_text", new_callable=AsyncMock) as mock_moderate:
                mock_moderate.return_value = (
                    False,
                    {
                        "harassment": False,
                        "hate": False,
                        "profanity": False,
                        "sexual": False,
                        "spam": False,
                        "violence": False,
                    },
                    {
                        "harassment": 0.1,
                        "hate": 0.05,
                        "profanity": 0.02,
                        "sexual": 0.01,
                        "spam": 0.03,
                        "violence": 0.04,
                    },
                )

                # Should not check rate limit
                response = client.post(
                    "/v1/moderate",
                    json={"inputs": [{"text": "Hello"}], "return_scores": True},
                )

                assert response.status_code == 200