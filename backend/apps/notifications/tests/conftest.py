# apps/notifications/tests/conftest.py
"""
Pytest configuration and fixtures for Notifications app tests.
"""

import pytest
from rest_framework.test import APIClient

from apps.users.tests.factories import UserFactory, VerifiedUserFactory
from apps.notifications.tests.factories import (
    NotificationPreferenceFactory,
    NotificationLogFactory,
    SentNotificationLogFactory,
    FailedNotificationLogFactory,
    PartialNotificationLogFactory,
)


# =============================================================================
# API CLIENT FIXTURES
# =============================================================================


@pytest.fixture
def api_client():
    """Return an unauthenticated DRF APIClient instance."""
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user):
    """Return an APIClient authenticated as a regular user."""
    api_client.force_authenticate(user=user)
    return api_client


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
def another_user(db):
    """Create and return another test user."""
    return UserFactory()


# =============================================================================
# FACTORY FIXTURES
# =============================================================================


@pytest.fixture
def preference_factory(db):
    """Return the NotificationPreferenceFactory."""
    return NotificationPreferenceFactory


@pytest.fixture
def log_factory(db):
    """Return the NotificationLogFactory."""
    return NotificationLogFactory


# =============================================================================
# URL FIXTURES
# =============================================================================


@pytest.fixture
def preferences_url():
    """Return the preferences list endpoint URL."""
    return "/api/v1/notifications/preferences/"


@pytest.fixture
def preference_detail_url():
    """Return a function that generates preference detail URL."""
    def _url(notification_type):
        return f"/api/v1/notifications/preferences/{notification_type}/"
    return _url


@pytest.fixture
def history_url():
    """Return the notification history endpoint URL."""
    return "/api/v1/notifications/history/"


@pytest.fixture
def configurable_types_url():
    """Return the configurable types endpoint URL."""
    return "/api/v1/notifications/types/"
