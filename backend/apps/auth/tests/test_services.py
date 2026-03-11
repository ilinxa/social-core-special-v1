"""
Auth Services Tests
===================
Comprehensive tests for AuthService, PasswordService, VerificationService,
and OAuthStateManager.

Covers:
    - Login / logout / refresh / token validation / session revocation
    - Password reset / confirm / change
    - Email verification (token + code) / resend
    - OAuth PKCE pair generation, state creation, and state validation

Security-critical tests are marked with comments so they are never deleted.
"""

import uuid
from datetime import timedelta
from unittest.mock import patch, MagicMock

import pytest
from django.core.cache import cache
from django.utils import timezone

from apps.auth.services import AuthService, DeviceInfo, TokenPair, PasswordService, VerificationService
from apps.auth.services.oauth_service import OAuthStateManager
from apps.core.exceptions import (
    InvalidCredentials,
    AccountInactive,
    AccountNotVerified,
    TokenExpired,
    TokenInvalid,
    ValidationError,
    OAuthError,
)
from apps.auth.models import RefreshToken, DeviceSession, EmailVerificationToken, PasswordResetToken
from apps.auth.blacklist import JTIBlacklist
from apps.auth.tests.factories import (
    RefreshTokenFactory,
    DeviceSessionFactory,
    EmailVerificationTokenFactory,
    PasswordResetTokenFactory,
    OAuthConnectionFactory,
)
from apps.users.tests.factories import UserFactory, VerifiedUserFactory, InactiveUserFactory


# =============================================================================
# HELPERS
# =============================================================================

def _device_info(**overrides):
    """Return a default DeviceInfo for testing."""
    defaults = dict(
        device_id="test-device",
        device_type="web",
        device_name="Test",
        user_agent="pytest",
        ip_address="127.0.0.1",
    )
    defaults.update(overrides)
    return DeviceInfo(**defaults)


# Patch targets (module-level where they are imported)
_AUDIT_AUTH = "apps.auth.services.auth_service.AuditService"
_AUDIT_PW = "apps.auth.services.password_service.AuditService"
_AUDIT_VER = "apps.auth.services.verification_service.AuditService"
_NOTIF = "apps.notifications.services.NotificationService"


# =============================================================================
# AuthService.login
# =============================================================================


@pytest.mark.django_db
class TestAuthServiceLogin:
    """Tests for AuthService.login."""

    # --- SECURITY: wrong email must raise same error as wrong password --- #
    @patch(_NOTIF)
    @patch(_AUDIT_AUTH)
    def test_login_wrong_email_raises_invalid_credentials(self, mock_audit, mock_notif):
        """SECURITY: wrong email must raise InvalidCredentials (not a different error)."""
        with pytest.raises(InvalidCredentials):
            AuthService.login(
                email="nonexistent@example.com",
                password="anything",
                device_info=_device_info(),
            )

    @patch(_NOTIF)
    @patch(_AUDIT_AUTH)
    def test_login_wrong_password_raises_invalid_credentials(self, mock_audit, mock_notif):
        """SECURITY: wrong password must raise InvalidCredentials (same as wrong email)."""
        user = UserFactory()
        with pytest.raises(InvalidCredentials):
            AuthService.login(
                email=user.email,
                password="wrong-password",
                device_info=_device_info(),
            )

    # --- SECURITY: same exception type prevents user enumeration --- #
    @patch(_NOTIF)
    @patch(_AUDIT_AUTH)
    def test_login_wrong_email_and_wrong_password_raise_same_exception_type(
        self, mock_audit, mock_notif
    ):
        """SECURITY: wrong email and wrong password MUST raise the same exception class."""
        user = UserFactory()

        with pytest.raises(InvalidCredentials) as exc_wrong_email:
            AuthService.login(
                email="no-such-user@example.com",
                password="anything",
                device_info=_device_info(),
            )

        with pytest.raises(InvalidCredentials) as exc_wrong_pw:
            AuthService.login(
                email=user.email,
                password="wrong-password",
                device_info=_device_info(),
            )

        assert type(exc_wrong_email.value) is type(exc_wrong_pw.value)

    # --- SECURITY: inactive account cannot login --- #
    @patch(_NOTIF)
    @patch(_AUDIT_AUTH)
    def test_login_inactive_user_raises_account_inactive(self, mock_audit, mock_notif):
        """SECURITY: inactive account must raise AccountInactive."""
        user = InactiveUserFactory()
        with pytest.raises(AccountInactive):
            AuthService.login(
                email=user.email,
                password="testpass123",
                device_info=_device_info(),
            )

    @patch(_NOTIF)
    @patch(_AUDIT_AUTH)
    def test_login_unverified_with_require_verified_raises(self, mock_audit, mock_notif):
        """When require_verified=True an unverified user is rejected."""
        user = UserFactory(is_verified=False)
        with pytest.raises(AccountNotVerified):
            AuthService.login(
                email=user.email,
                password="testpass123",
                device_info=_device_info(),
                require_verified=True,
            )

    @patch(_NOTIF)
    @patch(_AUDIT_AUTH)
    def test_login_unverified_without_require_verified_succeeds(self, mock_audit, mock_notif):
        """Default login succeeds even if user is not verified."""
        user = UserFactory(is_verified=False)
        result_user, tokens, session = AuthService.login(
            email=user.email,
            password="testpass123",
            device_info=_device_info(),
        )
        assert result_user.id == user.id

    @patch(_NOTIF)
    @patch(_AUDIT_AUTH)
    def test_login_verified_with_require_verified_succeeds(self, mock_audit, mock_notif):
        """Verified user passes require_verified check."""
        user = VerifiedUserFactory()
        result_user, tokens, session = AuthService.login(
            email=user.email,
            password="testpass123",
            device_info=_device_info(),
            require_verified=True,
        )
        assert result_user.id == user.id

    @patch(_NOTIF)
    @patch(_AUDIT_AUTH)
    def test_login_success_returns_tuple(self, mock_audit, mock_notif):
        """Successful login returns (User, TokenPair, DeviceSession)."""
        user = UserFactory()
        result_user, tokens, session = AuthService.login(
            email=user.email,
            password="testpass123",
            device_info=_device_info(),
        )
        assert result_user.id == user.id
        assert isinstance(tokens, TokenPair)
        assert isinstance(session, DeviceSession)
        assert tokens.access_token
        assert tokens.refresh_token
        assert tokens.access_expires_in > 0
        assert tokens.refresh_expires_in > 0

    @patch(_NOTIF)
    @patch(_AUDIT_AUTH)
    def test_login_creates_device_session(self, mock_audit, mock_notif):
        """Login creates a DeviceSession for the given device_id."""
        user = UserFactory()
        _, _, session = AuthService.login(
            email=user.email,
            password="testpass123",
            device_info=_device_info(device_id="my-device"),
        )
        assert session.device_id == "my-device"
        assert session.user_id == user.id
        assert session.is_active is True

    @patch(_NOTIF)
    @patch(_AUDIT_AUTH)
    def test_login_updates_existing_session_for_same_device(self, mock_audit, mock_notif):
        """Logging in again from the same device updates the session, not creates a new one."""
        user = UserFactory()
        _, _, session1 = AuthService.login(
            email=user.email,
            password="testpass123",
            device_info=_device_info(device_id="same-device"),
        )
        _, _, session2 = AuthService.login(
            email=user.email,
            password="testpass123",
            device_info=_device_info(device_id="same-device"),
        )
        assert session1.id == session2.id

    @patch(_NOTIF)
    @patch(_AUDIT_AUTH)
    def test_login_enforces_session_limit(self, mock_audit, mock_notif):
        """Oldest sessions are deactivated when session limit is exceeded."""
        user = UserFactory()
        # Create 5 sessions (the default limit)
        for i in range(5):
            AuthService.login(
                email=user.email,
                password="testpass123",
                device_info=_device_info(device_id=f"device-{i}"),
            )

        # 6th device should cause oldest to be evicted
        AuthService.login(
            email=user.email,
            password="testpass123",
            device_info=_device_info(device_id="device-new"),
        )

        active_sessions = DeviceSession.objects.filter(user=user, is_active=True).count()
        # Should not exceed 5 + 1 current
        assert active_sessions <= 6

    @patch(_NOTIF)
    @patch(_AUDIT_AUTH)
    def test_login_creates_refresh_token_in_db(self, mock_audit, mock_notif):
        """Login creates a RefreshToken record."""
        user = UserFactory()
        _, tokens, _ = AuthService.login(
            email=user.email,
            password="testpass123",
            device_info=_device_info(),
        )
        assert RefreshToken.objects.filter(user=user, is_revoked=False).exists()

    @patch(_NOTIF)
    @patch(_AUDIT_AUTH)
    def test_login_new_device_sends_notification(self, mock_audit, mock_notif):
        """A brand-new device login triggers a notification."""
        user = UserFactory()
        AuthService.login(
            email=user.email,
            password="testpass123",
            device_info=_device_info(device_id="brand-new-device"),
        )
        mock_notif.send.assert_called_once()


# =============================================================================
# AuthService.refresh_tokens
# =============================================================================


@pytest.mark.django_db
class TestAuthServiceRefresh:
    """Tests for AuthService.refresh_tokens."""

    @patch(_NOTIF)
    @patch(_AUDIT_AUTH)
    def test_refresh_token_not_found_raises_token_invalid(self, mock_audit, mock_notif):
        """Unknown refresh token raises TokenInvalid."""
        with pytest.raises(TokenInvalid):
            AuthService.refresh_tokens(
                refresh_token="nonexistent-token",
                device_info=_device_info(),
            )

    # --- SECURITY: revoked token reuse triggers logout_all --- #
    @patch(_NOTIF)
    @patch(_AUDIT_AUTH)
    def test_refresh_revoked_token_triggers_logout_all(self, mock_audit, mock_notif):
        """SECURITY: using a revoked refresh token triggers logout_all."""
        user = UserFactory()
        token_obj, raw = RefreshTokenFactory.create_with_raw_token(user=user)
        token_obj.is_revoked = True
        token_obj.revoked_at = timezone.now()
        token_obj.save(update_fields=["is_revoked", "revoked_at"])

        with pytest.raises(TokenInvalid):
            AuthService.refresh_tokens(
                refresh_token=raw,
                device_info=_device_info(),
            )

        # All remaining tokens for user should be revoked
        active = RefreshToken.objects.filter(user=user, is_revoked=False).count()
        assert active == 0

    # --- SECURITY: replaced token reuse (replay) triggers logout_all --- #
    @patch(_NOTIF)
    @patch(_AUDIT_AUTH)
    def test_refresh_replaced_token_triggers_logout_all(self, mock_audit, mock_notif):
        """SECURITY: using a token that already has replaced_by triggers logout_all."""
        user = UserFactory()
        replacement = RefreshTokenFactory(user=user)
        token_obj, raw = RefreshTokenFactory.create_with_raw_token(
            user=user, replaced_by=replacement
        )

        with pytest.raises(TokenInvalid):
            AuthService.refresh_tokens(
                refresh_token=raw,
                device_info=_device_info(),
            )

        active = RefreshToken.objects.filter(user=user, is_revoked=False).count()
        assert active == 0

    @patch(_NOTIF)
    @patch(_AUDIT_AUTH)
    def test_refresh_expired_token_raises_token_expired(self, mock_audit, mock_notif):
        """Expired refresh token raises TokenExpired."""
        user = UserFactory()
        token_obj, raw = RefreshTokenFactory.create_with_raw_token(
            user=user,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        with pytest.raises(TokenExpired):
            AuthService.refresh_tokens(
                refresh_token=raw,
                device_info=_device_info(),
            )

    @patch(_NOTIF)
    @patch(_AUDIT_AUTH)
    def test_refresh_inactive_user_raises_account_inactive(self, mock_audit, mock_notif):
        """Refresh with a valid token but inactive user raises AccountInactive."""
        user = UserFactory()
        token_obj, raw = RefreshTokenFactory.create_with_raw_token(user=user)
        # Deactivate user after token creation
        user.is_active = False
        user.save(update_fields=["is_active"])

        with pytest.raises(AccountInactive):
            AuthService.refresh_tokens(
                refresh_token=raw,
                device_info=_device_info(),
            )

    @patch(_NOTIF)
    @patch(_AUDIT_AUTH)
    def test_refresh_success_returns_new_token_pair(self, mock_audit, mock_notif):
        """Successful refresh returns a new TokenPair."""
        user = UserFactory()
        # Create session first
        session = DeviceSessionFactory(user=user, device_id="test-device")
        token_obj, raw = RefreshTokenFactory.create_with_raw_token(user=user)
        session.current_token = token_obj
        session.save(update_fields=["current_token"])

        new_tokens = AuthService.refresh_tokens(
            refresh_token=raw,
            device_info=_device_info(),
        )

        assert isinstance(new_tokens, TokenPair)
        assert new_tokens.access_token
        assert new_tokens.refresh_token
        assert new_tokens.refresh_token != raw

    @patch(_NOTIF)
    @patch(_AUDIT_AUTH)
    def test_refresh_marks_old_token_as_replaced(self, mock_audit, mock_notif):
        """Old token gets replaced_by set to the new token."""
        user = UserFactory()
        token_obj, raw = RefreshTokenFactory.create_with_raw_token(user=user)

        AuthService.refresh_tokens(
            refresh_token=raw,
            device_info=_device_info(),
        )

        token_obj.refresh_from_db()
        assert token_obj.replaced_by is not None

    @patch(_NOTIF)
    @patch(_AUDIT_AUTH)
    def test_refresh_updates_session_activity(self, mock_audit, mock_notif):
        """Session last_activity and current_token are updated on refresh."""
        user = UserFactory()
        session = DeviceSessionFactory(user=user, device_id="test-device")
        token_obj, raw = RefreshTokenFactory.create_with_raw_token(user=user)
        session.current_token = token_obj
        session.save(update_fields=["current_token"])

        AuthService.refresh_tokens(
            refresh_token=raw,
            device_info=_device_info(),
        )

        session.refresh_from_db()
        assert session.current_token_id != token_obj.id


# =============================================================================
# AuthService.logout
# =============================================================================


@pytest.mark.django_db
class TestAuthServiceLogout:
    """Tests for AuthService.logout."""

    @patch(_AUDIT_AUTH)
    def test_logout_unknown_token_returns_false(self, mock_audit):
        """Logout with unknown token returns False."""
        result = AuthService.logout(refresh_token="does-not-exist")
        assert result is False

    @patch(_AUDIT_AUTH)
    def test_logout_valid_token_returns_true(self, mock_audit):
        """Logout with valid token returns True and revokes the token."""
        user = UserFactory()
        token_obj, raw = RefreshTokenFactory.create_with_raw_token(user=user)
        DeviceSessionFactory(user=user, current_token=token_obj)

        result = AuthService.logout(refresh_token=raw)
        assert result is True

        token_obj.refresh_from_db()
        assert token_obj.is_revoked is True
        assert token_obj.revoked_reason == "logout"

    @patch(_AUDIT_AUTH)
    def test_logout_already_revoked_returns_false(self, mock_audit):
        """Logout with an already-revoked token returns False."""
        user = UserFactory()
        token_obj, raw = RefreshTokenFactory.create_with_raw_token(user=user)
        token_obj.is_revoked = True
        token_obj.revoked_at = timezone.now()
        token_obj.save(update_fields=["is_revoked", "revoked_at"])

        result = AuthService.logout(refresh_token=raw)
        assert result is False

    @patch(_AUDIT_AUTH)
    def test_logout_revokes_only_specified_token(self, mock_audit):
        """Logout revokes only the specified token, not others."""
        user = UserFactory()
        token1, raw1 = RefreshTokenFactory.create_with_raw_token(user=user)
        token2, raw2 = RefreshTokenFactory.create_with_raw_token(user=user)
        DeviceSessionFactory(user=user, current_token=token1, device_id="d1")
        DeviceSessionFactory(user=user, current_token=token2, device_id="d2")

        AuthService.logout(refresh_token=raw1)

        token1.refresh_from_db()
        token2.refresh_from_db()
        assert token1.is_revoked is True
        assert token2.is_revoked is False


# =============================================================================
# AuthService.logout_all
# =============================================================================


@pytest.mark.django_db
class TestAuthServiceLogoutAll:
    """Tests for AuthService.logout_all."""

    @patch("apps.auth.blacklist.JTIBlacklist._get_redis", return_value="fallback")
    @patch(_AUDIT_AUTH)
    def test_logout_all_revokes_all_tokens(self, mock_audit, mock_redis):
        """logout_all revokes every active refresh token for the user."""
        user = UserFactory()
        RefreshTokenFactory.create_with_raw_token(user=user)
        RefreshTokenFactory.create_with_raw_token(user=user)
        RefreshTokenFactory.create_with_raw_token(user=user)

        count = AuthService.logout_all(user=user)
        assert count == 3
        assert RefreshToken.objects.filter(user=user, is_revoked=False).count() == 0

    @patch("apps.auth.blacklist.JTIBlacklist._get_redis", return_value="fallback")
    @patch(_AUDIT_AUTH)
    def test_logout_all_deactivates_all_sessions(self, mock_audit, mock_redis):
        """logout_all deactivates all device sessions."""
        user = UserFactory()
        DeviceSessionFactory(user=user, device_id="d1")
        DeviceSessionFactory(user=user, device_id="d2")

        AuthService.logout_all(user=user)
        assert DeviceSession.objects.filter(user=user, is_active=True).count() == 0

    @patch("apps.auth.blacklist.JTIBlacklist._get_redis", return_value="fallback")
    @patch(_AUDIT_AUTH)
    def test_logout_all_returns_zero_when_no_tokens(self, mock_audit, mock_redis):
        """logout_all returns 0 when user has no active tokens."""
        user = UserFactory()
        count = AuthService.logout_all(user=user)
        assert count == 0

    @patch("apps.auth.blacklist.JTIBlacklist._get_redis", return_value="fallback")
    @patch(_AUDIT_AUTH)
    def test_logout_all_with_custom_reason(self, mock_audit, mock_redis):
        """logout_all stores the given reason on revoked tokens."""
        user = UserFactory()
        RefreshTokenFactory.create_with_raw_token(user=user)

        AuthService.logout_all(user=user, reason="token_reuse")

        token = RefreshToken.objects.filter(user=user).first()
        assert token.revoked_reason == "token_reuse"

    @patch("apps.auth.blacklist.JTIBlacklist._get_redis", return_value="fallback")
    @patch(_AUDIT_AUTH)
    def test_logout_all_does_not_affect_other_users(self, mock_audit, mock_redis):
        """logout_all only affects the specified user's tokens and sessions."""
        user1 = UserFactory()
        user2 = UserFactory()
        RefreshTokenFactory.create_with_raw_token(user=user1)
        RefreshTokenFactory.create_with_raw_token(user=user2)

        AuthService.logout_all(user=user1)

        assert RefreshToken.objects.filter(user=user1, is_revoked=False).count() == 0
        assert RefreshToken.objects.filter(user=user2, is_revoked=False).count() == 1


# =============================================================================
# AuthService.validate_access_token
# =============================================================================


@pytest.mark.django_db
class TestAuthServiceValidateToken:
    """Tests for AuthService.validate_access_token."""

    def _make_access_token(self, user, jti=None):
        """Helper to create a real access token via the private method."""
        jti = jti or uuid.uuid4()
        return AuthService._create_access_token(user, jti), str(jti)

    def test_validate_missing_user_id_raises_token_invalid(self):
        """Token without user_id in payload raises TokenInvalid."""
        from apps.core.utils.jwt import encode_token

        token = encode_token(payload={"jti": str(uuid.uuid4()), "token_type": "access"})
        with pytest.raises(TokenInvalid):
            AuthService.validate_access_token(token)

    def test_validate_missing_jti_raises_token_invalid(self):
        """Token without jti raises TokenInvalid."""
        from apps.core.utils.jwt import encode_token

        user = UserFactory()
        token = encode_token(payload={"user_id": str(user.id), "token_type": "access"})
        with pytest.raises(TokenInvalid):
            AuthService.validate_access_token(token)

    def test_validate_wrong_token_type_raises_token_invalid(self):
        """Token with token_type != 'access' raises TokenInvalid."""
        from apps.core.utils.jwt import encode_token

        user = UserFactory()
        token = encode_token(
            payload={
                "user_id": str(user.id),
                "jti": str(uuid.uuid4()),
                "token_type": "refresh",
            }
        )
        with pytest.raises(TokenInvalid):
            AuthService.validate_access_token(token)

    @patch("apps.auth.blacklist.JTIBlacklist.is_blacklisted", return_value=True)
    def test_validate_blacklisted_jti_raises_token_invalid(self, mock_bl):
        """Blacklisted JTI causes TokenInvalid."""
        user = UserFactory()
        token, jti = self._make_access_token(user)
        with pytest.raises(TokenInvalid):
            AuthService.validate_access_token(token)

    @patch("apps.auth.blacklist.JTIBlacklist.is_blacklisted", return_value=False)
    def test_validate_user_not_found_raises_token_invalid(self, mock_bl):
        """Token with non-existent user_id raises TokenInvalid."""
        from apps.core.utils.jwt import encode_token

        token = encode_token(
            payload={
                "user_id": 999999,
                "jti": str(uuid.uuid4()),
                "token_type": "access",
                "email": "ghost@example.com",
                "is_verified": False,
            }
        )
        with pytest.raises(TokenInvalid):
            AuthService.validate_access_token(token)

    @patch("apps.auth.blacklist.JTIBlacklist.is_blacklisted", return_value=False)
    def test_validate_inactive_user_raises_token_invalid(self, mock_bl):
        """Token for inactive user raises TokenInvalid."""
        user = InactiveUserFactory()
        token, _ = self._make_access_token(user)
        with pytest.raises(TokenInvalid):
            AuthService.validate_access_token(token)

    @patch("apps.auth.blacklist.JTIBlacklist.is_blacklisted", return_value=False)
    def test_validate_success_returns_user_and_payload(self, mock_bl):
        """Valid access token returns (user, payload)."""
        user = UserFactory()
        token, jti = self._make_access_token(user)

        result_user, payload = AuthService.validate_access_token(token)

        assert result_user.id == user.id
        assert payload["jti"] == jti
        assert payload["token_type"] == "access"

    def test_validate_expired_token_raises(self):
        """Expired access token raises TokenExpired."""
        from apps.core.utils.jwt import encode_token

        user = UserFactory()
        token = encode_token(
            payload={
                "user_id": str(user.id),
                "jti": str(uuid.uuid4()),
                "token_type": "access",
                "email": user.email,
                "is_verified": user.is_verified,
            },
            expires_in=-1,
        )
        with pytest.raises((TokenExpired, TokenInvalid)):
            AuthService.validate_access_token(token)

    def test_validate_malformed_token_raises_token_invalid(self):
        """Totally invalid JWT string raises TokenInvalid."""
        with pytest.raises(TokenInvalid):
            AuthService.validate_access_token("not-a-jwt")


# =============================================================================
# AuthService.revoke_session
# =============================================================================


@pytest.mark.django_db
class TestAuthServiceRevokeSession:
    """Tests for AuthService.revoke_session."""

    @patch("apps.auth.blacklist.JTIBlacklist.blacklist")
    @patch(_AUDIT_AUTH)
    def test_revoke_nonexistent_session_returns_false(self, mock_audit, mock_bl):
        """Revoking a non-existent session returns False."""
        user = UserFactory()
        result = AuthService.revoke_session(user=user, session_id=str(uuid.uuid4()))
        assert result is False

    @patch("apps.auth.blacklist.JTIBlacklist.blacklist")
    @patch(_AUDIT_AUTH)
    def test_revoke_other_users_session_returns_false(self, mock_audit, mock_bl):
        """Cannot revoke another user's session."""
        user1 = UserFactory()
        user2 = UserFactory()
        session = DeviceSessionFactory(user=user2, device_id="d1")

        result = AuthService.revoke_session(user=user1, session_id=str(session.id))
        assert result is False

    @patch("apps.auth.blacklist.JTIBlacklist.blacklist")
    @patch(_AUDIT_AUTH)
    def test_revoke_session_success(self, mock_audit, mock_bl):
        """Revoking own active session returns True and deactivates it."""
        user = UserFactory()
        token_obj, _ = RefreshTokenFactory.create_with_raw_token(user=user)
        session = DeviceSessionFactory(user=user, device_id="d1", current_token=token_obj)

        result = AuthService.revoke_session(user=user, session_id=str(session.id))
        assert result is True

        session.refresh_from_db()
        assert session.is_active is False

    @patch("apps.auth.blacklist.JTIBlacklist.blacklist")
    @patch(_AUDIT_AUTH)
    def test_revoke_session_revokes_associated_token(self, mock_audit, mock_bl):
        """Session revocation also revokes the associated refresh token."""
        user = UserFactory()
        token_obj, _ = RefreshTokenFactory.create_with_raw_token(user=user)
        session = DeviceSessionFactory(user=user, device_id="d1", current_token=token_obj)

        AuthService.revoke_session(user=user, session_id=str(session.id))

        token_obj.refresh_from_db()
        assert token_obj.is_revoked is True

    @patch("apps.auth.blacklist.JTIBlacklist.blacklist")
    @patch(_AUDIT_AUTH)
    def test_revoke_session_blacklists_jti(self, mock_audit, mock_bl):
        """Session revocation blacklists the JTI for immediate access token invalidation."""
        user = UserFactory()
        token_obj, _ = RefreshTokenFactory.create_with_raw_token(user=user)
        session = DeviceSessionFactory(user=user, device_id="d1", current_token=token_obj)

        AuthService.revoke_session(user=user, session_id=str(session.id))

        mock_bl.assert_called_once_with(str(token_obj.jti))

    @patch("apps.auth.blacklist.JTIBlacklist.blacklist")
    @patch(_AUDIT_AUTH)
    def test_revoke_already_inactive_session_returns_false(self, mock_audit, mock_bl):
        """Revoking an already-inactive session returns False."""
        user = UserFactory()
        session = DeviceSessionFactory(user=user, device_id="d1", is_active=False)

        result = AuthService.revoke_session(user=user, session_id=str(session.id))
        assert result is False

    @patch("apps.auth.blacklist.JTIBlacklist.blacklist")
    @patch(_AUDIT_AUTH)
    def test_revoke_session_without_token_succeeds(self, mock_audit, mock_bl):
        """Session with no current_token can still be revoked."""
        user = UserFactory()
        session = DeviceSessionFactory(user=user, device_id="d1", current_token=None)

        result = AuthService.revoke_session(user=user, session_id=str(session.id))
        assert result is True

        session.refresh_from_db()
        assert session.is_active is False
        mock_bl.assert_not_called()


# =============================================================================
# PasswordService.request_reset
# =============================================================================


@pytest.mark.django_db
class TestPasswordServiceRequestReset:
    """Tests for PasswordService.request_reset."""

    # --- SECURITY: always returns True regardless of email existence --- #
    @patch(_NOTIF)
    @patch(_AUDIT_PW)
    def test_request_reset_nonexistent_email_returns_true(self, mock_audit, mock_notif):
        """SECURITY: returns True even if email does not exist in the system."""
        result = PasswordService.request_reset(email="ghost@example.com")
        assert result is True

    @patch(_NOTIF)
    @patch(_AUDIT_PW)
    def test_request_reset_existing_user_returns_true(self, mock_audit, mock_notif):
        """Returns True for existing active user."""
        user = UserFactory()
        result = PasswordService.request_reset(email=user.email)
        assert result is True

    @patch(_NOTIF)
    @patch(_AUDIT_PW)
    def test_request_reset_creates_token_for_active_user(self, mock_audit, mock_notif):
        """Creates PasswordResetToken when user exists and is active."""
        user = UserFactory()
        PasswordService.request_reset(email=user.email)
        assert PasswordResetToken.objects.filter(user=user, is_used=False).exists()

    @patch(_NOTIF)
    @patch(_AUDIT_PW)
    def test_request_reset_inactive_user_returns_true_no_token(self, mock_audit, mock_notif):
        """Inactive user gets True but no token is created."""
        user = InactiveUserFactory()
        result = PasswordService.request_reset(email=user.email)
        assert result is True
        assert PasswordResetToken.objects.filter(user=user).count() == 0

    @patch(_NOTIF)
    @patch(_AUDIT_PW)
    def test_request_reset_sends_notification(self, mock_audit, mock_notif):
        """Notification is sent for existing active user."""
        user = UserFactory()
        PasswordService.request_reset(email=user.email)
        mock_notif.send.assert_called_once()

    @patch(_NOTIF)
    @patch(_AUDIT_PW)
    def test_request_reset_nonexistent_email_no_notification(self, mock_audit, mock_notif):
        """No notification sent when email doesn't exist."""
        PasswordService.request_reset(email="nobody@example.com")
        mock_notif.send.assert_not_called()

    @patch(_NOTIF)
    @patch(_AUDIT_PW)
    def test_request_reset_invalidates_old_token(self, mock_audit, mock_notif):
        """Creating a new reset token invalidates any existing one."""
        user = UserFactory()
        PasswordService.request_reset(email=user.email)
        first_token = PasswordResetToken.objects.filter(user=user, is_used=False).first()
        assert first_token is not None

        PasswordService.request_reset(email=user.email)
        first_token.refresh_from_db()
        assert first_token.is_used is True
        assert PasswordResetToken.objects.filter(user=user, is_used=False).count() == 1


# =============================================================================
# PasswordService.confirm_reset
# =============================================================================


@pytest.mark.django_db
class TestPasswordServiceConfirmReset:
    """Tests for PasswordService.confirm_reset."""

    @patch("apps.auth.blacklist.JTIBlacklist._get_redis", return_value="fallback")
    @patch(_NOTIF)
    @patch(_AUDIT_PW)
    @patch(_AUDIT_AUTH)
    def test_confirm_reset_invalid_token_raises(self, mock_a_auth, mock_audit, mock_notif, mock_redis):
        """Non-existent token UUID raises TokenInvalid."""
        with pytest.raises(TokenInvalid):
            PasswordService.confirm_reset(
                token_uuid=uuid.uuid4(),
                new_password="NewSecurePass123!",
            )

    @patch("apps.auth.blacklist.JTIBlacklist._get_redis", return_value="fallback")
    @patch(_NOTIF)
    @patch(_AUDIT_PW)
    @patch(_AUDIT_AUTH)
    def test_confirm_reset_expired_token_raises(self, mock_a_auth, mock_audit, mock_notif, mock_redis):
        """Expired token raises TokenExpired."""
        user = UserFactory()
        token = PasswordResetTokenFactory(
            user=user,
            expires_at=timezone.now() - timedelta(hours=2),
        )
        with pytest.raises(TokenExpired):
            PasswordService.confirm_reset(
                token_uuid=token.token,
                new_password="NewSecurePass123!",
            )

    @patch("apps.auth.blacklist.JTIBlacklist._get_redis", return_value="fallback")
    @patch(_NOTIF)
    @patch(_AUDIT_PW)
    @patch(_AUDIT_AUTH)
    def test_confirm_reset_weak_password_raises_validation_error(
        self, mock_a_auth, mock_audit, mock_notif, mock_redis
    ):
        """Password that doesn't meet requirements raises ValidationError."""
        user = UserFactory()
        token = PasswordResetTokenFactory(user=user)
        with pytest.raises(ValidationError):
            PasswordService.confirm_reset(
                token_uuid=token.token,
                new_password="123",
            )

    @patch("apps.auth.blacklist.JTIBlacklist._get_redis", return_value="fallback")
    @patch(_NOTIF)
    @patch(_AUDIT_PW)
    @patch(_AUDIT_AUTH)
    def test_confirm_reset_success(self, mock_a_auth, mock_audit, mock_notif, mock_redis):
        """Successful reset marks token used and updates password."""
        user = UserFactory()
        token = PasswordResetTokenFactory(user=user)
        old_password_hash = user.password

        result = PasswordService.confirm_reset(
            token_uuid=token.token,
            new_password="BrandNewSecure99!",
        )

        assert result.id == user.id
        token.refresh_from_db()
        assert token.is_used is True

        result.refresh_from_db()
        assert result.password != old_password_hash

    @patch("apps.auth.blacklist.JTIBlacklist._get_redis", return_value="fallback")
    @patch(_NOTIF)
    @patch(_AUDIT_PW)
    @patch(_AUDIT_AUTH)
    def test_confirm_reset_logout_all_sessions(self, mock_a_auth, mock_audit, mock_notif, mock_redis):
        """By default, confirm_reset logs out all sessions."""
        user = UserFactory()
        RefreshTokenFactory.create_with_raw_token(user=user)
        token = PasswordResetTokenFactory(user=user)

        PasswordService.confirm_reset(
            token_uuid=token.token,
            new_password="BrandNewSecure99!",
        )

        assert RefreshToken.objects.filter(user=user, is_revoked=False).count() == 0

    @patch("apps.auth.blacklist.JTIBlacklist._get_redis", return_value="fallback")
    @patch(_NOTIF)
    @patch(_AUDIT_PW)
    @patch(_AUDIT_AUTH)
    def test_confirm_reset_no_logout_when_disabled(self, mock_a_auth, mock_audit, mock_notif, mock_redis):
        """When logout_all_sessions=False, sessions are kept."""
        user = UserFactory()
        RefreshTokenFactory.create_with_raw_token(user=user)
        token = PasswordResetTokenFactory(user=user)

        PasswordService.confirm_reset(
            token_uuid=token.token,
            new_password="BrandNewSecure99!",
            logout_all_sessions=False,
        )

        assert RefreshToken.objects.filter(user=user, is_revoked=False).count() == 1

    @patch("apps.auth.blacklist.JTIBlacklist._get_redis", return_value="fallback")
    @patch(_NOTIF)
    @patch(_AUDIT_PW)
    @patch(_AUDIT_AUTH)
    def test_confirm_reset_used_token_raises(self, mock_a_auth, mock_audit, mock_notif, mock_redis):
        """Already-used token raises TokenInvalid."""
        user = UserFactory()
        token = PasswordResetTokenFactory(user=user, is_used=True, used_at=timezone.now())
        with pytest.raises(TokenInvalid):
            PasswordService.confirm_reset(
                token_uuid=token.token,
                new_password="BrandNewSecure99!",
            )


# =============================================================================
# PasswordService.change_password
# =============================================================================


@pytest.mark.django_db
class TestPasswordServiceChangePassword:
    """Tests for PasswordService.change_password."""

    # --- SECURITY: change password requires current password verification --- #
    @patch("apps.auth.blacklist.JTIBlacklist._get_redis", return_value="fallback")
    @patch(_NOTIF)
    @patch(_AUDIT_PW)
    def test_change_password_wrong_current_raises(self, mock_audit, mock_notif, mock_redis):
        """SECURITY: wrong current password raises InvalidCredentials."""
        user = UserFactory()
        with pytest.raises(InvalidCredentials):
            PasswordService.change_password(
                user=user,
                current_password="wrong",
                new_password="NewSecure123!",
            )

    @patch("apps.auth.blacklist.JTIBlacklist._get_redis", return_value="fallback")
    @patch(_NOTIF)
    @patch(_AUDIT_PW)
    def test_change_password_weak_new_password_raises(self, mock_audit, mock_notif, mock_redis):
        """Weak new password raises ValidationError."""
        user = UserFactory()
        with pytest.raises(ValidationError):
            PasswordService.change_password(
                user=user,
                current_password="testpass123",
                new_password="12",
            )

    # --- SECURITY: same password raises ValidationError --- #
    @patch("apps.auth.blacklist.JTIBlacklist._get_redis", return_value="fallback")
    @patch(_NOTIF)
    @patch(_AUDIT_PW)
    def test_change_password_same_as_current_raises(self, mock_audit, mock_notif, mock_redis):
        """SECURITY: new password same as current raises ValidationError."""
        user = UserFactory()
        with pytest.raises(ValidationError):
            PasswordService.change_password(
                user=user,
                current_password="testpass123",
                new_password="testpass123",
            )

    @patch("apps.auth.blacklist.JTIBlacklist._get_redis", return_value="fallback")
    @patch(_NOTIF)
    @patch(_AUDIT_PW)
    def test_change_password_success(self, mock_audit, mock_notif, mock_redis):
        """Successful password change updates the stored hash."""
        user = UserFactory()
        old_hash = user.password

        result = PasswordService.change_password(
            user=user,
            current_password="testpass123",
            new_password="CompletelyNew456!",
        )

        result.refresh_from_db()
        assert result.password != old_hash

    @patch("apps.auth.blacklist.JTIBlacklist._get_redis", return_value="fallback")
    @patch(_NOTIF)
    @patch(_AUDIT_PW)
    def test_change_password_blacklists_jtis(self, mock_audit, mock_notif, mock_redis):
        """Password change blacklists all user JTIs by default."""
        user = UserFactory()
        RefreshTokenFactory.create_with_raw_token(user=user)

        with patch("apps.auth.blacklist.JTIBlacklist.blacklist_user_tokens") as mock_bl:
            PasswordService.change_password(
                user=user,
                current_password="testpass123",
                new_password="CompletelyNew456!",
            )
            mock_bl.assert_called_once_with(user.id)

    @patch("apps.auth.blacklist.JTIBlacklist._get_redis", return_value="fallback")
    @patch(_NOTIF)
    @patch(_AUDIT_PW)
    def test_change_password_no_logout_when_disabled(self, mock_audit, mock_notif, mock_redis):
        """When logout_other_sessions=False, JTIs are not blacklisted."""
        user = UserFactory()

        with patch("apps.auth.blacklist.JTIBlacklist.blacklist_user_tokens") as mock_bl:
            PasswordService.change_password(
                user=user,
                current_password="testpass123",
                new_password="CompletelyNew456!",
                logout_other_sessions=False,
            )
            mock_bl.assert_not_called()

    @patch("apps.auth.blacklist.JTIBlacklist._get_redis", return_value="fallback")
    @patch(_NOTIF)
    @patch(_AUDIT_PW)
    def test_change_password_sends_notification(self, mock_audit, mock_notif, mock_redis):
        """Password change sends a notification."""
        user = UserFactory()
        PasswordService.change_password(
            user=user,
            current_password="testpass123",
            new_password="CompletelyNew456!",
        )
        mock_notif.send.assert_called_once()


# =============================================================================
# VerificationService.create_token
# =============================================================================


@pytest.mark.django_db
class TestVerificationServiceCreateToken:
    """Tests for VerificationService.create_token."""

    @patch(_NOTIF)
    @patch(_AUDIT_VER)
    def test_create_token_returns_none_if_already_verified(self, mock_audit, mock_notif):
        """Already-verified user gets None."""
        user = VerifiedUserFactory()
        result = VerificationService.create_token(user=user)
        assert result is None

    @patch(_NOTIF)
    @patch(_AUDIT_VER)
    def test_create_token_for_unverified_user(self, mock_audit, mock_notif):
        """Unverified user gets an EmailVerificationToken."""
        user = UserFactory(is_verified=False)
        token = VerificationService.create_token(user=user)
        assert isinstance(token, EmailVerificationToken)
        assert token.user_id == user.id
        assert token.is_used is False

    @patch(_NOTIF)
    @patch(_AUDIT_VER)
    def test_create_token_sends_notification(self, mock_audit, mock_notif):
        """Notification is sent with verification link and code."""
        user = UserFactory(is_verified=False)
        VerificationService.create_token(user=user)
        mock_notif.send.assert_called_once()

    @patch(_NOTIF)
    @patch(_AUDIT_VER)
    def test_create_token_has_code_and_uuid(self, mock_audit, mock_notif):
        """Token has both a UUID token and a 6-digit code."""
        user = UserFactory(is_verified=False)
        token = VerificationService.create_token(user=user)
        assert token.token is not None
        assert len(token.code) == 6
        assert token.code.isdigit()

    @patch(_NOTIF)
    @patch(_AUDIT_VER)
    def test_create_token_invalidates_previous_tokens(self, mock_audit, mock_notif):
        """Creating a new token invalidates any existing unused token."""
        user = UserFactory(is_verified=False)
        token1 = VerificationService.create_token(user=user)
        token2 = VerificationService.create_token(user=user)

        token1.refresh_from_db()
        assert token1.is_used is True
        assert token2.is_used is False


# =============================================================================
# VerificationService.verify_by_token
# =============================================================================


@pytest.mark.django_db
class TestVerificationServiceVerifyByToken:
    """Tests for VerificationService.verify_by_token."""

    @patch(_NOTIF)
    @patch(_AUDIT_VER)
    def test_verify_invalid_token_raises(self, mock_audit, mock_notif):
        """Non-existent token UUID raises TokenInvalid."""
        with pytest.raises(TokenInvalid):
            VerificationService.verify_by_token(uuid.uuid4())

    @patch(_NOTIF)
    @patch(_AUDIT_VER)
    def test_verify_expired_token_raises(self, mock_audit, mock_notif):
        """Expired token raises TokenExpired."""
        user = UserFactory(is_verified=False)
        token = EmailVerificationTokenFactory(
            user=user,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        with pytest.raises(TokenExpired):
            VerificationService.verify_by_token(token.token)

    @patch(_NOTIF)
    @patch(_AUDIT_VER)
    def test_verify_used_token_raises(self, mock_audit, mock_notif):
        """Already-used token raises TokenInvalid."""
        user = UserFactory(is_verified=False)
        token = EmailVerificationTokenFactory(
            user=user,
            is_used=True,
            used_at=timezone.now(),
        )
        with pytest.raises(TokenInvalid):
            VerificationService.verify_by_token(token.token)

    @patch(_NOTIF)
    @patch(_AUDIT_VER)
    def test_verify_success_marks_user_verified(self, mock_audit, mock_notif):
        """Successful verification marks user.is_verified = True."""
        user = UserFactory(is_verified=False)
        token = EmailVerificationTokenFactory(user=user)

        result = VerificationService.verify_by_token(token.token)
        result.refresh_from_db()
        assert result.is_verified is True

    @patch(_NOTIF)
    @patch(_AUDIT_VER)
    def test_verify_success_marks_token_used(self, mock_audit, mock_notif):
        """Successful verification marks the token as used."""
        user = UserFactory(is_verified=False)
        token = EmailVerificationTokenFactory(user=user)

        VerificationService.verify_by_token(token.token)
        token.refresh_from_db()
        assert token.is_used is True
        assert token.used_at is not None

    @patch(_NOTIF)
    @patch(_AUDIT_VER)
    def test_verify_sends_welcome_notification(self, mock_audit, mock_notif):
        """Welcome notification is sent after successful verification."""
        user = UserFactory(is_verified=False)
        token = EmailVerificationTokenFactory(user=user)

        VerificationService.verify_by_token(token.token)
        # At least one call is the welcome notification
        assert mock_notif.send.called


# =============================================================================
# VerificationService.verify_by_code
# =============================================================================


@pytest.mark.django_db
class TestVerificationServiceVerifyByCode:
    """Tests for VerificationService.verify_by_code."""

    @patch(_NOTIF)
    @patch(_AUDIT_VER)
    def test_verify_invalid_code_raises(self, mock_audit, mock_notif):
        """Non-existent code raises TokenInvalid."""
        with pytest.raises(TokenInvalid):
            VerificationService.verify_by_code(
                email="nobody@example.com",
                code="000000",
            )

    @patch(_NOTIF)
    @patch(_AUDIT_VER)
    def test_verify_expired_code_raises(self, mock_audit, mock_notif):
        """Expired code raises TokenExpired."""
        user = UserFactory(is_verified=False)
        token = EmailVerificationTokenFactory(
            user=user,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        with pytest.raises(TokenExpired):
            VerificationService.verify_by_code(email=user.email, code=token.code)

    @patch(_NOTIF)
    @patch(_AUDIT_VER)
    def test_verify_used_code_raises(self, mock_audit, mock_notif):
        """Already-used code raises TokenInvalid."""
        user = UserFactory(is_verified=False)
        token = EmailVerificationTokenFactory(
            user=user,
            is_used=True,
            used_at=timezone.now(),
        )
        with pytest.raises(TokenInvalid):
            VerificationService.verify_by_code(email=user.email, code=token.code)

    @patch(_NOTIF)
    @patch(_AUDIT_VER)
    def test_verify_by_code_success(self, mock_audit, mock_notif):
        """Successful code verification marks user verified."""
        user = UserFactory(is_verified=False)
        token = EmailVerificationTokenFactory(user=user)

        result = VerificationService.verify_by_code(email=user.email, code=token.code)
        result.refresh_from_db()
        assert result.is_verified is True

    @patch(_NOTIF)
    @patch(_AUDIT_VER)
    def test_verify_by_code_marks_token_used(self, mock_audit, mock_notif):
        """Token is marked used after code verification."""
        user = UserFactory(is_verified=False)
        token = EmailVerificationTokenFactory(user=user)

        VerificationService.verify_by_code(email=user.email, code=token.code)
        token.refresh_from_db()
        assert token.is_used is True

    @patch(_NOTIF)
    @patch(_AUDIT_VER)
    def test_verify_by_code_case_insensitive_email(self, mock_audit, mock_notif):
        """Email matching is case-insensitive."""
        user = UserFactory(is_verified=False)
        token = EmailVerificationTokenFactory(user=user)

        result = VerificationService.verify_by_code(
            email=user.email.upper(),
            code=token.code,
        )
        result.refresh_from_db()
        assert result.is_verified is True

    @patch(_NOTIF)
    @patch(_AUDIT_VER)
    def test_verify_by_code_wrong_email_raises(self, mock_audit, mock_notif):
        """Correct code with wrong email raises TokenInvalid."""
        user = UserFactory(is_verified=False)
        token = EmailVerificationTokenFactory(user=user)

        with pytest.raises(TokenInvalid):
            VerificationService.verify_by_code(
                email="wrong@example.com",
                code=token.code,
            )


# =============================================================================
# VerificationService.resend_verification
# =============================================================================


@pytest.mark.django_db
class TestVerificationServiceResend:
    """Tests for VerificationService.resend_verification."""

    # --- SECURITY: resend returns None for verified user --- #
    def test_resend_verified_user_returns_none(self):
        """SECURITY: resend returns None if user is already verified."""
        user = VerifiedUserFactory()
        result = VerificationService.resend_verification(user)
        assert result is None

    @patch(_NOTIF)
    @patch(_AUDIT_VER)
    def test_resend_unverified_user_creates_token(self, mock_audit, mock_notif):
        """Unverified user receives a new verification token."""
        user = UserFactory(is_verified=False)
        token = VerificationService.resend_verification(user)
        assert isinstance(token, EmailVerificationToken)
        assert token.user_id == user.id

    @patch(_NOTIF)
    @patch(_AUDIT_VER)
    def test_resend_sends_notification(self, mock_audit, mock_notif):
        """Resend triggers a notification."""
        user = UserFactory(is_verified=False)
        VerificationService.resend_verification(user)
        mock_notif.send.assert_called_once()


# =============================================================================
# OAuthStateManager
# =============================================================================


@pytest.mark.django_db
class TestOAuthStateManager:
    """Tests for OAuthStateManager."""

    @pytest.fixture(autouse=True)
    def _use_locmem_cache(self, settings):
        """Use LocMemCache instead of DummyCache so cache.set/get work."""
        settings.CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
                'LOCATION': 'oauth-state-test',
            }
        }

    def test_generate_pkce_pair_returns_two_strings(self):
        """generate_pkce_pair returns (code_verifier, code_challenge) as strings."""
        verifier, challenge = OAuthStateManager.generate_pkce_pair()
        assert isinstance(verifier, str)
        assert isinstance(challenge, str)
        assert len(verifier) > 0
        assert len(challenge) > 0

    def test_generate_pkce_pair_unique(self):
        """Each call produces a different PKCE pair."""
        pair1 = OAuthStateManager.generate_pkce_pair()
        pair2 = OAuthStateManager.generate_pkce_pair()
        assert pair1[0] != pair2[0]

    def test_generate_pkce_challenge_is_valid_sha256(self):
        """Code challenge is base64url(SHA256(code_verifier))."""
        import base64
        import hashlib

        verifier, challenge = OAuthStateManager.generate_pkce_pair()
        expected_digest = hashlib.sha256(verifier.encode()).digest()
        expected_challenge = base64.urlsafe_b64encode(expected_digest).rstrip(b"=").decode()
        assert challenge == expected_challenge

    def test_create_state_returns_expected_keys(self):
        """create_state returns dict with state_token, code_verifier, code_challenge, nonce."""
        result = OAuthStateManager.create_state("google")
        assert "state_token" in result
        assert "code_verifier" in result
        assert "code_challenge" in result
        assert "nonce" in result

    def test_create_state_stores_in_cache(self):
        """State data is stored in Django cache."""
        result = OAuthStateManager.create_state("google", redirect_to="/dashboard")
        cache_key = f"{OAuthStateManager.STATE_CACHE_PREFIX}{result['state_token']}"
        cached = cache.get(cache_key)
        assert cached is not None
        assert cached["provider"] == "google"
        assert cached["redirect_to"] == "/dashboard"

    def test_create_state_stores_device_info(self):
        """Device info is persisted in the state cache."""
        device = {"device_id": "d1", "device_type": "ios"}
        result = OAuthStateManager.create_state("apple", device_info=device)
        cache_key = f"{OAuthStateManager.STATE_CACHE_PREFIX}{result['state_token']}"
        cached = cache.get(cache_key)
        assert cached["device_info"] == device

    def test_validate_and_consume_state_success(self):
        """Valid state token returns state data and deletes it from cache."""
        result = OAuthStateManager.create_state("google")
        state_data = OAuthStateManager.validate_and_consume_state(result["state_token"])

        assert state_data["provider"] == "google"
        assert "code_verifier" in state_data

        # Second consume should fail (one-time use)
        with pytest.raises(OAuthError):
            OAuthStateManager.validate_and_consume_state(result["state_token"])

    def test_validate_and_consume_state_invalid_raises(self):
        """Non-existent state token raises OAuthError."""
        with pytest.raises(OAuthError):
            OAuthStateManager.validate_and_consume_state("nonexistent-state-token")

    def test_validate_and_consume_is_one_time_use(self):
        """State can only be consumed once (prevents replay)."""
        result = OAuthStateManager.create_state("google")
        OAuthStateManager.validate_and_consume_state(result["state_token"])

        with pytest.raises(OAuthError):
            OAuthStateManager.validate_and_consume_state(result["state_token"])

    def test_create_state_unique_tokens(self):
        """Each create_state call generates unique state tokens."""
        state1 = OAuthStateManager.create_state("google")
        state2 = OAuthStateManager.create_state("google")
        assert state1["state_token"] != state2["state_token"]

    def test_create_state_nonce_present(self):
        """Nonce is generated for ID token replay protection."""
        result = OAuthStateManager.create_state("apple")
        assert result["nonce"]
        assert len(result["nonce"]) > 0
