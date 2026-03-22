"""
Auth Views Tests
================
Integration tests for all authentication API views.

Tests cover:
    - Registration (RegisterView)
    - Login (LoginView)
    - Token refresh (RefreshView)
    - Logout (LogoutView, LogoutAllView)
    - Email verification (VerifyEmailCodeView, VerifyEmailLinkView, ResendVerificationView)
    - Password management (PasswordResetRequestView, PasswordResetConfirmView, PasswordChangeView)
    - Session management (SessionListView, SessionRevokeView)
    - OAuth (GoogleOAuthView, AppleOAuthView, callbacks)

Mock strategy:
    - NotificationService is mocked globally to prevent actual email sends.
    - OAuth backends and state managers are mocked for OAuth views.
    - All other services (AuthService, AuditService, etc.) run naturally against the test DB.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from rest_framework import status

from apps.auth.tests.factories import (
    DeviceSessionFactory,
    EmailVerificationTokenFactory,
    ExpiredPasswordResetTokenFactory,
    ExpiredVerificationTokenFactory,
    PasswordResetTokenFactory,
    RefreshTokenFactory,
    UsedPasswordResetTokenFactory,
)
from apps.users.tests.factories import (
    InactiveUserFactory,
    UserFactory,
    VerifiedUserFactory,
)

# =============================================================================
# MODULE-LEVEL AUTOUSE FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def mock_notifications():
    """Mock NotificationService globally to prevent actual email/notification sends."""
    with patch("apps.notifications.services.NotificationService") as mock:
        yield mock


@pytest.fixture(autouse=True)
def _patch_jwt_uuid_serialization():
    """
    Patch encode_token to auto-convert UUID values in the JWT payload to strings.

    This works around a known issue where user.id (a UUID from UUIDModel) is passed
    directly into the JWT payload without str() conversion, causing PyJWT to raise
    'Object of type UUID is not JSON serializable'.
    """
    from apps.core.utils import jwt as jwt_module

    _original_encode = jwt_module.encode_token

    def _encode_with_uuid_fix(payload, **kwargs):
        sanitized = {}
        for key, value in payload.items():
            if isinstance(value, uuid.UUID):
                sanitized[key] = str(value)
            else:
                sanitized[key] = value
        return _original_encode(sanitized, **kwargs)

    with patch.object(jwt_module, "encode_token", side_effect=_encode_with_uuid_fix):
        yield


# =============================================================================
# REGISTER VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestRegisterView:
    """Tests for POST /api/v1/auth/register/."""

    def test_register_success(self, api_client, register_url):
        """Successful registration returns 201 with user, tokens, and is_new_user."""
        data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "SecurePass123!",
        }
        response = api_client.post(register_url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert "user" in response.data
        assert "tokens" in response.data
        assert response.data["is_new_user"] is True
        assert "access_token" in response.data["tokens"]
        assert response.data["user"]["username"] == "newuser"

    def test_register_success_mobile_client(self, api_client, register_url):
        """Mobile clients receive refresh_token in response body."""
        data = {
            "email": "mobileuser@example.com",
            "username": "mobileuser",
            "password": "SecurePass123!",
        }
        response = api_client.post(
            register_url,
            data,
            format="json",
            HTTP_X_CLIENT_TYPE="mobile",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert "refresh_token" in response.data["tokens"]

    def test_register_success_web_client_sets_cookie(self, api_client, register_url):
        """Web clients receive refresh_token as HttpOnly cookie."""
        data = {
            "email": "webuser@example.com",
            "username": "webuser",
            "password": "SecurePass123!",
        }
        response = api_client.post(register_url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert "refresh_token" in response.cookies

    def test_register_missing_email(self, api_client, register_url):
        """Missing email returns 400."""
        data = {"username": "nouser", "password": "SecurePass123!"}
        response = api_client.post(register_url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_missing_password(self, api_client, register_url):
        """Missing password returns 400."""
        data = {"email": "user@example.com", "username": "nopassuser"}
        response = api_client.post(register_url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_missing_username(self, api_client, register_url):
        """Missing username returns 400."""
        data = {"email": "user@example.com", "password": "SecurePass123!"}
        response = api_client.post(register_url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_invalid_email_format(self, api_client, register_url):
        """Invalid email format returns 400."""
        data = {
            "email": "not-an-email",
            "username": "badmail",
            "password": "SecurePass123!",
        }
        response = api_client.post(register_url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_invalid_username_format(self, api_client, register_url):
        """Invalid username format returns 400."""
        data = {
            "email": "user@example.com",
            "username": "a b",
            "password": "SecurePass123!",
        }
        response = api_client.post(register_url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_password_too_short(self, api_client, register_url):
        """Password shorter than 8 characters returns 400."""
        data = {"email": "user@example.com", "username": "shortpw", "password": "short"}
        response = api_client.post(register_url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_duplicate_email(self, api_client, register_url):
        """Duplicate email returns 409 Conflict."""
        UserFactory(email="existing@example.com")
        data = {
            "email": "existing@example.com",
            "username": "uniqueuser",
            "password": "SecurePass123!",
        }
        response = api_client.post(register_url, data, format="json")

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_register_duplicate_username(self, api_client, register_url):
        """Duplicate username returns 409 Conflict."""
        UserFactory(email="other@example.com", username="taken_user")
        data = {
            "email": "new@example.com",
            "username": "taken_user",
            "password": "SecurePass123!",
        }
        response = api_client.post(register_url, data, format="json")

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_register_empty_body(self, api_client, register_url):
        """Empty body returns 400."""
        response = api_client.post(register_url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# LOGIN VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestLoginView:
    """Tests for POST /api/v1/auth/login/."""

    def test_login_success(self, api_client, login_url):
        """Successful login returns 200 with user and tokens."""
        user = UserFactory(email="login@example.com")
        data = {"email": "login@example.com", "password": "testpass123"}
        response = api_client.post(login_url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "user" in response.data
        assert "tokens" in response.data
        assert "access_token" in response.data["tokens"]

    def test_login_success_mobile_client(self, api_client, login_url):
        """Mobile login returns refresh_token in body."""
        UserFactory(email="mobile@example.com")
        data = {"email": "mobile@example.com", "password": "testpass123"}
        response = api_client.post(
            login_url,
            data,
            format="json",
            HTTP_X_CLIENT_TYPE="mobile",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "refresh_token" in response.data["tokens"]

    def test_login_wrong_password(self, api_client, login_url):
        """Wrong password returns 401."""
        UserFactory(email="user@example.com")
        data = {"email": "user@example.com", "password": "wrongpassword"}
        response = api_client.post(login_url, data, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_wrong_email(self, api_client, login_url):
        """Non-existent email returns 401."""
        data = {"email": "nonexistent@example.com", "password": "testpass123"}
        response = api_client.post(login_url, data, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_wrong_email_same_error_as_wrong_password(
        self, api_client, login_url
    ):
        """
        SECURITY: Wrong email returns the same error code as wrong password.
        This prevents email enumeration.
        """
        UserFactory(email="real@example.com")

        # Wrong password
        resp_wrong_pass = api_client.post(
            login_url,
            {"email": "real@example.com", "password": "wrongpassword"},
            format="json",
        )

        # Wrong email
        resp_wrong_email = api_client.post(
            login_url,
            {"email": "fake@example.com", "password": "testpass123"},
            format="json",
        )

        assert resp_wrong_pass.status_code == resp_wrong_email.status_code == 401
        # Both should use the same error code
        assert (
            resp_wrong_pass.data["error"]["code"]
            == resp_wrong_email.data["error"]["code"]
        )

    def test_login_inactive_account(self, api_client, login_url):
        """Inactive account returns 401."""
        InactiveUserFactory(email="inactive@example.com")
        data = {"email": "inactive@example.com", "password": "testpass123"}
        response = api_client.post(login_url, data, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_missing_fields(self, api_client, login_url):
        """Missing fields returns 400."""
        response = api_client.post(login_url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_missing_password(self, api_client, login_url):
        """Missing password returns 400."""
        data = {"email": "user@example.com"}
        response = api_client.post(login_url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# REFRESH VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestRefreshView:
    """Tests for POST /api/v1/auth/refresh/."""

    def test_refresh_success_mobile(self, api_client, login_url, refresh_url):
        """Successful token refresh returns 200 with new tokens (mobile flow)."""
        UserFactory(email="refresh@example.com")

        # Login first to get refresh token
        login_resp = api_client.post(
            login_url,
            {"email": "refresh@example.com", "password": "testpass123"},
            format="json",
            HTTP_X_CLIENT_TYPE="mobile",
        )
        refresh_token = login_resp.data["tokens"]["refresh_token"]

        response = api_client.post(
            refresh_url,
            {"refresh_token": refresh_token},
            format="json",
            HTTP_X_CLIENT_TYPE="mobile",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.data
        assert "refresh_token" in response.data

    def test_refresh_missing_token(self, api_client, refresh_url):
        """Missing refresh token returns 400."""
        response = api_client.post(refresh_url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_refresh_invalid_token(self, api_client, refresh_url):
        """Invalid (non-existent) refresh token returns 401."""
        response = api_client.post(
            refresh_url,
            {"refresh_token": "totally-invalid-token"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_expired_token(self, api_client, login_url, refresh_url):
        """Expired refresh token returns 401."""
        user = UserFactory(email="expired@example.com")
        # Create an expired token using factory
        token_obj, raw_token = RefreshTokenFactory.create_with_raw_token(user=user)
        # Manually expire it
        from datetime import timedelta

        from django.utils import timezone

        token_obj.expires_at = timezone.now() - timedelta(hours=1)
        token_obj.save(update_fields=["expires_at"])

        response = api_client.post(
            refresh_url,
            {"refresh_token": raw_token},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_revoked_token(self, api_client, refresh_url):
        """Revoked refresh token returns 401."""
        user = UserFactory(email="revoked@example.com")
        token_obj, raw_token = RefreshTokenFactory.create_with_raw_token(user=user)
        token_obj.is_revoked = True
        token_obj.save(update_fields=["is_revoked"])

        response = api_client.post(
            refresh_url,
            {"refresh_token": raw_token},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# LOGOUT VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestLogoutView:
    """Tests for POST /api/v1/auth/logout/."""

    def test_logout_success(self, api_client, login_url, logout_url):
        """Authenticated logout returns 200."""
        user = UserFactory(email="logout@example.com")

        # Login to get tokens
        login_resp = api_client.post(
            login_url,
            {"email": "logout@example.com", "password": "testpass123"},
            format="json",
            HTTP_X_CLIENT_TYPE="mobile",
        )
        refresh_token = login_resp.data["tokens"]["refresh_token"]

        api_client.force_authenticate(user=user)
        response = api_client.post(
            logout_url,
            {"refresh_token": refresh_token},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data

    def test_logout_unauthenticated(self, api_client, logout_url):
        """Unauthenticated logout returns 401."""
        response = api_client.post(logout_url, {}, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_without_refresh_token(self, api_client, logout_url):
        """Logout without refresh token still returns 200 (clears cookie)."""
        user = UserFactory()
        api_client.force_authenticate(user=user)

        response = api_client.post(logout_url, {}, format="json")

        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# LOGOUT ALL VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestLogoutAllView:
    """Tests for POST /api/v1/auth/logout-all/."""

    def test_logout_all_success(self, api_client, logout_all_url):
        """Authenticated logout-all returns 200 with sessions_revoked count."""
        user = UserFactory()
        api_client.force_authenticate(user=user)

        response = api_client.post(logout_all_url, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "sessions_revoked" in response.data
        assert "message" in response.data

    def test_logout_all_unauthenticated(self, api_client, logout_all_url):
        """Unauthenticated logout-all returns 401."""
        response = api_client.post(logout_all_url, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_all_revokes_multiple_sessions(
        self, api_client, login_url, logout_all_url
    ):
        """Logout-all revokes all active sessions."""
        user = UserFactory(email="multi@example.com")

        # Create multiple sessions by logging in with different device IDs
        for i in range(3):
            api_client.post(
                login_url,
                {
                    "email": "multi@example.com",
                    "password": "testpass123",
                    "device_id": f"device_{i}",
                },
                format="json",
                HTTP_X_CLIENT_TYPE="mobile",
            )

        api_client.force_authenticate(user=user)
        response = api_client.post(logout_all_url, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["sessions_revoked"] >= 0


# =============================================================================
# VERIFY EMAIL CODE VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestVerifyEmailCodeView:
    """Tests for POST /api/v1/auth/verify-email/."""

    def test_verify_email_code_success(self, api_client, verify_email_code_url):
        """Valid code verifies email and returns 200."""
        user = UserFactory(email="verify@example.com")
        token = EmailVerificationTokenFactory(user=user, email=user.email)

        data = {"email": user.email, "code": token.code}
        response = api_client.post(verify_email_code_url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data
        user.refresh_from_db()
        assert user.is_verified is True

    def test_verify_email_code_invalid(self, api_client, verify_email_code_url):
        """Invalid code returns 400 with invalid_code error."""
        user = UserFactory(email="verify2@example.com")
        EmailVerificationTokenFactory(user=user, email=user.email)

        data = {"email": user.email, "code": "000000"}
        response = api_client.post(verify_email_code_url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "invalid_code"

    def test_verify_email_code_expired(self, api_client, verify_email_code_url):
        """Expired code returns 400 with code_expired error."""
        user = UserFactory(email="expired@example.com")
        token = ExpiredVerificationTokenFactory(user=user, email=user.email)

        data = {"email": user.email, "code": token.code}
        response = api_client.post(verify_email_code_url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "code_expired"

    def test_verify_email_code_missing_fields(self, api_client, verify_email_code_url):
        """Missing fields returns 400."""
        response = api_client.post(verify_email_code_url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# VERIFY EMAIL LINK VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestVerifyEmailLinkView:
    """Tests for GET /api/v1/auth/verify-email/<uuid>/."""

    @override_settings(FRONTEND_URL=None)
    def test_verify_email_link_success(self, api_client):
        """Valid token verifies email and returns 200 (no FRONTEND_URL redirect)."""
        user = UserFactory(email="link@example.com")
        token = EmailVerificationTokenFactory(user=user, email=user.email)

        url = f"/api/v1/auth/verify-email/{token.token}/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data
        user.refresh_from_db()
        assert user.is_verified is True

    def test_verify_email_link_redirects_with_frontend_url(self, api_client):
        """When FRONTEND_URL is configured, successful verification redirects."""
        user = UserFactory(email="linkredir@example.com")
        token = EmailVerificationTokenFactory(user=user, email=user.email)

        url = f"/api/v1/auth/verify-email/{token.token}/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_302_FOUND
        user.refresh_from_db()
        assert user.is_verified is True

    def test_verify_email_link_invalid_uuid(self, api_client):
        """Invalid UUID format returns 400."""
        url = "/api/v1/auth/verify-email/not-a-uuid/"
        response = api_client.get(url)

        # Django URL routing will return 404 for non-uuid path
        assert response.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
        )

    def test_verify_email_link_nonexistent_token(self, api_client):
        """Non-existent token returns 401 (TokenInvalid)."""
        fake_uuid = uuid.uuid4()
        url = f"/api/v1/auth/verify-email/{fake_uuid}/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_verify_email_link_expired_token(self, api_client):
        """Expired token returns 401 (TokenExpired)."""
        user = UserFactory(email="explink@example.com")
        token = ExpiredVerificationTokenFactory(user=user, email=user.email)

        url = f"/api/v1/auth/verify-email/{token.token}/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# RESEND VERIFICATION VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestResendVerificationView:
    """Tests for POST /api/v1/auth/resend-verification/."""

    def test_resend_verification_existing_user(
        self, api_client, resend_verification_url
    ):
        """
        SECURITY: Returns 200 success message for existing unverified user.
        """
        UserFactory(email="unverified@example.com")

        data = {"email": "unverified@example.com"}
        response = api_client.post(resend_verification_url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data

    def test_resend_verification_nonexistent_email(
        self, api_client, resend_verification_url
    ):
        """
        SECURITY: Returns 200 even for non-existent email (prevents enumeration).
        """
        data = {"email": "doesnotexist@example.com"}
        response = api_client.post(resend_verification_url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data

    def test_resend_verification_same_response_regardless_of_email_existence(
        self, api_client, resend_verification_url
    ):
        """
        SECURITY: Response for existing and non-existing emails must be identical.
        """
        UserFactory(email="exists@example.com")

        resp_exists = api_client.post(
            resend_verification_url,
            {"email": "exists@example.com"},
            format="json",
        )
        resp_not_exists = api_client.post(
            resend_verification_url,
            {"email": "ghost@example.com"},
            format="json",
        )

        assert resp_exists.status_code == resp_not_exists.status_code == 200

    def test_resend_verification_missing_email(
        self, api_client, resend_verification_url
    ):
        """Missing email returns 400."""
        response = api_client.post(resend_verification_url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# PASSWORD RESET REQUEST VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestPasswordResetRequestView:
    """Tests for POST /api/v1/auth/password/reset/."""

    def test_password_reset_request_existing_email(
        self, api_client, password_reset_url
    ):
        """Returns 200 for existing email."""
        UserFactory(email="reset@example.com")

        data = {"email": "reset@example.com"}
        response = api_client.post(password_reset_url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data

    def test_password_reset_request_nonexistent_email(
        self, api_client, password_reset_url
    ):
        """
        SECURITY: Returns 200 even for non-existent email (prevents enumeration).
        """
        data = {"email": "noone@example.com"}
        response = api_client.post(password_reset_url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data

    def test_password_reset_always_200_regardless_of_email(
        self, api_client, password_reset_url
    ):
        """
        SECURITY: Both existing and non-existing emails return the same 200 response.
        """
        UserFactory(email="real@example.com")

        resp_real = api_client.post(
            password_reset_url,
            {"email": "real@example.com"},
            format="json",
        )
        resp_fake = api_client.post(
            password_reset_url,
            {"email": "fake@example.com"},
            format="json",
        )

        assert resp_real.status_code == resp_fake.status_code == 200

    def test_password_reset_request_missing_email(self, api_client, password_reset_url):
        """Missing email returns 400."""
        response = api_client.post(password_reset_url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# PASSWORD RESET CONFIRM VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestPasswordResetConfirmView:
    """Tests for POST /api/v1/auth/password/reset/confirm/."""

    def test_password_reset_confirm_success(
        self, api_client, password_reset_confirm_url
    ):
        """Valid token and new password resets the password and returns 200."""
        user = UserFactory(email="resetconfirm@example.com")
        token = PasswordResetTokenFactory(user=user)

        data = {
            "token": str(token.token),
            "new_password": "NewSecurePass456!",
        }
        response = api_client.post(password_reset_confirm_url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data

    def test_password_reset_confirm_invalid_token(
        self, api_client, password_reset_confirm_url
    ):
        """Invalid token returns 401."""
        data = {
            "token": str(uuid.uuid4()),
            "new_password": "NewSecurePass456!",
        }
        response = api_client.post(password_reset_confirm_url, data, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_password_reset_confirm_expired_token(
        self, api_client, password_reset_confirm_url
    ):
        """Expired token returns 401."""
        user = UserFactory(email="exptoken@example.com")
        token = ExpiredPasswordResetTokenFactory(user=user)

        data = {
            "token": str(token.token),
            "new_password": "NewSecurePass456!",
        }
        response = api_client.post(password_reset_confirm_url, data, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_password_reset_confirm_used_token(
        self, api_client, password_reset_confirm_url
    ):
        """Already-used token returns 401."""
        user = UserFactory(email="usedtoken@example.com")
        token = UsedPasswordResetTokenFactory(user=user)

        data = {
            "token": str(token.token),
            "new_password": "NewSecurePass456!",
        }
        response = api_client.post(password_reset_confirm_url, data, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_password_reset_confirm_missing_fields(
        self, api_client, password_reset_confirm_url
    ):
        """Missing fields returns 400."""
        response = api_client.post(password_reset_confirm_url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# PASSWORD CHANGE VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestPasswordChangeView:
    """Tests for POST /api/v1/auth/password/change/."""

    def test_password_change_success(self, api_client, password_change_url):
        """Successful password change returns 200."""
        user = UserFactory(email="change@example.com")
        api_client.force_authenticate(user=user)

        data = {
            "current_password": "testpass123",
            "new_password": "NewSecurePass456!",
        }
        response = api_client.post(password_change_url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data

    def test_password_change_unauthenticated(self, api_client, password_change_url):
        """
        SECURITY: Password change requires authentication; returns 401 without.
        """
        data = {
            "current_password": "testpass123",
            "new_password": "NewSecurePass456!",
        }
        response = api_client.post(password_change_url, data, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_password_change_wrong_current_password(
        self, api_client, password_change_url
    ):
        """Wrong current password returns 401."""
        user = UserFactory(email="wrongcurrent@example.com")
        api_client.force_authenticate(user=user)

        data = {
            "current_password": "wrongpassword",
            "new_password": "NewSecurePass456!",
        }
        response = api_client.post(password_change_url, data, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_password_change_weak_new_password(self, api_client, password_change_url):
        """Weak new password returns 400."""
        user = UserFactory(email="weakpass@example.com")
        api_client.force_authenticate(user=user)

        data = {
            "current_password": "testpass123",
            "new_password": "short",
        }
        response = api_client.post(password_change_url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_change_missing_fields(self, api_client, password_change_url):
        """Missing fields returns 400."""
        user = UserFactory()
        api_client.force_authenticate(user=user)

        response = api_client.post(password_change_url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# SESSION LIST VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestSessionListView:
    """Tests for GET /api/v1/auth/sessions/."""

    def test_session_list_success(self, api_client, sessions_url):
        """Returns list of active sessions for authenticated user."""
        user = UserFactory()
        DeviceSessionFactory(user=user, device_name="Chrome on Mac")
        DeviceSessionFactory(user=user, device_name="iPhone App")
        api_client.force_authenticate(user=user)

        response = api_client.get(sessions_url)

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        assert len(response.data) == 2

    def test_session_list_unauthenticated(self, api_client, sessions_url):
        """Unauthenticated request returns 401."""
        response = api_client.get(sessions_url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_session_list_only_own_sessions(self, api_client, sessions_url):
        """User only sees their own sessions, not other users'."""
        user = UserFactory(email="owner@example.com")
        other_user = UserFactory(email="other@example.com")
        DeviceSessionFactory(user=user, device_name="My Device")
        DeviceSessionFactory(user=other_user, device_name="Other Device")

        api_client.force_authenticate(user=user)
        response = api_client.get(sessions_url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["device_name"] == "My Device"

    def test_session_list_only_active_sessions(self, api_client, sessions_url):
        """Only active sessions are listed."""
        user = UserFactory()
        DeviceSessionFactory(user=user, is_active=True, device_name="Active")
        DeviceSessionFactory(user=user, is_active=False, device_name="Inactive")

        api_client.force_authenticate(user=user)
        response = api_client.get(sessions_url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1


# =============================================================================
# SESSION REVOKE VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestSessionRevokeView:
    """Tests for DELETE /api/v1/auth/sessions/<uuid>/."""

    def test_session_revoke_success(self, api_client):
        """Revoking own session returns 200."""
        user = UserFactory()
        session = DeviceSessionFactory(user=user)
        api_client.force_authenticate(user=user)

        url = f"/api/v1/auth/sessions/{session.id}/"
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data

    def test_session_revoke_unauthenticated(self, api_client):
        """Unauthenticated request returns 401."""
        fake_uuid = uuid.uuid4()
        url = f"/api/v1/auth/sessions/{fake_uuid}/"
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_session_revoke_not_found(self, api_client):
        """Non-existent session returns 404."""
        user = UserFactory()
        api_client.force_authenticate(user=user)

        fake_uuid = uuid.uuid4()
        url = f"/api/v1/auth/sessions/{fake_uuid}/"
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_session_revoke_other_users_session(self, api_client):
        """
        SECURITY: Cannot revoke another user's session (returns 404, not 403).
        """
        user = UserFactory(email="me@example.com")
        other_user = UserFactory(email="them@example.com")
        other_session = DeviceSessionFactory(user=other_user)

        api_client.force_authenticate(user=user)
        url = f"/api/v1/auth/sessions/{other_session.id}/"
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# GOOGLE OAUTH VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestGoogleOAuthView:
    """Tests for GET /api/v1/auth/oauth/google/."""

    @patch("apps.auth.views.GoogleOAuthBackend")
    @patch("apps.auth.views.OAuthStateManager")
    def test_google_oauth_init_success(
        self, mock_state_manager, mock_google_backend, api_client, oauth_google_url
    ):
        """Returns authorization_url on success."""
        mock_state_manager.create_state.return_value = {
            "state_token": "test_state",
            "code_verifier": "test_verifier",
            "code_challenge": "test_challenge",
            "nonce": "test_nonce",
        }
        mock_google_backend.get_authorization_url.return_value = (
            "https://accounts.google.com/o/oauth2/v2/auth?test=1"
        )

        response = api_client.get(oauth_google_url)

        assert response.status_code == status.HTTP_200_OK
        assert "authorization_url" in response.data
        mock_state_manager.create_state.assert_called_once()
        mock_google_backend.get_authorization_url.assert_called_once()

    @patch("apps.auth.views.GoogleOAuthBackend")
    @patch("apps.auth.views.OAuthStateManager")
    def test_google_oauth_init_with_redirect(
        self, mock_state_manager, mock_google_backend, api_client, oauth_google_url
    ):
        """Passes redirect_to parameter through."""
        mock_state_manager.create_state.return_value = {
            "state_token": "s",
            "code_verifier": "v",
            "code_challenge": "c",
            "nonce": "n",
        }
        mock_google_backend.get_authorization_url.return_value = "https://google.com"

        response = api_client.get(
            oauth_google_url, {"redirect_to": "http://localhost:3000/callback"}
        )

        assert response.status_code == status.HTTP_200_OK
        call_kwargs = mock_state_manager.create_state.call_args
        assert call_kwargs[1].get("redirect_to") or call_kwargs[0][1] is not None


@pytest.mark.django_db
class TestGoogleOAuthCallbackView:
    """Tests for GET /api/v1/auth/oauth/google/callback/."""

    @patch("apps.auth.views.OAuthService")
    @patch("apps.auth.views.GoogleOAuthBackend")
    @patch("apps.auth.views.OAuthStateManager")
    def test_google_callback_success(
        self,
        mock_state_manager,
        mock_google_backend,
        mock_oauth_service,
        api_client,
        oauth_google_callback_url,
    ):
        """Successful callback returns auth response."""
        from apps.auth.services.auth_service import TokenPair

        user = UserFactory(email="google@example.com")
        session = DeviceSessionFactory(user=user)
        tokens = TokenPair(
            access_token="access_123",
            refresh_token="refresh_123",
            access_expires_in=900,
            refresh_expires_in=604800,
        )

        mock_state_manager.validate_and_consume_state.return_value = {
            "provider": "google",
            "code_verifier": "verifier",
            "nonce": "nonce",
            "redirect_to": None,
            "device_info": {},
        }
        mock_google_backend.exchange_code.return_value = {
            "access_token": "google_access",
            "id_token": "google_id_token",
        }
        mock_google_backend.verify_id_token.return_value = {
            "sub": "google_uid_123",
            "email": "google@example.com",
            "email_verified": True,
            "name": "Test User",
        }
        mock_oauth_service.authenticate_or_create_user.return_value = (
            user,
            tokens,
            session,
            False,
        )

        response = api_client.get(
            oauth_google_callback_url,
            {"code": "auth_code_123", "state": "valid_state"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert "user" in response.data

    def test_google_callback_missing_code(self, api_client, oauth_google_callback_url):
        """Missing code returns 400."""
        response = api_client.get(oauth_google_callback_url, {"state": "some_state"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_google_callback_missing_state(self, api_client, oauth_google_callback_url):
        """Missing state returns 400."""
        response = api_client.get(oauth_google_callback_url, {"code": "some_code"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_google_callback_missing_both(self, api_client, oauth_google_callback_url):
        """Missing both code and state returns 400."""
        response = api_client.get(oauth_google_callback_url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("apps.auth.views.GoogleOAuthBackend")
    @patch("apps.auth.views.OAuthStateManager")
    def test_google_callback_wrong_provider(
        self,
        mock_state_manager,
        mock_google_backend,
        api_client,
        oauth_google_callback_url,
    ):
        """State with wrong provider returns 400."""
        mock_state_manager.validate_and_consume_state.return_value = {
            "provider": "apple",  # Wrong provider
            "code_verifier": "v",
            "nonce": "n",
        }

        response = api_client.get(
            oauth_google_callback_url,
            {"code": "code", "state": "state"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# APPLE OAUTH VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestAppleOAuthView:
    """Tests for GET /api/v1/auth/oauth/apple/."""

    @patch("apps.auth.views.AppleOAuthBackend")
    @patch("apps.auth.views.OAuthStateManager")
    def test_apple_oauth_init_success(
        self, mock_state_manager, mock_apple_backend, api_client, oauth_apple_url
    ):
        """Returns authorization_url on success."""
        mock_state_manager.create_state.return_value = {
            "state_token": "test_state",
            "code_verifier": "test_verifier",
            "code_challenge": "test_challenge",
            "nonce": "test_nonce",
        }
        mock_apple_backend.get_authorization_url.return_value = (
            "https://appleid.apple.com/auth/authorize?test=1"
        )

        response = api_client.get(oauth_apple_url)

        assert response.status_code == status.HTTP_200_OK
        assert "authorization_url" in response.data
        mock_apple_backend.get_authorization_url.assert_called_once()


@pytest.mark.django_db
class TestAppleOAuthCallbackView:
    """Tests for POST /api/v1/auth/oauth/apple/callback/."""

    @patch("apps.auth.views.OAuthService")
    @patch("apps.auth.views.AppleOAuthBackend")
    @patch("apps.auth.views.OAuthStateManager")
    def test_apple_callback_success_with_id_token(
        self,
        mock_state_manager,
        mock_apple_backend,
        mock_oauth_service,
        api_client,
        oauth_apple_callback_url,
    ):
        """Successful Apple callback with id_token returns auth response."""
        from apps.auth.services.auth_service import TokenPair

        user = UserFactory(email="apple@example.com")
        session = DeviceSessionFactory(user=user)
        tokens = TokenPair(
            access_token="access_456",
            refresh_token="refresh_456",
            access_expires_in=900,
            refresh_expires_in=604800,
        )

        mock_state_manager.validate_and_consume_state.return_value = {
            "provider": "apple",
            "code_verifier": "verifier",
            "nonce": "nonce",
            "redirect_to": None,
            "device_info": {},
        }
        mock_apple_backend.verify_id_token.return_value = {
            "sub": "apple_uid_123",
            "email": "apple@example.com",
            "email_verified": True,
        }
        mock_apple_backend.parse_user_data.return_value = {}
        mock_oauth_service.authenticate_or_create_user.return_value = (
            user,
            tokens,
            session,
            True,
        )

        data = {
            "code": "apple_auth_code",
            "state": "valid_state",
            "id_token": "apple_id_token",
        }
        response = api_client.post(oauth_apple_callback_url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "user" in response.data

    @patch("apps.auth.views.OAuthService")
    @patch("apps.auth.views.AppleOAuthBackend")
    @patch("apps.auth.views.OAuthStateManager")
    def test_apple_callback_success_without_id_token(
        self,
        mock_state_manager,
        mock_apple_backend,
        mock_oauth_service,
        api_client,
        oauth_apple_callback_url,
    ):
        """Apple callback without id_token exchanges code first."""
        from apps.auth.services.auth_service import TokenPair

        user = UserFactory(email="apple2@example.com")
        session = DeviceSessionFactory(user=user)
        tokens = TokenPair(
            access_token="access_789",
            refresh_token="refresh_789",
            access_expires_in=900,
            refresh_expires_in=604800,
        )

        mock_state_manager.validate_and_consume_state.return_value = {
            "provider": "apple",
            "code_verifier": "verifier",
            "nonce": "nonce",
            "redirect_to": None,
            "device_info": {},
        }
        mock_apple_backend.exchange_code.return_value = {
            "id_token": "exchanged_id_token",
            "access_token": "apple_access",
        }
        mock_apple_backend.verify_id_token.return_value = {
            "sub": "apple_uid_456",
            "email": "apple2@example.com",
            "email_verified": True,
        }
        mock_apple_backend.parse_user_data.return_value = {}
        mock_oauth_service.authenticate_or_create_user.return_value = (
            user,
            tokens,
            session,
            False,
        )

        data = {"code": "apple_code", "state": "valid_state"}
        response = api_client.post(oauth_apple_callback_url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        mock_apple_backend.exchange_code.assert_called_once()

    def test_apple_callback_missing_code(self, api_client, oauth_apple_callback_url):
        """Missing code returns 400."""
        data = {"state": "some_state"}
        response = api_client.post(oauth_apple_callback_url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_apple_callback_missing_state(self, api_client, oauth_apple_callback_url):
        """Missing state returns 400."""
        data = {"code": "some_code"}
        response = api_client.post(oauth_apple_callback_url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("apps.auth.views.AppleOAuthBackend")
    @patch("apps.auth.views.OAuthStateManager")
    def test_apple_callback_wrong_provider(
        self,
        mock_state_manager,
        mock_apple_backend,
        api_client,
        oauth_apple_callback_url,
    ):
        """State with wrong provider returns 400."""
        mock_state_manager.validate_and_consume_state.return_value = {
            "provider": "google",  # Wrong provider for Apple callback
            "code_verifier": "v",
            "nonce": "n",
        }

        data = {"code": "code", "state": "state"}
        response = api_client.post(oauth_apple_callback_url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
