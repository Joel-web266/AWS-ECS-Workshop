"""Shared test fixtures for the ECS Workshop test suite."""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_session():
    """Provide a mock boto3 session for AWS manager tests."""
    return MagicMock()
