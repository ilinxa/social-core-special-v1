"""
Auth Selectors
==============
Read-only queries for authentication data.

All read operations for auth models SHOULD go through this selector layer.
"""

from django.db.models import QuerySet
from django.utils import timezone

from apps.auth.models import (
    DeviceSession,
    EmailVerificationToken,
    OAuthConnection,
    PasswordResetToken,
    RefreshToken,
)


class AuthSelector:
    """
    Read-only queries for authentication data.
    """

    # =========================================================================
    # REFRESH TOKENS
    # =========================================================================

    @staticmethod
    def get_active_tokens_for_user(user) -> QuerySet[RefreshToken]:
        """Get all active (valid) refresh tokens for a user."""
        return RefreshToken.objects.filter(
            user=user,
            is_revoked=False,
            replaced_by__isnull=True,
            expires_at__gt=timezone.now(),
        )

    @staticmethod
    def count_active_tokens_for_user(user) -> int:
        """Count active refresh tokens for a user."""
        return AuthSelector.get_active_tokens_for_user(user).count()

    # =========================================================================
    # DEVICE SESSIONS
    # =========================================================================

    @staticmethod
    def get_active_sessions_for_user(user) -> QuerySet[DeviceSession]:
        """Get all active sessions for a user."""
        return (
            DeviceSession.objects.filter(user=user, is_active=True)
            .select_related("current_token")
            .order_by("-last_activity")
        )

    @staticmethod
    def get_session_by_id(user, session_id: str) -> DeviceSession | None:
        """Get a specific session for a user."""
        return DeviceSession.objects.filter(
            user=user, id=session_id, is_active=True
        ).first()

    @staticmethod
    def count_active_sessions_for_user(user) -> int:
        """Count active sessions for a user."""
        return DeviceSession.objects.filter(user=user, is_active=True).count()

    # =========================================================================
    # VERIFICATION TOKENS
    # =========================================================================

    @staticmethod
    def get_pending_verification_for_user(user) -> EmailVerificationToken | None:
        """Get pending verification token for a user."""
        return EmailVerificationToken.objects.filter(
            user=user, is_used=False, expires_at__gt=timezone.now()
        ).first()

    @staticmethod
    def has_pending_verification(user) -> bool:
        """Check if user has a pending verification token."""
        return EmailVerificationToken.objects.filter(
            user=user, is_used=False, expires_at__gt=timezone.now()
        ).exists()

    # =========================================================================
    # PASSWORD RESET TOKENS
    # =========================================================================

    @staticmethod
    def get_pending_password_reset_for_user(user) -> PasswordResetToken | None:
        """Get pending password reset token for a user."""
        return PasswordResetToken.objects.filter(
            user=user, is_used=False, expires_at__gt=timezone.now()
        ).first()

    @staticmethod
    def has_pending_password_reset(user) -> bool:
        """Check if user has a pending password reset token."""
        return PasswordResetToken.objects.filter(
            user=user, is_used=False, expires_at__gt=timezone.now()
        ).exists()

    # =========================================================================
    # OAUTH CONNECTIONS
    # =========================================================================

    @staticmethod
    def get_oauth_connections_for_user(user) -> QuerySet[OAuthConnection]:
        """Get all OAuth connections for a user."""
        return OAuthConnection.objects.filter(user=user)

    @staticmethod
    def get_oauth_connection(user, provider: str) -> OAuthConnection | None:
        """Get specific OAuth connection for a user."""
        return OAuthConnection.objects.filter(user=user, provider=provider).first()

    @staticmethod
    def has_oauth_connection(user, provider: str) -> bool:
        """Check if user has a specific OAuth connection."""
        return OAuthConnection.objects.filter(user=user, provider=provider).exists()

    @staticmethod
    def get_oauth_by_provider_uid(
        provider: str, provider_uid: str
    ) -> OAuthConnection | None:
        """Get OAuth connection by provider UID."""
        return (
            OAuthConnection.objects.filter(provider=provider, provider_uid=provider_uid)
            .select_related("user")
            .first()
        )
