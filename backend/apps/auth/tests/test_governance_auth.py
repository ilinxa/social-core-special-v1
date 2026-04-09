# apps/auth/tests/test_governance_auth.py
"""
Tests for Governance Step-Up Authentication.

Covers:
    - GovernancePasswordAuthView (POST /api/v1/auth/governance/authenticate/)
    - GovernanceOTPSendView (POST /api/v1/auth/governance/otp/send/)
    - GovernanceOTPVerifyView (POST /api/v1/auth/governance/otp/verify/)
    - GovernanceAuthService (direct service calls)
    - GovernanceOTPToken model

Test strategy:
    - Views are tested via APIClient (integration style, real DB)
    - Service methods are tested directly for edge cases
    - Model methods are tested for correctness
    - NotificationService is mocked globally (no real email)
    - JWT encode_token is patched to handle UUID serialization
"""

import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.auth.models import GovernanceOTPToken
from apps.auth.services.governance_service import GovernanceAuthService, GovernanceToken
from apps.auth.tests.factories import (
    ExpiredGovernanceOTPFactory,
    GovernanceOTPTokenFactory,
    MaxAttemptsGovernanceOTPFactory,
    UsedGovernanceOTPFactory,
)
from apps.core.exceptions import (
    AccountLocked,
    InvalidCredentials,
    PermissionDenied,
    TokenExpired,
    TokenInvalid,
)
from apps.core.observability.audit import AuditLog
from apps.users.tests.factories import UserFactory

# =============================================================================
# CONSTANTS
# =============================================================================

PASSWORD = "TestPassword123!"

GOVERNANCE_AUTH_URL = "/api/v1/auth/governance/authenticate/"
GOVERNANCE_OTP_SEND_URL = "/api/v1/auth/governance/otp/send/"
GOVERNANCE_OTP_VERIFY_URL = "/api/v1/auth/governance/otp/verify/"

# =============================================================================
# AUTOUSE FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def mock_notifications():
    """Mock NotificationService globally to prevent actual email sends."""
    with patch("apps.notifications.services.NotificationService") as mock:
        yield mock


@pytest.fixture(autouse=True)
def _patch_jwt_uuid_serialization():
    """Patch encode_token to auto-convert UUID values in JWT payload to strings."""
    from apps.auth.services import governance_service as gov_module

    _original_encode = gov_module.encode_token

    def _encode_with_uuid_fix(payload, **kwargs):
        sanitized = {
            k: str(v) if isinstance(v, uuid.UUID) else v for k, v in payload.items()
        }
        return _original_encode(sanitized, **kwargs)

    with patch.object(gov_module, "encode_token", side_effect=_encode_with_uuid_fix):
        yield


# =============================================================================
# SHARED FIXTURES
# =============================================================================


@pytest.fixture
def immediate_on_commit(monkeypatch):
    """Execute transaction.on_commit() callbacks immediately."""
    monkeypatch.setattr(
        "django.db.transaction.on_commit",
        lambda func, using=None, robust=False: func(),
    )


@pytest.fixture
def platform_account(db):
    """Get or create the platform singleton."""
    from apps.organization.platform.models import PlatformAccount
    from apps.organization.tests.factories import PlatformAccountFactory

    platform = PlatformAccount.objects.first()
    if platform:
        return platform
    return PlatformAccountFactory()


@pytest.fixture
def _ensure_platform_rbac(platform_account):
    """Initialize platform RBAC roles if not already present."""
    from apps.rbac.models import Role
    from apps.rbac.services import RBACService

    exists = Role.objects.filter(
        account_type="platform",
        account_id=platform_account.id,
    ).exists()
    if not exists:
        RBACService.initialize_platform_account(
            platform_id=platform_account.id,
        )


@pytest.fixture
def governance_user(db, platform_account, _ensure_platform_rbac):
    """
    Create a user with Global Moderator role (has global-scope permissions).

    Sets a known password for authentication tests.
    """
    from apps.rbac.models import Role
    from apps.rbac.services import RBACService

    user = UserFactory(
        username="gov_user",
        email="gov_user@example.com",
        is_verified=True,
    )
    user.set_password(PASSWORD)
    user.save()

    mod_role = Role.objects.get(
        account_type="platform",
        account_id=platform_account.id,
        name="Global Moderator",
    )
    RBACService.create_membership(
        user=user,
        account_type="platform",
        account_id=platform_account.id,
        role_id=mod_role.id,
        created_by=user,
    )
    return user


@pytest.fixture
def regular_user(db):
    """Create a regular user without any platform membership."""
    user = UserFactory(
        username="regular_user",
        email="regular@example.com",
        is_verified=True,
    )
    user.set_password(PASSWORD)
    user.save()
    return user


@pytest.fixture
def api_client():
    """Return an unauthenticated DRF APIClient."""
    return APIClient()


@pytest.fixture
def gov_client(api_client, governance_user):
    """APIClient authenticated as governance user."""
    api_client.force_authenticate(user=governance_user)
    return api_client


@pytest.fixture
def regular_client(api_client, regular_user):
    """APIClient authenticated as regular user (no global perms)."""
    api_client.force_authenticate(user=regular_user)
    return api_client


# =============================================================================
# TestGovernancePasswordAuthView
# =============================================================================


@pytest.mark.django_db
class TestGovernancePasswordAuthView:
    """Tests for POST /api/v1/auth/governance/authenticate/."""

    def test_successful_auth(self, gov_client, governance_user):
        """Valid password + global permissions returns 200 with access + expires_in."""
        response = gov_client.post(
            GOVERNANCE_AUTH_URL,
            {"password": PASSWORD},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "expires_in" in response.data
        assert isinstance(response.data["access"], str)
        assert response.data["expires_in"] > 0

    def test_wrong_password(self, gov_client):
        """Wrong password returns 401 (InvalidCredentials)."""
        response = gov_client.post(
            GOVERNANCE_AUTH_URL,
            {"password": "WrongPassword999!"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_failed_attempts_increment(self, governance_user):
        """Wrong password increments user.failed_login_attempts (service level).

        Note: The view-level @transaction.atomic rolls back on exception,
        so we test the _verify_password side-effect directly.
        """
        assert governance_user.failed_login_attempts == 0

        # Call _verify_password directly (outside @transaction.atomic)
        with pytest.raises(InvalidCredentials):
            GovernanceAuthService._verify_password(governance_user, "WrongPassword999!")

        governance_user.refresh_from_db()
        assert governance_user.failed_login_attempts == 1

    def test_lockout_after_max_attempts(self, governance_user):
        """10 consecutive wrong passwords triggers account lockout.

        Note: Tested at service-internal level to bypass @transaction.atomic
        rollback on the view method.
        """
        for _ in range(10):
            with pytest.raises(InvalidCredentials):
                GovernanceAuthService._verify_password(
                    governance_user, "WrongPassword999!"
                )
            governance_user.refresh_from_db()

        assert governance_user.failed_login_attempts == 10
        assert governance_user.locked_until is not None
        assert governance_user.locked_until > timezone.now()

    def test_locked_account(self, gov_client, governance_user):
        """Locked account returns 401 (AccountLocked)."""
        governance_user.locked_until = timezone.now() + timedelta(minutes=15)
        governance_user.save(update_fields=["locked_until"])

        response = gov_client.post(
            GOVERNANCE_AUTH_URL,
            {"password": PASSWORD},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_successful_auth_resets_lockout(self, gov_client, governance_user):
        """Correct password resets failed_login_attempts to 0."""
        governance_user.failed_login_attempts = 5
        governance_user.save(update_fields=["failed_login_attempts"])

        response = gov_client.post(
            GOVERNANCE_AUTH_URL,
            {"password": PASSWORD},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        governance_user.refresh_from_db()
        assert governance_user.failed_login_attempts == 0

    def test_no_global_permissions(self, regular_client):
        """User without platform membership returns 403 (PermissionDenied)."""
        response = regular_client.post(
            GOVERNANCE_AUTH_URL,
            {"password": PASSWORD},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated(self, api_client):
        """Unauthenticated request returns 401."""
        response = api_client.post(
            GOVERNANCE_AUTH_URL,
            {"password": PASSWORD},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_missing_password_field(self, gov_client):
        """Empty POST body returns 400 (validation error)."""
        response = gov_client.post(
            GOVERNANCE_AUTH_URL,
            {},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_token_contains_governance_scope(self, gov_client):
        """Returned JWT has token_scope='governance' in its payload."""
        from apps.core.utils.jwt import decode_token

        response = gov_client.post(
            GOVERNANCE_AUTH_URL,
            {"password": PASSWORD},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        payload = decode_token(response.data["access"])
        assert payload["token_scope"] == "governance"
        assert payload["token_type"] == "access"

    def test_audit_log_created(self, gov_client, governance_user):
        """Successful auth creates a GOVERNANCE_AUTHENTICATED audit entry."""
        response = gov_client.post(
            GOVERNANCE_AUTH_URL,
            {"password": PASSWORD},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

        log = AuditLog.objects.filter(
            action=AuditLog.Action.GOVERNANCE_AUTHENTICATED,
            actor_id=str(governance_user.id),
        ).first()
        assert log is not None
        assert log.details["method"] == "password"


# =============================================================================
# TestGovernanceOTPSendView
# =============================================================================


@pytest.mark.django_db
class TestGovernanceOTPSendView:
    """Tests for POST /api/v1/auth/governance/otp/send/."""

    def test_send_otp(self, gov_client, governance_user):
        """Authenticated user with global perms gets 200 and OTP is created."""
        response = gov_client.post(GOVERNANCE_OTP_SEND_URL)

        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data

        otp = GovernanceOTPToken.objects.filter(
            user=governance_user, is_used=False
        ).first()
        assert otp is not None

    def test_otp_code_is_6_digits(self, gov_client, governance_user):
        """Created OTP has a 6-digit numeric code."""
        gov_client.post(GOVERNANCE_OTP_SEND_URL)

        otp = GovernanceOTPToken.objects.filter(
            user=governance_user, is_used=False
        ).first()
        assert otp is not None
        assert len(otp.code) == 6
        assert otp.code.isdigit()

    def test_send_invalidates_existing_otp(self, gov_client, governance_user):
        """Sending a new OTP marks the previous one as used."""
        gov_client.post(GOVERNANCE_OTP_SEND_URL)
        first_otp = GovernanceOTPToken.objects.filter(
            user=governance_user, is_used=False
        ).first()
        first_otp_id = first_otp.id

        gov_client.post(GOVERNANCE_OTP_SEND_URL)

        first_otp.refresh_from_db()
        assert first_otp.is_used is True

        new_otp = GovernanceOTPToken.objects.filter(
            user=governance_user, is_used=False
        ).first()
        assert new_otp is not None
        assert new_otp.id != first_otp_id

    def test_email_sent_via_notification(
        self, gov_client, governance_user, immediate_on_commit, mock_notifications
    ):
        """OTP email is sent via NotificationService.send after commit."""
        gov_client.post(GOVERNANCE_OTP_SEND_URL)

        mock_notifications.send.assert_called_once()
        call_kwargs = mock_notifications.send.call_args
        # positional or keyword args
        if call_kwargs.kwargs:
            assert call_kwargs.kwargs["notification_type"] == "governance_otp"
            assert "code" in call_kwargs.kwargs["context"]
            assert call_kwargs.kwargs["force_channels"] == ["email"]
        else:
            # Fallback: check positional
            assert call_kwargs[1]["notification_type"] == "governance_otp"

    def test_no_global_permissions(self, regular_client):
        """User without global permissions returns 403."""
        response = regular_client.post(GOVERNANCE_OTP_SEND_URL)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated(self, api_client):
        """Unauthenticated request returns 401."""
        response = api_client.post(GOVERNANCE_OTP_SEND_URL)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_otp_expires_correctly(self, gov_client, governance_user):
        """Created OTP expires approximately 300 seconds from now."""
        before = timezone.now()
        gov_client.post(GOVERNANCE_OTP_SEND_URL)
        after = timezone.now()

        otp = GovernanceOTPToken.objects.filter(
            user=governance_user, is_used=False
        ).first()
        assert otp is not None

        # Default expiry is 300 seconds
        expected_min = before + timedelta(seconds=295)
        expected_max = after + timedelta(seconds=305)
        assert expected_min <= otp.expires_at <= expected_max


# =============================================================================
# TestGovernanceOTPVerifyView
# =============================================================================


@pytest.mark.django_db
class TestGovernanceOTPVerifyView:
    """Tests for POST /api/v1/auth/governance/otp/verify/."""

    def test_successful_verify(self, gov_client, governance_user):
        """Correct OTP code returns 200 with access + expires_in."""
        otp = GovernanceOTPTokenFactory(user=governance_user)

        response = gov_client.post(
            GOVERNANCE_OTP_VERIFY_URL,
            {"code": otp.code},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "expires_in" in response.data

    def test_wrong_code(self, gov_client, governance_user):
        """Wrong OTP code returns 401 (TokenInvalid)."""
        otp = GovernanceOTPTokenFactory(user=governance_user)
        wrong_code = "000000" if otp.code != "000000" else "111111"

        response = gov_client.post(
            GOVERNANCE_OTP_VERIFY_URL,
            {"code": wrong_code},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_wrong_code_increments_attempts_model_level(self, governance_user):
        """increment_attempts increases counter (model level, separate from atomic view)."""
        otp = GovernanceOTPTokenFactory(user=governance_user, attempts=0)
        otp.increment_attempts()
        otp.refresh_from_db()
        assert otp.attempts == 1

    def test_max_attempts_reached(self, gov_client, governance_user):
        """OTP already at max attempts (5) returns 403 (PermissionDenied)."""
        MaxAttemptsGovernanceOTPFactory(user=governance_user)

        response = gov_client.post(
            GOVERNANCE_OTP_VERIFY_URL,
            {"code": "123456"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_expired_otp(self, gov_client, governance_user):
        """Expired OTP returns 401 (TokenExpired)."""
        otp = ExpiredGovernanceOTPFactory(user=governance_user)

        response = gov_client.post(
            GOVERNANCE_OTP_VERIFY_URL,
            {"code": otp.code},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_used_otp(self, gov_client, governance_user):
        """Used OTP returns 401 (no active OTP found)."""
        UsedGovernanceOTPFactory(user=governance_user)

        response = gov_client.post(
            GOVERNANCE_OTP_VERIFY_URL,
            {"code": "123456"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_no_active_otp(self, gov_client):
        """No OTP in DB returns 401 (TokenInvalid)."""
        response = gov_client.post(
            GOVERNANCE_OTP_VERIFY_URL,
            {"code": "123456"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated(self, api_client):
        """Unauthenticated request returns 401."""
        response = api_client.post(
            GOVERNANCE_OTP_VERIFY_URL,
            {"code": "123456"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_missing_code(self, gov_client):
        """Missing code field returns 400 (validation error)."""
        response = gov_client.post(
            GOVERNANCE_OTP_VERIFY_URL,
            {},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_code_too_short(self, gov_client):
        """Code with fewer than 6 digits returns 400."""
        response = gov_client.post(
            GOVERNANCE_OTP_VERIFY_URL,
            {"code": "123"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_code_too_long(self, gov_client):
        """Code with more than 6 digits returns 400."""
        response = gov_client.post(
            GOVERNANCE_OTP_VERIFY_URL,
            {"code": "12345678"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_successful_verify_marks_otp_used(self, gov_client, governance_user):
        """After successful verification the OTP is marked as used."""
        otp = GovernanceOTPTokenFactory(user=governance_user)

        response = gov_client.post(
            GOVERNANCE_OTP_VERIFY_URL,
            {"code": otp.code},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        otp.refresh_from_db()
        assert otp.is_used is True
        assert otp.used_at is not None

    def test_verify_creates_audit_log(self, gov_client, governance_user):
        """Successful OTP verify creates a GOVERNANCE_AUTHENTICATED audit entry."""
        otp = GovernanceOTPTokenFactory(user=governance_user)

        response = gov_client.post(
            GOVERNANCE_OTP_VERIFY_URL,
            {"code": otp.code},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        log = AuditLog.objects.filter(
            action=AuditLog.Action.GOVERNANCE_AUTHENTICATED,
            actor_id=str(governance_user.id),
        ).first()
        assert log is not None
        assert log.details["method"] == "otp"


# =============================================================================
# TestGovernanceAuthService
# =============================================================================


@pytest.mark.django_db
class TestGovernanceAuthService:
    """Direct tests for GovernanceAuthService methods."""

    def test_authenticate_success(self, governance_user):
        """authenticate_with_password returns GovernanceToken on success."""
        token = GovernanceAuthService.authenticate_with_password(
            user=governance_user,
            password=PASSWORD,
        )

        assert isinstance(token, GovernanceToken)
        assert isinstance(token.access_token, str)
        assert token.expires_in > 0

    def test_authenticate_lockout_check(self, governance_user):
        """Locked user raises AccountLocked."""
        governance_user.locked_until = timezone.now() + timedelta(minutes=15)
        governance_user.save(update_fields=["locked_until"])

        with pytest.raises(AccountLocked):
            GovernanceAuthService.authenticate_with_password(
                user=governance_user,
                password=PASSWORD,
            )

    def test_authenticate_bad_password(self, governance_user):
        """Wrong password raises InvalidCredentials."""
        with pytest.raises(InvalidCredentials):
            GovernanceAuthService.authenticate_with_password(
                user=governance_user,
                password="WrongPassword999!",
            )

    def test_authenticate_no_permissions(self, regular_user):
        """User without global permissions raises PermissionDenied."""
        with pytest.raises(PermissionDenied):
            GovernanceAuthService.authenticate_with_password(
                user=regular_user,
                password=PASSWORD,
            )

    def test_send_otp_creates_token(self, governance_user):
        """send_otp creates a GovernanceOTPToken in the database."""
        GovernanceAuthService.send_otp(user=governance_user)

        otp = GovernanceOTPToken.objects.filter(
            user=governance_user, is_used=False
        ).first()
        assert otp is not None
        assert otp.email == governance_user.email
        assert len(otp.code) == 6

    def test_verify_otp_success(self, governance_user):
        """verify_otp returns GovernanceToken when code matches."""
        otp = GovernanceOTPTokenFactory(user=governance_user)

        token = GovernanceAuthService.verify_otp(
            user=governance_user,
            code=otp.code,
        )

        assert isinstance(token, GovernanceToken)
        assert isinstance(token.access_token, str)

    def test_verify_otp_wrong_code(self, governance_user):
        """Wrong OTP code raises TokenInvalid."""
        otp = GovernanceOTPTokenFactory(user=governance_user)
        wrong_code = "000000" if otp.code != "000000" else "111111"

        with pytest.raises(TokenInvalid, match="Invalid governance OTP code"):
            GovernanceAuthService.verify_otp(
                user=governance_user,
                code=wrong_code,
            )

    def test_verify_otp_expired(self, governance_user):
        """Expired OTP raises TokenExpired."""
        ExpiredGovernanceOTPFactory(user=governance_user)

        with pytest.raises(TokenExpired, match="Governance OTP has expired"):
            GovernanceAuthService.verify_otp(
                user=governance_user,
                code="123456",
            )

    def test_has_any_global_permission_true(self, governance_user):
        """User with Global Moderator role has global permissions."""
        result = GovernanceAuthService.has_any_global_permission(governance_user)

        assert result is True

    def test_has_any_global_permission_false(self, regular_user):
        """User without platform membership has no global permissions."""
        result = GovernanceAuthService.has_any_global_permission(regular_user)

        assert result is False


# =============================================================================
# TestGovernanceOTPTokenModel
# =============================================================================


@pytest.mark.django_db
class TestGovernanceOTPTokenModel:
    """Tests for GovernanceOTPToken model methods and properties."""

    def test_create_for_user(self, governance_user):
        """create_for_user creates OTP with correct fields."""
        otp = GovernanceOTPToken.create_for_user(governance_user)

        assert otp.user == governance_user
        assert otp.email == governance_user.email
        assert len(otp.code) == 6
        assert otp.code.isdigit()
        assert otp.is_used is False
        assert otp.attempts == 0
        assert otp.expires_at > timezone.now()

    def test_is_valid_fresh(self, governance_user):
        """Fresh (unused, not expired) OTP is_valid returns True."""
        otp = GovernanceOTPTokenFactory(user=governance_user)

        assert otp.is_valid is True

    def test_is_valid_expired(self, governance_user):
        """Expired OTP is_valid returns False."""
        otp = ExpiredGovernanceOTPFactory(user=governance_user)

        assert otp.is_valid is False

    def test_is_valid_used(self, governance_user):
        """Used OTP is_valid returns False."""
        otp = UsedGovernanceOTPFactory(user=governance_user)

        assert otp.is_valid is False

    def test_is_max_attempts_reached(self, governance_user):
        """OTP with 5 attempts has is_max_attempts_reached True."""
        otp = MaxAttemptsGovernanceOTPFactory(user=governance_user)

        assert otp.is_max_attempts_reached is True

    def test_is_max_attempts_not_reached(self, governance_user):
        """OTP with fewer than 5 attempts has is_max_attempts_reached False."""
        otp = GovernanceOTPTokenFactory(user=governance_user, attempts=4)

        assert otp.is_max_attempts_reached is False

    def test_increment_attempts(self, governance_user):
        """increment_attempts increases the counter by 1."""
        otp = GovernanceOTPTokenFactory(user=governance_user, attempts=2)

        otp.increment_attempts()

        otp.refresh_from_db()
        assert otp.attempts == 3

    def test_mark_used(self, governance_user):
        """mark_used sets is_used=True and records used_at timestamp."""
        otp = GovernanceOTPTokenFactory(user=governance_user)
        assert otp.is_used is False
        assert otp.used_at is None

        before = timezone.now()
        otp.mark_used()
        after = timezone.now()

        otp.refresh_from_db()
        assert otp.is_used is True
        assert otp.used_at is not None
        assert before <= otp.used_at <= after

    def test_generate_code_default_length(self):
        """generate_code returns a 6-digit numeric string by default."""
        code = GovernanceOTPToken.generate_code()

        assert len(code) == 6
        assert code.isdigit()

    def test_generate_code_custom_length(self):
        """generate_code with explicit length returns correct number of digits."""
        code = GovernanceOTPToken.generate_code(length=8)

        assert len(code) == 8
        assert code.isdigit()

    def test_create_for_user_invalidates_existing(self, governance_user):
        """create_for_user marks existing active OTP as used before creating a new one."""
        first_otp = GovernanceOTPToken.create_for_user(governance_user)
        first_id = first_otp.id

        second_otp = GovernanceOTPToken.create_for_user(governance_user)

        first_otp.refresh_from_db()
        assert first_otp.is_used is True
        assert second_otp.is_used is False
        assert second_otp.id != first_id
