"""
Password Service
================
Password reset and change service.

Flows:
    1. Password Reset (forgot password):
       - request_reset() → sends reset email with link
       - confirm_reset() → validates token and sets new password

    2. Password Change (logged in user):
       - change_password() → validates current password, sets new one

Security:
    - Only one active reset token per user (enforced by DB)
    - Tokens expire after 1 hour
    - Password change revokes all sessions (optional)
    - Old tokens invalidated when new one is created
"""

import uuid
from typing import Optional

from django.conf import settings
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone

from apps.core.exceptions import (
    InvalidCredentials,
    TokenExpired,
    TokenInvalid,
    ValidationError,
)
from apps.core.utils.password import validate_password_strength, verify_password
from apps.users.selectors import UserSelector

from apps.auth.models import PasswordResetToken

# Observability
from apps.core.observability import get_logger
from apps.core.observability.audit import AuditService, AuditLog

logger = get_logger(__name__)


class PasswordService:
    """
    Password management service.

    Handles password reset flow and authenticated password changes.
    """

    @staticmethod
    @transaction.atomic
    def request_reset(
        *,
        email: str,
        ip_address: str = None,
        request: Optional[HttpRequest] = None
    ) -> bool:
        """
        Request password reset.

        Creates reset token and sends email. Returns True regardless of
        whether user exists (prevents email enumeration).

        Args:
            email: User's email address
            ip_address: Request IP for audit
            request: HTTP request for audit context (optional)

        Returns:
            Always returns True (don't reveal if email exists)
        """
        user = UserSelector.get_by_email_or_none(email=email)

        if not user:
            # Don't reveal that email doesn't exist
            logger.info(
                "auth.password_reset.user_not_found",
                email_hash=hash(email),
            )
            return True

        if not user.is_active:
            # Don't reveal account status
            logger.info(
                "auth.password_reset.inactive_account",
                user_id=str(user.id),
            )
            return True

        # Create token (invalidates existing tokens)
        token = PasswordResetToken.create_for_user(user, ip_address=ip_address)

        # Build reset URL
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        reset_link = f"{frontend_url}/reset-password?token={token.token}"

        # Log reset link to console in DEBUG mode
        if getattr(settings, 'DEBUG', False):
            print(f"\n{'=' * 60}")
            print("PASSWORD RESET LINK (Dev Console)")
            print(f"{'=' * 60}")
            print(f"User: {user.email}")
            print(f"Link: {reset_link}")
            print(f"{'=' * 60}\n")

        # Send notification via Notifications system
        try:
            from apps.notifications.services import NotificationService

            NotificationService.send(
                user=user,
                notification_type='password_reset',
                context={
                    'reset_link': reset_link
                },
                force_channels=['email']  # Always send via email
            )

            logger.info(
                "auth.password_reset.sent",
                user_id=str(user.id),
                token_id=str(token.token),
            )

            # Audit: Password reset requested
            AuditService.log(
                action=AuditLog.Action.PASSWORD_RESET_REQUESTED,
                actor=user,
                resource=token,
                request=request,
            )

        except Exception as e:
            logger.error(
                "auth.password_reset.send_failed",
                user_id=str(user.id),
                error=str(e),
            )

        return True

    @staticmethod
    @transaction.atomic
    def confirm_reset(
        *,
        token_uuid: uuid.UUID,
        new_password: str,
        logout_all_sessions: bool = True,
        request: Optional[HttpRequest] = None
    ) -> 'User':
        """
        Confirm password reset with new password.

        Args:
            token_uuid: Reset token UUID
            new_password: New password to set
            logout_all_sessions: Whether to revoke all sessions (default True)
            request: HTTP request for audit context (optional)

        Returns:
            Updated User instance

        Raises:
            TokenInvalid: Token not found or already used
            TokenExpired: Token has expired
            ValidationError: New password doesn't meet requirements
        """
        # Find token
        token = PasswordResetToken.objects.filter(
            token=token_uuid,
            is_used=False
        ).select_related('user').first()

        if not token:
            logger.warning(
                "auth.password_reset.invalid_token",
                token=str(token_uuid),
            )
            raise TokenInvalid(message="Invalid password reset link")

        if not token.is_valid:
            logger.warning(
                "auth.password_reset.expired_token",
                token_id=str(token.token),
                user_id=str(token.user_id),
            )
            raise TokenExpired(message="Password reset link has expired")

        # Validate new password
        password_errors = validate_password_strength(new_password, user=token.user)
        if password_errors:
            raise ValidationError(
                message=password_errors[0],
                field='new_password'
            )

        # Mark token as used
        token.mark_used()

        # Update password
        user = token.user
        user.set_password(new_password)
        user.save(update_fields=['password'])

        logger.info(
            "auth.password_reset.success",
            user_id=str(user.id),
        )

        # Audit: Password reset completed
        AuditService.log(
            action=AuditLog.Action.PASSWORD_RESET_COMPLETED,
            actor=user,
            resource=user,
            request=request,
        )

        # Logout all sessions for security
        if logout_all_sessions:
            from apps.auth.services import AuthService
            AuthService.logout_all(user=user, reason='password_change', request=request)

        # Send confirmation notification
        PasswordService._send_password_changed_notification(user)

        return user

    @staticmethod
    @transaction.atomic
    def change_password(
        *,
        user,
        current_password: str,
        new_password: str,
        logout_other_sessions: bool = True,
        request: Optional[HttpRequest] = None
    ) -> 'User':
        """
        Change password for authenticated user.

        Args:
            user: Authenticated user
            current_password: Current password for verification
            new_password: New password to set
            logout_other_sessions: Whether to revoke other sessions (default True)
            request: HTTP request for audit context (optional)

        Returns:
            Updated User instance

        Raises:
            InvalidCredentials: Current password is wrong
            ValidationError: New password doesn't meet requirements
        """
        # Verify current password
        if not verify_password(current_password, user.password):
            logger.warning(
                "auth.password_change.wrong_current",
                user_id=str(user.id),
            )
            # Audit: Failed password change (wrong current password)
            AuditService.log_failure(
                action=AuditLog.Action.PASSWORD_CHANGED,
                reason="wrong_current_password",
                actor=user,
                request=request,
            )
            raise InvalidCredentials(message="Current password is incorrect")

        # Validate new password
        password_errors = validate_password_strength(new_password, user=user)
        if password_errors:
            raise ValidationError(
                message=password_errors[0],
                field='new_password'
            )

        # Check new password is different
        if verify_password(new_password, user.password):
            raise ValidationError(
                message="New password must be different from current password",
                field='new_password'
            )

        # Update password
        user.set_password(new_password)
        user.save(update_fields=['password'])

        logger.info(
            "auth.password_change.success",
            user_id=str(user.id),
        )

        # Audit: Password changed successfully
        AuditService.log(
            action=AuditLog.Action.PASSWORD_CHANGED,
            actor=user,
            resource=user,
            request=request,
        )

        # Logout other sessions for security
        if logout_other_sessions:
            from apps.auth.services import AuthService
            from apps.auth.blacklist import JTIBlacklist

            # Blacklist all JTIs except current (if we knew it)
            # For simplicity, blacklist all and client will re-authenticate
            JTIBlacklist.blacklist_user_tokens(user.id)

        # Send confirmation notification
        PasswordService._send_password_changed_notification(user)

        return user

    @staticmethod
    def _send_password_changed_notification(user) -> None:
        """Send notification after password change."""
        try:
            from apps.notifications.services import NotificationService

            NotificationService.send(
                user=user,
                notification_type='password_changed',
                context={}  # user_name auto-added by channel
            )

        except Exception as e:
            # Don't fail password change due to notification error
            logger.error(
                "auth.password_changed.notification_failed",
                user_id=str(user.id),
                error=str(e),
            )
