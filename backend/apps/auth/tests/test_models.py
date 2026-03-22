# apps/auth/tests/test_models.py
"""
Tests for Auth app models.

Covers:
    - RefreshToken: creation, validity, hashing, token creation, revocation
    - DeviceSession: creation, device types, constraints, relationships
    - EmailVerificationToken: creation, validity, code generation, lifecycle
    - PasswordResetToken: creation, validity, lifecycle, constraints
    - OAuthConnection: creation, providers, constraints
"""

import hashlib
import uuid
from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.auth.models import (
    DeviceSession,
    EmailVerificationToken,
    OAuthConnection,
    PasswordResetToken,
    RefreshToken,
)
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
# REFRESH TOKEN TESTS
# =============================================================================


@pytest.mark.django_db
class TestRefreshToken:
    """Tests for the RefreshToken model."""

    def test_creation_with_factory(self):
        """RefreshToken can be created via factory with correct defaults."""
        token = RefreshTokenFactory()
        assert token.pk is not None
        assert token.user is not None
        assert len(token.token_hash) == 64
        assert token.is_revoked is False
        assert token.revoked_at is None
        assert token.revoked_reason == ""
        assert token.replaced_by is None
        assert token.device_info == {}

    def test_str_representation_active(self):
        """String representation shows 'active' for non-revoked tokens."""
        token = RefreshTokenFactory()
        assert "active" in str(token)
        assert "RefreshToken(" in str(token)

    def test_str_representation_revoked(self):
        """String representation shows 'revoked' for revoked tokens."""
        token = RevokedRefreshTokenFactory()
        assert "revoked" in str(token)

    def test_is_valid_true_for_fresh_token(self):
        """is_valid returns True for a non-revoked, non-expired, non-replaced token."""
        token = RefreshTokenFactory()
        assert token.is_valid is True

    def test_is_valid_false_when_expired(self):
        """is_valid returns False when the token has expired."""
        token = ExpiredRefreshTokenFactory()
        assert token.is_valid is False

    def test_is_valid_false_when_expired_by_one_second(self):
        """is_valid returns False when the token expired just one second ago."""
        token = RefreshTokenFactory(expires_at=timezone.now() - timedelta(seconds=1))
        assert token.is_valid is False

    def test_is_valid_false_when_revoked(self):
        """is_valid returns False when the token is revoked."""
        token = RevokedRefreshTokenFactory()
        assert token.is_valid is False

    def test_is_valid_false_when_replaced(self):
        """is_valid returns False when the token has been replaced by another."""
        replacement = RefreshTokenFactory()
        original = RefreshTokenFactory(replaced_by=replacement)
        assert original.is_valid is False

    def test_hash_token_returns_sha256(self):
        """hash_token returns the correct SHA256 hex digest of the input."""
        raw = "test-token-value"
        expected = hashlib.sha256(raw.encode()).hexdigest()
        assert RefreshToken.hash_token(raw) == expected

    def test_hash_token_deterministic(self):
        """hash_token produces the same output for the same input."""
        raw = "deterministic-test"
        assert RefreshToken.hash_token(raw) == RefreshToken.hash_token(raw)

    def test_hash_token_different_inputs_different_hashes(self):
        """hash_token produces different outputs for different inputs."""
        assert RefreshToken.hash_token("a") != RefreshToken.hash_token("b")

    def test_create_token_returns_tuple(self):
        """create_token returns a (RefreshToken, str) tuple."""
        user = UserFactory()
        result = RefreshToken.create_token(user)
        assert isinstance(result, tuple)
        assert len(result) == 2
        instance, raw_token = result
        assert isinstance(instance, RefreshToken)
        assert isinstance(raw_token, str)

    def test_create_token_hash_matches(self):
        """The stored token_hash matches the hash of the returned raw token."""
        user = UserFactory()
        instance, raw_token = RefreshToken.create_token(user)
        assert instance.token_hash == RefreshToken.hash_token(raw_token)

    def test_create_token_expiry_is_7_days(self):
        """create_token sets expiry to ~7 days from now by default."""
        user = UserFactory()
        before = timezone.now()
        instance, _ = RefreshToken.create_token(user)
        after = timezone.now()
        expected_min = before + timedelta(seconds=604800)
        expected_max = after + timedelta(seconds=604800)
        assert expected_min <= instance.expires_at <= expected_max

    def test_create_token_stores_device_info(self):
        """create_token stores device_id, device_info, and ip_address."""
        user = UserFactory()
        device_info = {"platform": "iOS", "version": "17.0"}
        instance, _ = RefreshToken.create_token(
            user,
            device_id="iphone-abc",
            device_info=device_info,
            ip_address="192.168.1.1",
        )
        assert instance.device_id == "iphone-abc"
        assert instance.device_info == device_info
        assert instance.ip_address == "192.168.1.1"

    def test_create_token_default_device_info(self):
        """create_token uses empty defaults for device_id, device_info, ip_address."""
        user = UserFactory()
        instance, _ = RefreshToken.create_token(user)
        assert instance.device_id == ""
        assert instance.device_info == {}
        assert instance.ip_address is None

    def test_revoke_sets_fields(self):
        """revoke() sets is_revoked, revoked_at, and revoked_reason."""
        token = RefreshTokenFactory()
        before = timezone.now()
        token.revoke(reason="password_change")
        token.refresh_from_db()
        assert token.is_revoked is True
        assert token.revoked_at is not None
        assert token.revoked_at >= before
        assert token.revoked_reason == "password_change"

    def test_revoke_default_reason_is_logout(self):
        """revoke() defaults to 'logout' as the reason."""
        token = RefreshTokenFactory()
        token.revoke()
        token.refresh_from_db()
        assert token.revoked_reason == "logout"

    def test_default_ordering(self):
        """Tokens are ordered by -created_at by default."""
        assert RefreshToken._meta.ordering == ["-created_at"]

    def test_meta_db_table(self):
        """RefreshToken uses the correct database table name."""
        assert RefreshToken._meta.db_table == "auth_refresh_tokens"

    def test_jti_is_unique(self):
        """Two tokens cannot share the same jti."""
        token = RefreshTokenFactory()
        with pytest.raises(IntegrityError):
            RefreshTokenFactory(jti=token.jti)


# =============================================================================
# DEVICE SESSION TESTS
# =============================================================================


@pytest.mark.django_db
class TestDeviceSession:
    """Tests for the DeviceSession model."""

    def test_creation_with_factory(self):
        """DeviceSession can be created via factory with correct defaults."""
        session = DeviceSessionFactory()
        assert session.pk is not None
        assert session.user is not None
        assert session.is_active is True
        assert session.device_type == DeviceSession.DeviceType.WEB

    def test_device_type_choices(self):
        """All expected DeviceType choices exist."""
        choices = {c.value for c in DeviceSession.DeviceType}
        assert choices == {"web", "ios", "android", "desktop", "unknown"}

    def test_str_with_device_name(self):
        """String representation uses device_name when available."""
        session = DeviceSessionFactory(device_name="My iPhone")
        assert str(session) == f"My iPhone - {session.user_id}"

    def test_str_without_device_name(self):
        """String representation falls back to device_type when name is empty."""
        session = DeviceSessionFactory(device_name="", device_type="ios")
        assert str(session) == f"ios - {session.user_id}"

    def test_default_is_active_true(self):
        """is_active defaults to True."""
        session = DeviceSessionFactory()
        assert session.is_active is True

    def test_unique_together_user_device_id(self):
        """Cannot create two sessions with the same user and device_id."""
        user = UserFactory()
        DeviceSessionFactory(user=user, device_id="same-device")
        with pytest.raises(IntegrityError):
            DeviceSessionFactory(user=user, device_id="same-device")

    def test_different_users_same_device_id(self):
        """Different users can have the same device_id."""
        user1 = UserFactory()
        user2 = UserFactory()
        s1 = DeviceSessionFactory(user=user1, device_id="shared-device")
        s2 = DeviceSessionFactory(user=user2, device_id="shared-device")
        assert s1.pk != s2.pk

    def test_current_token_relationship(self):
        """DeviceSession can be linked to a RefreshToken via current_token."""
        token = RefreshTokenFactory()
        session = DeviceSessionFactory(user=token.user, current_token=token)
        assert session.current_token == token
        assert token.session == session

    def test_current_token_nullable(self):
        """DeviceSession can exist without a current_token."""
        session = DeviceSessionFactory(current_token=None)
        assert session.current_token is None

    def test_ordering_by_last_activity(self):
        """Sessions are ordered by -last_activity by default."""
        assert DeviceSession._meta.ordering == ["-last_activity"]


# =============================================================================
# EMAIL VERIFICATION TOKEN TESTS
# =============================================================================


@pytest.mark.django_db
class TestEmailVerificationToken:
    """Tests for the EmailVerificationToken model."""

    def test_creation_with_factory(self):
        """EmailVerificationToken can be created via factory."""
        token = EmailVerificationTokenFactory()
        assert token.pk is not None
        assert token.user is not None
        assert token.is_used is False
        assert token.used_at is None
        assert len(token.code) == 6
        assert token.email == token.user.email

    def test_is_valid_true_for_fresh_token(self):
        """is_valid returns True for an unused, non-expired token."""
        token = EmailVerificationTokenFactory()
        assert token.is_valid is True

    def test_is_valid_false_when_expired(self):
        """is_valid returns False when the token has expired."""
        token = ExpiredVerificationTokenFactory()
        assert token.is_valid is False

    def test_is_valid_false_when_expired_by_one_second(self):
        """is_valid returns False when the token expired just one second ago."""
        user = UserFactory()
        token = EmailVerificationTokenFactory(
            user=user,
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        assert token.is_valid is False

    def test_is_valid_false_when_used(self):
        """is_valid returns False when the token has been used."""
        token = UsedVerificationTokenFactory()
        assert token.is_valid is False

    def test_generate_code_length(self):
        """generate_code returns a 6-character string."""
        code = EmailVerificationToken.generate_code()
        assert len(code) == 6

    def test_generate_code_all_digits(self):
        """generate_code returns a string containing only digits."""
        for _ in range(20):
            code = EmailVerificationToken.generate_code()
            assert code.isdigit()

    def test_create_for_user_returns_token(self):
        """create_for_user returns an EmailVerificationToken instance."""
        user = UserFactory()
        token = EmailVerificationToken.create_for_user(user)
        assert isinstance(token, EmailVerificationToken)
        assert token.pk is not None
        assert token.user == user

    def test_create_for_user_uses_user_email_by_default(self):
        """create_for_user uses user.email when no email is provided."""
        user = UserFactory()
        token = EmailVerificationToken.create_for_user(user)
        assert token.email == user.email

    def test_create_for_user_with_custom_email(self):
        """create_for_user uses the provided email when given."""
        user = UserFactory()
        token = EmailVerificationToken.create_for_user(user, email="new@example.com")
        assert token.email == "new@example.com"

    def test_create_for_user_expiry_is_15_minutes(self):
        """create_for_user sets expiry to ~15 minutes from now."""
        user = UserFactory()
        before = timezone.now()
        token = EmailVerificationToken.create_for_user(user)
        after = timezone.now()
        expected_min = before + timedelta(minutes=15)
        expected_max = after + timedelta(minutes=15)
        assert expected_min <= token.expires_at <= expected_max

    def test_create_for_user_invalidates_existing_tokens(self):
        """create_for_user marks existing active tokens as used before creating new one."""
        user = UserFactory()
        first_token = EmailVerificationToken.create_for_user(user)
        assert first_token.is_used is False

        second_token = EmailVerificationToken.create_for_user(user)
        first_token.refresh_from_db()
        assert first_token.is_used is True
        assert second_token.is_used is False

    def test_mark_used(self):
        """mark_used sets is_used=True and records used_at timestamp."""
        token = EmailVerificationTokenFactory()
        before = timezone.now()
        token.mark_used()
        token.refresh_from_db()
        assert token.is_used is True
        assert token.used_at is not None
        assert token.used_at >= before

    def test_unique_constraint_active_token_per_user(self):
        """Cannot have two active (unused) tokens for the same user via direct creation."""
        user = UserFactory()
        EmailVerificationTokenFactory(user=user, is_used=False)
        with pytest.raises(IntegrityError):
            EmailVerificationTokenFactory(user=user, is_used=False)

    def test_used_tokens_dont_violate_constraint(self):
        """Multiple used tokens for the same user are allowed."""
        user = UserFactory()
        UsedVerificationTokenFactory(user=user)
        UsedVerificationTokenFactory(user=user)
        count = EmailVerificationToken.objects.filter(user=user, is_used=True).count()
        assert count == 2


# =============================================================================
# PASSWORD RESET TOKEN TESTS
# =============================================================================


@pytest.mark.django_db
class TestPasswordResetToken:
    """Tests for the PasswordResetToken model."""

    def test_creation_with_factory(self):
        """PasswordResetToken can be created via factory."""
        token = PasswordResetTokenFactory()
        assert token.pk is not None
        assert token.user is not None
        assert token.is_used is False
        assert token.used_at is None
        assert token.ip_address == "127.0.0.1"

    def test_is_valid_true_for_fresh_token(self):
        """is_valid returns True for an unused, non-expired token."""
        token = PasswordResetTokenFactory()
        assert token.is_valid is True

    def test_is_valid_false_when_expired(self):
        """is_valid returns False when the token has expired."""
        token = ExpiredPasswordResetTokenFactory()
        assert token.is_valid is False

    def test_is_valid_false_when_expired_by_one_second(self):
        """is_valid returns False when the token expired just one second ago."""
        user = UserFactory()
        token = PasswordResetTokenFactory(
            user=user,
            expires_at=timezone.now() - timedelta(seconds=1),
        )
        assert token.is_valid is False

    def test_is_valid_false_when_used(self):
        """is_valid returns False when the token has been used."""
        token = UsedPasswordResetTokenFactory()
        assert token.is_valid is False

    def test_create_for_user_returns_token(self):
        """create_for_user returns a PasswordResetToken instance."""
        user = UserFactory()
        token = PasswordResetToken.create_for_user(user)
        assert isinstance(token, PasswordResetToken)
        assert token.pk is not None
        assert token.user == user

    def test_create_for_user_stores_ip_address(self):
        """create_for_user stores the provided ip_address."""
        user = UserFactory()
        token = PasswordResetToken.create_for_user(user, ip_address="10.0.0.1")
        assert token.ip_address == "10.0.0.1"

    def test_create_for_user_ip_address_default_none(self):
        """create_for_user defaults ip_address to None when not provided."""
        user = UserFactory()
        token = PasswordResetToken.create_for_user(user)
        assert token.ip_address is None

    def test_create_for_user_expiry_is_1_hour(self):
        """create_for_user sets expiry to ~1 hour from now."""
        user = UserFactory()
        before = timezone.now()
        token = PasswordResetToken.create_for_user(user)
        after = timezone.now()
        expected_min = before + timedelta(hours=1)
        expected_max = after + timedelta(hours=1)
        assert expected_min <= token.expires_at <= expected_max

    def test_create_for_user_invalidates_existing_tokens(self):
        """create_for_user marks existing active tokens as used before creating new one."""
        user = UserFactory()
        first_token = PasswordResetToken.create_for_user(user)
        assert first_token.is_used is False

        second_token = PasswordResetToken.create_for_user(user)
        first_token.refresh_from_db()
        assert first_token.is_used is True
        assert second_token.is_used is False

    def test_mark_used(self):
        """mark_used sets is_used=True and records used_at timestamp."""
        token = PasswordResetTokenFactory()
        before = timezone.now()
        token.mark_used()
        token.refresh_from_db()
        assert token.is_used is True
        assert token.used_at is not None
        assert token.used_at >= before

    def test_unique_constraint_active_token_per_user(self):
        """Cannot have two active (unused) tokens for the same user via direct creation."""
        user = UserFactory()
        PasswordResetTokenFactory(user=user, is_used=False)
        with pytest.raises(IntegrityError):
            PasswordResetTokenFactory(user=user, is_used=False)

    def test_used_tokens_dont_violate_constraint(self):
        """Multiple used tokens for the same user are allowed."""
        user = UserFactory()
        UsedPasswordResetTokenFactory(user=user)
        UsedPasswordResetTokenFactory(user=user)
        count = PasswordResetToken.objects.filter(user=user, is_used=True).count()
        assert count == 2

    def test_str_representation(self):
        """String representation includes user_id and status."""
        token = PasswordResetTokenFactory()
        assert "PasswordReset(" in str(token)
        assert "pending" in str(token)

        token.mark_used()
        assert "used" in str(token)


# =============================================================================
# OAUTH CONNECTION TESTS
# =============================================================================


@pytest.mark.django_db
class TestOAuthConnection:
    """Tests for the OAuthConnection model."""

    def test_creation_with_factory(self):
        """OAuthConnection can be created via factory."""
        conn = OAuthConnectionFactory()
        assert conn.pk is not None
        assert conn.user is not None
        assert conn.provider == OAuthConnection.Provider.GOOGLE

    def test_google_connection(self):
        """GoogleOAuthConnectionFactory creates a Google connection with provider data."""
        conn = GoogleOAuthConnectionFactory()
        assert conn.provider == "google"
        assert "sub" in conn.provider_data
        assert conn.provider_data["email_verified"] is True

    def test_apple_connection(self):
        """AppleOAuthConnectionFactory creates an Apple connection with provider data."""
        conn = AppleOAuthConnectionFactory()
        assert conn.provider == "apple"
        assert "sub" in conn.provider_data

    def test_provider_choices(self):
        """All expected Provider choices exist."""
        choices = {c.value for c in OAuthConnection.Provider}
        assert choices == {"google", "apple"}

    def test_unique_together_provider_uid(self):
        """Cannot create two connections with the same provider + provider_uid."""
        conn = OAuthConnectionFactory(provider="google", provider_uid="uid_123")
        with pytest.raises(IntegrityError):
            OAuthConnectionFactory(provider="google", provider_uid="uid_123")

    def test_different_providers_same_uid(self):
        """Different providers can have the same provider_uid."""
        user = UserFactory()
        c1 = OAuthConnectionFactory(
            user=user, provider="google", provider_uid="shared_uid"
        )
        c2 = OAuthConnectionFactory(
            user=user, provider="apple", provider_uid="shared_uid"
        )
        assert c1.pk != c2.pk

    def test_str_representation(self):
        """String representation shows provider and user_id."""
        conn = GoogleOAuthConnectionFactory()
        assert str(conn) == f"google - {conn.user_id}"

    def test_provider_data_defaults_to_dict(self):
        """provider_data defaults to an empty dict when not specified."""
        user = UserFactory()
        conn = OAuthConnection.objects.create(
            user=user,
            provider="google",
            provider_uid="default_test_uid",
            provider_email=user.email,
        )
        assert conn.provider_data == {}

    def test_provider_email_stored(self):
        """provider_email is stored correctly."""
        conn = OAuthConnectionFactory(provider_email="oauth@example.com")
        conn.refresh_from_db()
        assert conn.provider_email == "oauth@example.com"
