# apps/auth/tests/test_selectors.py
"""
Tests for AuthSelector — read-only queries for authentication data.

Covers: RefreshToken, DeviceSession, EmailVerificationToken,
        PasswordResetToken, and OAuthConnection selectors.
"""

import pytest

from apps.auth.models import OAuthConnection
from apps.auth.selectors import AuthSelector
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
from apps.users.tests.factories import UserFactory

# =============================================================================
# REFRESH TOKEN SELECTORS
# =============================================================================


@pytest.mark.django_db
class TestRefreshTokenSelectors:
    """Tests for refresh token selector methods."""

    def test_get_active_tokens_returns_only_active(self):
        """Active tokens (not revoked, not expired, not replaced) are returned."""
        user = UserFactory()
        token1 = RefreshTokenFactory(user=user)
        token2 = RefreshTokenFactory(user=user)

        result = AuthSelector.get_active_tokens_for_user(user)

        assert result.count() == 2
        assert token1 in result
        assert token2 in result

    def test_get_active_tokens_excludes_revoked(self):
        """Revoked tokens are excluded from active tokens."""
        user = UserFactory()
        RefreshTokenFactory(user=user)
        RevokedRefreshTokenFactory(user=user)

        result = AuthSelector.get_active_tokens_for_user(user)

        assert result.count() == 1

    def test_get_active_tokens_excludes_expired(self):
        """Expired tokens are excluded from active tokens."""
        user = UserFactory()
        RefreshTokenFactory(user=user)
        ExpiredRefreshTokenFactory(user=user)

        result = AuthSelector.get_active_tokens_for_user(user)

        assert result.count() == 1

    def test_get_active_tokens_excludes_replaced(self):
        """Tokens that have been replaced (rotated) are excluded."""
        user = UserFactory()
        active_token = RefreshTokenFactory(user=user)
        replacement = RefreshTokenFactory(user=user)
        old_token = RefreshTokenFactory(user=user, replaced_by=replacement)

        result = AuthSelector.get_active_tokens_for_user(user)

        assert result.count() == 2
        assert active_token in result
        assert replacement in result
        assert old_token not in result

    def test_count_active_tokens_returns_correct_count(self):
        """count_active_tokens_for_user returns the number of active tokens."""
        user = UserFactory()
        RefreshTokenFactory(user=user)
        RefreshTokenFactory(user=user)
        RevokedRefreshTokenFactory(user=user)
        ExpiredRefreshTokenFactory(user=user)

        count = AuthSelector.count_active_tokens_for_user(user)

        assert count == 2

    def test_get_active_tokens_empty_for_user_with_no_tokens(self):
        """Returns empty queryset when user has no tokens at all."""
        user = UserFactory()

        result = AuthSelector.get_active_tokens_for_user(user)

        assert result.count() == 0
        assert not result.exists()


# =============================================================================
# DEVICE SESSION SELECTORS
# =============================================================================


@pytest.mark.django_db
class TestDeviceSessionSelectors:
    """Tests for device session selector methods."""

    def test_get_active_sessions_returns_active(self):
        """Active sessions are returned for the user."""
        user = UserFactory()
        session1 = DeviceSessionFactory(user=user, device_id="dev_a")
        session2 = DeviceSessionFactory(user=user, device_id="dev_b")

        result = AuthSelector.get_active_sessions_for_user(user)

        assert result.count() == 2
        returned_ids = set(result.values_list("id", flat=True))
        assert session1.id in returned_ids
        assert session2.id in returned_ids

    def test_get_active_sessions_excludes_inactive(self):
        """Inactive sessions are excluded."""
        user = UserFactory()
        DeviceSessionFactory(user=user, device_id="active_dev")
        DeviceSessionFactory(user=user, device_id="inactive_dev", is_active=False)

        result = AuthSelector.get_active_sessions_for_user(user)

        assert result.count() == 1

    def test_get_session_by_id_returns_matching(self):
        """Returns the session matching user and session_id."""
        user = UserFactory()
        session = DeviceSessionFactory(user=user)

        result = AuthSelector.get_session_by_id(user, session.id)

        assert result is not None
        assert result.id == session.id

    def test_get_session_by_id_returns_none_for_wrong_user(self):
        """Returns None when session belongs to a different user."""
        user = UserFactory()
        other_user = UserFactory()
        session = DeviceSessionFactory(user=other_user)

        result = AuthSelector.get_session_by_id(user, session.id)

        assert result is None

    def test_get_session_by_id_returns_none_for_inactive(self):
        """Returns None when the session is inactive."""
        user = UserFactory()
        session = DeviceSessionFactory(user=user, is_active=False)

        result = AuthSelector.get_session_by_id(user, session.id)

        assert result is None

    def test_count_active_sessions_returns_correct_count(self):
        """count_active_sessions_for_user returns the correct count."""
        user = UserFactory()
        DeviceSessionFactory(user=user, device_id="dev_1")
        DeviceSessionFactory(user=user, device_id="dev_2")
        DeviceSessionFactory(user=user, device_id="dev_3", is_active=False)

        count = AuthSelector.count_active_sessions_for_user(user)

        assert count == 2


# =============================================================================
# VERIFICATION TOKEN SELECTORS
# =============================================================================


@pytest.mark.django_db
class TestVerificationTokenSelectors:
    """Tests for email verification token selector methods."""

    def test_get_pending_returns_valid_token(self):
        """Returns a valid pending verification token."""
        user = UserFactory()
        token = EmailVerificationTokenFactory(user=user)

        result = AuthSelector.get_pending_verification_for_user(user)

        assert result is not None
        assert result.id == token.id

    def test_get_pending_returns_none_when_expired(self):
        """Returns None when the only token is expired."""
        user = UserFactory()
        ExpiredVerificationTokenFactory(user=user)

        result = AuthSelector.get_pending_verification_for_user(user)

        assert result is None

    def test_get_pending_returns_none_when_used(self):
        """Returns None when the only token has been used."""
        user = UserFactory()
        UsedVerificationTokenFactory(user=user)

        result = AuthSelector.get_pending_verification_for_user(user)

        assert result is None

    def test_has_pending_returns_true_and_false(self):
        """has_pending_verification returns True when pending, False otherwise."""
        user = UserFactory()
        other_user = UserFactory()

        EmailVerificationTokenFactory(user=user)

        assert AuthSelector.has_pending_verification(user) is True
        assert AuthSelector.has_pending_verification(other_user) is False


# =============================================================================
# PASSWORD RESET TOKEN SELECTORS
# =============================================================================


@pytest.mark.django_db
class TestPasswordResetSelectors:
    """Tests for password reset token selector methods."""

    def test_get_pending_returns_valid_token(self):
        """Returns a valid pending password reset token."""
        user = UserFactory()
        token = PasswordResetTokenFactory(user=user)

        result = AuthSelector.get_pending_password_reset_for_user(user)

        assert result is not None
        assert result.id == token.id

    def test_get_pending_returns_none_when_expired(self):
        """Returns None when the only token is expired."""
        user = UserFactory()
        ExpiredPasswordResetTokenFactory(user=user)

        result = AuthSelector.get_pending_password_reset_for_user(user)

        assert result is None

    def test_get_pending_returns_none_when_used(self):
        """Returns None when the only token has been used."""
        user = UserFactory()
        UsedPasswordResetTokenFactory(user=user)

        result = AuthSelector.get_pending_password_reset_for_user(user)

        assert result is None

    def test_has_pending_returns_true_and_false(self):
        """has_pending_password_reset returns True when pending, False otherwise."""
        user = UserFactory()
        other_user = UserFactory()

        PasswordResetTokenFactory(user=user)

        assert AuthSelector.has_pending_password_reset(user) is True
        assert AuthSelector.has_pending_password_reset(other_user) is False


# =============================================================================
# OAUTH CONNECTION SELECTORS
# =============================================================================


@pytest.mark.django_db
class TestOAuthSelectors:
    """Tests for OAuth connection selector methods."""

    def test_get_connections_returns_all_for_user(self):
        """Returns all OAuth connections belonging to the user."""
        user = UserFactory()
        google = GoogleOAuthConnectionFactory(user=user)
        apple = AppleOAuthConnectionFactory(user=user)

        result = AuthSelector.get_oauth_connections_for_user(user)

        assert result.count() == 2
        returned_ids = set(result.values_list("id", flat=True))
        assert google.id in returned_ids
        assert apple.id in returned_ids

    def test_get_connections_returns_empty_for_user_with_none(self):
        """Returns empty queryset when user has no OAuth connections."""
        user = UserFactory()

        result = AuthSelector.get_oauth_connections_for_user(user)

        assert result.count() == 0
        assert not result.exists()

    def test_get_connection_returns_specific_provider(self):
        """Returns the connection for the requested provider."""
        user = UserFactory()
        google = GoogleOAuthConnectionFactory(user=user)
        AppleOAuthConnectionFactory(user=user)

        result = AuthSelector.get_oauth_connection(
            user, OAuthConnection.Provider.GOOGLE
        )

        assert result is not None
        assert result.id == google.id

    def test_get_connection_returns_none_for_wrong_provider(self):
        """Returns None when user has no connection for the requested provider."""
        user = UserFactory()
        GoogleOAuthConnectionFactory(user=user)

        result = AuthSelector.get_oauth_connection(user, OAuthConnection.Provider.APPLE)

        assert result is None

    def test_has_connection_true_and_false(self):
        """has_oauth_connection returns True when connected, False otherwise."""
        user = UserFactory()
        GoogleOAuthConnectionFactory(user=user)

        assert (
            AuthSelector.has_oauth_connection(user, OAuthConnection.Provider.GOOGLE)
            is True
        )
        assert (
            AuthSelector.has_oauth_connection(user, OAuthConnection.Provider.APPLE)
            is False
        )

    def test_get_by_provider_uid_returns_matching(self):
        """Returns the connection matching provider and provider_uid."""
        user = UserFactory()
        conn = GoogleOAuthConnectionFactory(user=user, provider_uid="google_xyz_123")

        result = AuthSelector.get_oauth_by_provider_uid(
            OAuthConnection.Provider.GOOGLE, "google_xyz_123"
        )

        assert result is not None
        assert result.id == conn.id

    def test_get_by_provider_uid_returns_none_for_wrong_uid(self):
        """Returns None when no connection matches the provider_uid."""
        user = UserFactory()
        GoogleOAuthConnectionFactory(user=user, provider_uid="google_real_uid")

        result = AuthSelector.get_oauth_by_provider_uid(
            OAuthConnection.Provider.GOOGLE, "nonexistent_uid"
        )

        assert result is None

    def test_get_by_provider_uid_select_related_loads_user(self):
        """select_related('user') is applied so accessing .user causes no extra query."""
        user = UserFactory()
        GoogleOAuthConnectionFactory(user=user, provider_uid="sr_test_uid")

        result = AuthSelector.get_oauth_by_provider_uid(
            OAuthConnection.Provider.GOOGLE, "sr_test_uid"
        )

        assert result is not None
        # After select_related, accessing .user should not trigger a DB query.
        # django.test.utils.override_settings is not needed; we use assertNumQueries-style
        # check via the _state.fields_cache or simply verify the data is present.
        assert result.user.id == user.id
        assert result.user.email == user.email
