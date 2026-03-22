"""
Pytest configuration and shared fixtures.

This file is automatically loaded by pytest. Fixtures defined here
are available to all tests in the project.

Note: User and authentication fixtures are defined in each app's own
conftest.py to avoid shadowing and ensure correct factory usage.
"""

import pytest
from rest_framework.test import APIClient

# =============================================================================
# API Client Fixtures
# =============================================================================


@pytest.fixture
def api_client():
    """Return an unauthenticated DRF APIClient instance."""
    return APIClient()


# =============================================================================
# Database Fixtures
# =============================================================================


@pytest.fixture
def db_no_rollback(request, django_db_setup, django_db_blocker):
    """
    Database access without transaction rollback.

    Use this for tests that need to verify database constraints
    or test transaction behavior.

    WARNING: Tests using this fixture may leave data in the database.
    """
    django_db_blocker.unblock()
    request.addfinalizer(django_db_blocker.restore)


# =============================================================================
# Utility Fixtures
# =============================================================================


@pytest.fixture
def json_content_type():
    """Return JSON content type header dict."""
    return {"content_type": "application/json"}


# =============================================================================
# Settings Override Fixtures
# =============================================================================


@pytest.fixture
def settings_debug_true(settings):
    """Temporarily enable DEBUG mode."""
    settings.DEBUG = True
    return settings


@pytest.fixture
def settings_debug_false(settings):
    """Temporarily disable DEBUG mode."""
    settings.DEBUG = False
    return settings
