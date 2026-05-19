# apps/core/tests/conftest.py
"""
Pytest configuration and fixtures for Core app tests.
"""

import pytest
from rest_framework.test import APIRequestFactory

from apps.users.tests.factories import UserFactory

# =============================================================================
# API CLIENT FIXTURES
# =============================================================================


@pytest.fixture
def request_factory():
    """Return a DRF APIRequestFactory for permission testing."""
    return APIRequestFactory()


# =============================================================================
# USER FIXTURES
# =============================================================================


@pytest.fixture
def another_user(db):
    """Create and return another regular test user."""
    return UserFactory()


# =============================================================================
# FACTORY FIXTURES
# =============================================================================


@pytest.fixture
def user_factory(db):
    """Return the UserFactory for creating users in tests."""
    return UserFactory
