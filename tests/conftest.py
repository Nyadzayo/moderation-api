"""Shared fixtures for pytest."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch

from app.main import app
from app.config.settings import settings


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock = Mock()
    mock.ping.return_value = True
    mock.get.return_value = None
    mock.setex.return_value = True
    mock.zadd.return_value = 1
    mock.zcard.return_value = 0
    mock.zrange.return_value = []
    mock.zremrangebyscore.return_value = 0
    mock.expire.return_value = True
    return mock


@pytest.fixture
def sample_moderation_request():
    """Sample valid moderation request."""
    return {
        "inputs": [
            {"text": "Hello, world!"},
            {"text": "This is a test message."},
        ],
        "model": "unitary/toxic-bert",
        "return_scores": True,
    }


@pytest.fixture
def sample_moderation_request_with_thresholds():
    """Sample moderation request with custom thresholds."""
    return {
        "inputs": [
            {"text": "Hello, world!"},
        ],
        "model": "unitary/toxic-bert",
        "thresholds": {
            "harassment": 0.8,
            "hate": 0.8,
            "profanity": 0.7,
            "sexual": 0.8,
            "spam": 0.9,
            "violence": 0.7,
        },
        "return_scores": True,
    }


@pytest.fixture
def mock_model_inference():
    """Mock model inference."""
    with patch("app.services.moderation.run_inference") as mock:
        mock.return_value = AsyncMock(
            return_value={
                "harassment": 0.1,
                "hate": 0.05,
                "profanity": 0.02,
                "sexual": 0.01,
                "spam": 0.03,
                "violence": 0.04,
            }
        )
        yield mock


@pytest.fixture
def mock_toxic_inference():
    """Mock toxic content inference."""
    with patch("app.services.moderation.run_inference") as mock:
        mock.return_value = AsyncMock(
            return_value={
                "harassment": 0.9,
                "hate": 0.85,
                "profanity": 0.8,
                "sexual": 0.1,
                "spam": 0.05,
                "violence": 0.2,
            }
        )
        yield mock


@pytest.fixture(autouse=True)
def mock_redis_for_tests(mock_redis):
    """Automatically mock Redis for all tests."""
    with patch("app.utils.redis_client.get_redis_client", return_value=mock_redis):
        yield mock_redis


@pytest.fixture(autouse=True)
def reset_model_state():
    """Reset global model state before each test."""
    import app.services.moderation as mod
    mod._model = None
    mod._tokenizer = None
    mod._model_lock = __import__('threading').Lock()
    mod._model_load_time = None
    mod._model_name = None
    yield
    # Clean up after test
    mod._model = None
    mod._tokenizer = None
    mod._model_load_time = None
    mod._model_name = None