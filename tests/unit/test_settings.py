"""Tests for settings - minimal coverage."""

from src.config.settings import Settings


class TestSettings:
    def test_default_region(self):
        assert Settings.AWS_REGION == "us-east-1"

    def test_app_name(self):
        assert Settings.APP_NAME == "AWS ECS Workshop"
