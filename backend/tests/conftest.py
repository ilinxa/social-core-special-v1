"""
Pytest configuration and shared fixtures for integration tests.

Fixtures here are available to all tests under ``backend/tests/``.

Note: ``api_client``, ``user``, ``authenticated_client``, ``verified_user``,
``staff_user``, and ``superuser`` are hoisted to root ``backend/conftest.py``
and visible from every test directory.
"""

import pytest

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
