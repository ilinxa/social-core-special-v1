# apps/auth/tests/factories.py
"""
Factory-boy factories for Auth app tests.

Usage:
    from apps.auth.tests.factories import RefreshTokenFactory, DeviceSessionFactory

    # Create a refresh token (with raw token for testing)
    token_obj, raw_token = RefreshTokenFactory.create_with_raw_token(user=user)

    # Create a device session
    session = DeviceSessionFactory(user=user)
"""

import hashlib
import secrets
import uuid
from datetime import timedelta

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from apps.auth.models import (
    DeviceSession,
    EmailVerificationToken,
    OAuthConnection,
    PasswordResetToken,
    RefreshToken,
)
from apps.users.tests.factories import UserFactory

# =============================================================================
# REFRESH TOKEN FACTORY
# =============================================================================


class RefreshTokenFactory(DjangoModelFactory):
    """
    Factory for RefreshToken.

    Note: token_hash is a SHA256 hash of a random token. If you need
    the raw token for testing refresh flows, use create_with_raw_token().
    """

    class Meta:
        model = RefreshToken

    user = factory.SubFactory(UserFactory)
    token_hash = factory.LazyFunction(
        lambda: hashlib.sha256(secrets.token_urlsafe(32).encode()).hexdigest()
    )
    jti = factory.LazyFunction(uuid.uuid4)
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=7))
    device_id = factory.Sequence(lambda n: f"device_{n}")
    device_info = factory.LazyFunction(dict)
    ip_address = "127.0.0.1"
    is_revoked = False
    revoked_at = None
    revoked_reason = ""
    replaced_by = None

    @classmethod
    def create_with_raw_token(cls, **kwargs):
        """
        Create a RefreshToken and return (instance, raw_token).

        Use this when you need the raw token value (e.g., for logout/refresh tests).
        """
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        instance = cls.create(token_hash=token_hash, **kwargs)
        return instance, raw_token


class ExpiredRefreshTokenFactory(RefreshTokenFactory):
    """Factory for expired refresh tokens."""

    expires_at = factory.LazyFunction(lambda: timezone.now() - timedelta(hours=1))


class RevokedRefreshTokenFactory(RefreshTokenFactory):
    """Factory for revoked refresh tokens."""

    is_revoked = True
    revoked_at = factory.LazyFunction(timezone.now)
    revoked_reason = "logout"


# =============================================================================
# DEVICE SESSION FACTORY
# =============================================================================


class DeviceSessionFactory(DjangoModelFactory):
    """Factory for DeviceSession."""

    class Meta:
        model = DeviceSession

    user = factory.SubFactory(UserFactory)
    device_id = factory.Sequence(lambda n: f"device_{n}")
    device_name = factory.Sequence(lambda n: f"Test Device {n}")
    device_type = DeviceSession.DeviceType.WEB
    user_agent = "Mozilla/5.0 (Test)"
    ip_address = "127.0.0.1"
    location = ""
    is_active = True
    current_token = None


# =============================================================================
# EMAIL VERIFICATION TOKEN FACTORY
# =============================================================================


class EmailVerificationTokenFactory(DjangoModelFactory):
    """Factory for EmailVerificationToken."""

    class Meta:
        model = EmailVerificationToken

    user = factory.SubFactory(UserFactory)
    token = factory.LazyFunction(uuid.uuid4)
    code = factory.LazyFunction(
        lambda: "".join(secrets.choice("0123456789") for _ in range(6))
    )
    email = factory.LazyAttribute(lambda obj: obj.user.email)
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(minutes=15))
    is_used = False
    used_at = None


class ExpiredVerificationTokenFactory(EmailVerificationTokenFactory):
    """Factory for expired verification tokens."""

    expires_at = factory.LazyFunction(lambda: timezone.now() - timedelta(hours=1))


class UsedVerificationTokenFactory(EmailVerificationTokenFactory):
    """Factory for used verification tokens."""

    is_used = True
    used_at = factory.LazyFunction(timezone.now)


# =============================================================================
# PASSWORD RESET TOKEN FACTORY
# =============================================================================


class PasswordResetTokenFactory(DjangoModelFactory):
    """Factory for PasswordResetToken."""

    class Meta:
        model = PasswordResetToken

    user = factory.SubFactory(UserFactory)
    token = factory.LazyFunction(uuid.uuid4)
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(hours=1))
    is_used = False
    used_at = None
    ip_address = "127.0.0.1"


class ExpiredPasswordResetTokenFactory(PasswordResetTokenFactory):
    """Factory for expired password reset tokens."""

    expires_at = factory.LazyFunction(lambda: timezone.now() - timedelta(hours=1))


class UsedPasswordResetTokenFactory(PasswordResetTokenFactory):
    """Factory for used password reset tokens."""

    is_used = True
    used_at = factory.LazyFunction(timezone.now)


# =============================================================================
# OAUTH CONNECTION FACTORY
# =============================================================================


class OAuthConnectionFactory(DjangoModelFactory):
    """Factory for OAuthConnection."""

    class Meta:
        model = OAuthConnection

    user = factory.SubFactory(UserFactory)
    provider = OAuthConnection.Provider.GOOGLE
    provider_uid = factory.Sequence(lambda n: f"provider_uid_{n}")
    access_token = factory.LazyFunction(lambda: secrets.token_urlsafe(32))
    refresh_token = factory.LazyFunction(lambda: secrets.token_urlsafe(32))
    token_expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(hours=1))
    provider_data = factory.LazyFunction(dict)
    provider_email = factory.LazyAttribute(lambda obj: obj.user.email)


class GoogleOAuthConnectionFactory(OAuthConnectionFactory):
    """Factory for Google OAuth connections."""

    provider = OAuthConnection.Provider.GOOGLE
    provider_data = factory.LazyFunction(
        lambda: {
            "sub": "google_123456",
            "email": "user@gmail.com",
            "email_verified": True,
            "name": "Test User",
        }
    )


class AppleOAuthConnectionFactory(OAuthConnectionFactory):
    """Factory for Apple OAuth connections."""

    provider = OAuthConnection.Provider.APPLE
    provider_data = factory.LazyFunction(
        lambda: {
            "sub": "apple_123456",
            "email": "user@privaterelay.appleid.com",
            "email_verified": True,
        }
    )
