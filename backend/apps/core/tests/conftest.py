# apps/core/tests/conftest.py
"""
Pytest configuration and fixtures for Core app tests.
"""

import pytest
from rest_framework.test import APIClient, APIRequestFactory

from apps.users.tests.factories import (
    UserFactory,
    VerifiedUserFactory,
    StaffUserFactory,
    SuperuserFactory,
)


# =============================================================================
# API CLIENT FIXTURES
# =============================================================================


@pytest.fixture
def api_client():
    """Return an unauthenticated DRF APIClient instance."""
    return APIClient()


@pytest.fixture
def request_factory():
    """Return a DRF APIRequestFactory for permission testing."""
    return APIRequestFactory()


# =============================================================================
# USER FIXTURES
# =============================================================================


@pytest.fixture
def user(db):
    """Create and return a regular test user."""
    return UserFactory()


@pytest.fixture
def verified_user(db):
    """Create and return a verified test user."""
    return VerifiedUserFactory()


@pytest.fixture
def staff_user(db):
    """Create and return a staff test user."""
    return StaffUserFactory()


@pytest.fixture
def superuser(db):
    """Create and return a superuser."""
    return SuperuserFactory()


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
