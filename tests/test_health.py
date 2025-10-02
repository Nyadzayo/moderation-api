"""Tests for health endpoint."""

import pytest
from unittest.mock import patch, AsyncMock


class TestHealthEndpoint:
    """Test cases for GET /v1/health endpoint."""

    def test_health_success(self, client):
        """Test successful health check."""
        with patch("app.services.health.check_redis_health", new_callable=AsyncMock) as mock_redis_health:
            mock_redis_health.return_value = (True, 2)

            response = client.get("/v1/health")

            assert response.status_code == 200
            data = response.json()

            assert "status" in data
            assert "timestamp" in data
            assert "uptime_seconds" in data
            assert "components" in data
            assert "version" in data

            assert data["status"] == "healthy"
            assert "api" in data["components"]
            assert "redis" in data["components"]

    def test_health_redis_unavailable(self, client):
        """Test health check when Redis is unavailable."""
        with patch("app.services.health.check_redis_health", new_callable=AsyncMock) as mock_redis_health:
            mock_redis_health.return_value = (False, None)

            response = client.get("/v1/health")

            assert response.status_code == 503
            data = response.json()

            assert data["status"] == "degraded"
            assert data["components"]["redis"]["status"] == "unavailable"

    def test_health_model_not_loaded(self, client):
        """Test health check when model is not loaded."""
        with patch("app.services.health.check_redis_health", new_callable=AsyncMock) as mock_redis_health:
            with patch("app.services.health.is_model_loaded") as mock_model_loaded:
                mock_redis_health.return_value = (True, 2)
                mock_model_loaded.return_value = False

                response = client.get("/v1/health")

                assert response.status_code == 200
                data = response.json()

                assert data["components"]["text_model"]["status"] == "not_loaded"

    def test_health_model_loaded(self, client):
        """Test health check when model is loaded."""
        with patch("app.services.health.check_redis_health", new_callable=AsyncMock) as mock_redis_health:
            with patch("app.services.health.is_model_loaded") as mock_model_loaded:
                with patch(
                    "app.services.health.get_loaded_model_name"
                ) as mock_model_name:
                    with patch(
                        "app.services.health.get_model_load_time"
                    ) as mock_load_time:
                        mock_redis_health.return_value = (True, 2)
                        mock_model_loaded.return_value = True
                        mock_model_name.return_value = "unitary/toxic-bert"
                        mock_load_time.return_value = 12.5

                        response = client.get("/v1/health")

                        assert response.status_code == 200
                        data = response.json()

                        assert data["components"]["text_model"]["status"] == "loaded"
                        assert (
                            data["components"]["text_model"]["name"] == "unitary/toxic-bert"
                        )
                        assert data["components"]["text_model"]["load_time_seconds"] == 12.5