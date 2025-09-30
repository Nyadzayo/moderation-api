"""Tests for service layer."""

import pytest
from app.services.moderation import apply_thresholds


class TestModerationService:
    """Test cases for moderation service."""

    def test_apply_thresholds_not_flagged(self):
        """Test threshold application when content is not flagged."""
        scores = {
            "harassment": 0.1,
            "hate": 0.05,
            "profanity": 0.02,
            "sexual": 0.01,
            "spam": 0.03,
            "violence": 0.04,
        }

        flagged, category_flags = apply_thresholds(scores)

        assert flagged is False
        assert all(not flag for flag in category_flags.values())

    def test_apply_thresholds_flagged(self):
        """Test threshold application when content is flagged."""
        scores = {
            "harassment": 0.9,
            "hate": 0.85,
            "profanity": 0.8,
            "sexual": 0.1,
            "spam": 0.05,
            "violence": 0.2,
        }

        flagged, category_flags = apply_thresholds(scores)

        assert flagged is True
        assert category_flags["harassment"] is True
        assert category_flags["hate"] is True
        assert category_flags["profanity"] is True
        assert category_flags["sexual"] is False
        assert category_flags["spam"] is False

    def test_apply_thresholds_custom(self):
        """Test threshold application with custom thresholds."""
        scores = {
            "harassment": 0.75,
            "hate": 0.65,
            "profanity": 0.55,
            "sexual": 0.1,
            "spam": 0.05,
            "violence": 0.2,
        }

        custom_thresholds = {
            "harassment": 0.8,
            "hate": 0.8,
            "profanity": 0.5,
        }

        flagged, category_flags = apply_thresholds(scores, custom_thresholds)

        assert flagged is True
        assert category_flags["harassment"] is False  # 0.75 < 0.8
        assert category_flags["hate"] is False  # 0.65 < 0.8
        assert category_flags["profanity"] is True  # 0.55 >= 0.5

    def test_apply_thresholds_edge_case(self):
        """Test threshold application at exact threshold value."""
        scores = {
            "harassment": 0.7,  # Exactly at default threshold
            "hate": 0.05,
            "profanity": 0.02,
            "sexual": 0.01,
            "spam": 0.03,
            "violence": 0.04,
        }

        flagged, category_flags = apply_thresholds(scores)

        assert flagged is True
        assert category_flags["harassment"] is True  # 0.7 >= 0.7


class TestHealthService:
    """Test cases for health service."""

    def test_get_uptime_seconds(self):
        """Test uptime calculation."""
        from app.services.health import get_uptime_seconds

        uptime = get_uptime_seconds()
        assert uptime >= 0
        assert isinstance(uptime, float)