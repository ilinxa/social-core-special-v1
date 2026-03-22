# apps/auth/tests/conftest.py
"""
Pytest configuration and fixtures for Auth app tests.

These fixtures are available to all tests in the auth app.
"""

import pytest
from rest_framework.test import APIClient

from apps.auth.tests.factories import (
    AppleOAuthConnectionFactory,
    DeviceSessionFactory,
    EmailVerificationTokenFactory,
    ExpiredPasswordResetTokenFactory,
    ExpiredRefreshTokenFactory,
    ExpiredVerificationTokenFactory,
    GoogleOAuthConnectionFactory,
    OAuthConnectionFactory,
    PasswordResetTokenFactory,
    RefreshTokenFactory,
    RevokedRefreshTokenFactory,
    UsedPasswordResetTokenFactory,
    UsedVerificationTokenFactory,
)
from apps.users.tests.factories import (
    InactiveUserFactory,
    StaffUserFactory,
    SuperuserFactory,
    UserFactory,
    VerifiedUserFactory,
)

# =============================================================================
# ON-COMMIT FIXTURE
# =============================================================================


@pytest.fixture
def immediate_on_commit(monkeypatch):
    """Execute transaction.on_commit() callbacks immediately.

    Needed because pytest-django wraps tests in a transaction that never
    commits, so on_commit callbacks registered inside nested atomic blocks
    are deferred indefinitely. This fixture makes them fire synchronously.
    """
    monkeypatch.setattr(
        "django.db.transaction.on_commit",
        lambda func, using=None, robust=False: func(),
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


@pytest.fixture
def verified_client(api_client, verified_user):
    """Return an APIClient authenticated as a verified user."""
    api_client.force_authenticate(user=verified_user)
    return api_client


# =============================================================================
# USER FIXTURES
# =============================================================================


@pytest.fixture
def user(db):
    """Create and return a regular test user (unverified)."""
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
def inactive_user(db):
    """Create and return an inactive user."""
    return InactiveUserFactory()


@pytest.fixture
def another_user(db):
    """Create and return another regular test user."""
    return UserFactory(username="another_user", email="another@example.com")


# =============================================================================
# FACTORY FIXTURES
# =============================================================================


@pytest.fixture
def user_factory(db):
    """Return the UserFactory for creating users in tests."""
    return UserFactory


@pytest.fixture
def refresh_token_factory(db):
    """Return the RefreshTokenFactory."""
    return RefreshTokenFactory


@pytest.fixture
def device_session_factory(db):
    """Return the DeviceSessionFactory."""
    return DeviceSessionFactory


@pytest.fixture
def verification_token_factory(db):
    """Return the EmailVerificationTokenFactory."""
    return EmailVerificationTokenFactory


@pytest.fixture
def password_reset_token_factory(db):
    """Return the PasswordResetTokenFactory."""
    return PasswordResetTokenFactory


@pytest.fixture
def oauth_connection_factory(db):
    """Return the OAuthConnectionFactory."""
    return OAuthConnectionFactory


# =============================================================================
# URL FIXTURES
# =============================================================================


@pytest.fixture
def register_url():
    """Return the register endpoint URL."""
    return "/api/v1/auth/register/"


@pytest.fixture
def login_url():
    """Return the login endpoint URL."""
    return "/api/v1/auth/login/"


@pytest.fixture
def logout_url():
    """Return the logout endpoint URL."""
    return "/api/v1/auth/logout/"


@pytest.fixture
def logout_all_url():
    """Return the logout-all endpoint URL."""
    return "/api/v1/auth/logout-all/"


@pytest.fixture
def refresh_url():
    """Return the refresh endpoint URL."""
    return "/api/v1/auth/refresh/"


@pytest.fixture
def verify_email_code_url():
    """Return the verify-email (code) endpoint URL."""
    return "/api/v1/auth/verify-email/"


@pytest.fixture
def resend_verification_url():
    """Return the resend-verification endpoint URL."""
    return "/api/v1/auth/resend-verification/"


@pytest.fixture
def password_reset_url():
    """Return the password/reset endpoint URL."""
    return "/api/v1/auth/password/reset/"


@pytest.fixture
def password_reset_confirm_url():
    """Return the password/reset/confirm endpoint URL."""
    return "/api/v1/auth/password/reset/confirm/"


@pytest.fixture
def password_change_url():
    """Return the password/change endpoint URL."""
    return "/api/v1/auth/password/change/"


@pytest.fixture
def sessions_url():
    """Return the sessions list endpoint URL."""
    return "/api/v1/auth/sessions/"


@pytest.fixture
def oauth_google_url():
    """Return the Google OAuth init endpoint URL."""
    return "/api/v1/auth/oauth/google/"


@pytest.fixture
def oauth_google_callback_url():
    """Return the Google OAuth callback endpoint URL."""
    return "/api/v1/auth/oauth/google/callback/"


@pytest.fixture
def oauth_apple_url():
    """Return the Apple OAuth init endpoint URL."""
    return "/api/v1/auth/oauth/apple/"


@pytest.fixture
def oauth_apple_callback_url():
    """Return the Apple OAuth callback endpoint URL."""
    return "/api/v1/auth/oauth/apple/callback/"
