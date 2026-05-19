# apps/notifications/tests/conftest.py
"""
Pytest configuration and fixtures for Notifications app tests.
"""

import pytest

from apps.notifications.tests.factories import (
    FailedNotificationLogFactory,
    NotificationLogFactory,
    NotificationPreferenceFactory,
    PartialNotificationLogFactory,
    SentNotificationLogFactory,
)
from apps.users.tests.factories import UserFactory

# =============================================================================
# USER FIXTURES
# =============================================================================


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
