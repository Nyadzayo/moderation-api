"""Tests for moderation endpoint."""

import pytest
from unittest.mock import AsyncMock, patch


class TestModerateEndpoint:
    """Test cases for POST /v1/moderate endpoint."""

    @pytest.mark.asyncio
    async def test_moderate_success(self, client, sample_moderation_request):
        """Test successful moderation request."""
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

            response = client.post("/v1/moderate", json=sample_moderation_request)

            assert response.status_code == 200
            data = response.json()

            assert "results" in data
            assert "total_items" in data
            assert "processing_time_ms" in data
            assert data["total_items"] == 2
            assert len(data["results"]) == 2

            # Check result structure
            result = data["results"][0]
            assert "request_id" in result
            assert "flagged" in result
            assert "categories" in result
            assert "category_scores" in result
            assert "model_info" in result
            assert "processing_time_ms" in result
            assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_moderate_with_thresholds(
        self, client, sample_moderation_request_with_thresholds
    ):
        """Test moderation with custom thresholds."""
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
                "/v1/moderate", json=sample_moderation_request_with_thresholds
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total_items"] == 1

    @pytest.mark.asyncio
    async def test_moderate_flagged_content(self, client):
        """Test moderation of flagged content."""
        with patch("app.api.v1.moderate.moderate_text", new_callable=AsyncMock) as mock_moderate:
            mock_moderate.return_value = (
                True,
                {
                    "harassment": True,
                    "hate": True,
                    "profanity": True,
                    "sexual": False,
                    "spam": False,
                    "violence": False,
                },
                {
                    "harassment": 0.9,
                    "hate": 0.85,
                    "profanity": 0.8,
                    "sexual": 0.1,
                    "spam": 0.05,
                    "violence": 0.2,
                },
            )

            request_data = {
                "inputs": [{"text": "Toxic content"}],
                "return_scores": True,
            }

            response = client.post("/v1/moderate", json=request_data)

            assert response.status_code == 200
            data = response.json()
            result = data["results"][0]

            assert result["flagged"] is True
            assert result["categories"]["harassment"] is True
            assert result["categories"]["hate"] is True
            assert result["categories"]["profanity"] is True

    def test_moderate_invalid_input(self, client):
        """Test moderation with invalid input."""
        invalid_request = {
            "inputs": [],  # Empty inputs
        }

        response = client.post("/v1/moderate", json=invalid_request)
        assert response.status_code == 422  # Validation error

    def test_moderate_missing_text(self, client):
        """Test moderation with missing text field."""
        invalid_request = {
            "inputs": [{}],  # Missing text field
        }

        response = client.post("/v1/moderate", json=invalid_request)
        assert response.status_code == 422  # Validation error

    def test_moderate_invalid_threshold(self, client):
        """Test moderation with invalid threshold values."""
        invalid_request = {
            "inputs": [{"text": "Hello"}],
            "thresholds": {
                "harassment": 1.5,  # Invalid: > 1.0
            },
        }

        response = client.post("/v1/moderate", json=invalid_request)
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_moderate_without_scores(self, client):
        """Test moderation without returning scores."""
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

            request_data = {
                "inputs": [{"text": "Hello, world!"}],
                "return_scores": False,
            }

            response = client.post("/v1/moderate", json=request_data)

            assert response.status_code == 200
            data = response.json()
            result = data["results"][0]

            assert "category_scores" not in result or result["category_scores"] is None