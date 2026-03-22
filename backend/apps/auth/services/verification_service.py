"""
Verification Service
====================
Email verification service supporting both magic links and 6-digit codes.

Flow:
    1. User registers → create_token() sends verification email
    2. User clicks link → verify_by_token() validates and marks verified
    3. OR user enters code → verify_by_code() validates and marks verified

Security:
    - Only one active verification token per user (enforced by DB)
    - Tokens expire after 15 minutes
    - Old tokens invalidated when new one is created
"""

import uuid

from django.conf import settings
from django.db import transaction
from django.http import HttpRequest

from apps.auth.models import EmailVerificationToken
from apps.core.exceptions import TokenExpired, TokenInvalid

# Observability
from apps.core.observability import get_logger
from apps.core.observability.audit import AuditLog, AuditService
from apps.users.services import UserService

logger = get_logger(__name__)


class VerificationService:
    """
    Email verification service.

    Supports both magic link (UUID token) and 6-digit code verification.
    """

    @staticmethod
    @transaction.atomic
    def create_token(
        *, user, request: HttpRequest | None = None
    ) -> EmailVerificationToken:
        """
        Create verification token and send email.

        Args:
            user: User to send verification to
            request: HTTP request for audit context (optional)

        Returns:
            EmailVerificationToken instance
        """
        # Already verified?
        if user.is_verified:
            logger.debug(
                "auth.verification.already_verified",
                user_id=str(user.id),
            )
            return None

        # Create token (invalidates existing tokens)
        token = EmailVerificationToken.create_for_user(user)

        # Build verification URL
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        verification_link = f"{frontend_url}/verify-email?token={token.token}"

        # Log verification details in DEBUG mode (structured output via structlog)
        if getattr(settings, "DEBUG", False):
            logger.info(
                "dev.verification_code",
                user=user.email,
                code=token.code,
                link=verification_link,
            )

        # Defer notification until transaction commits (Celery dispatch safety)
        _user, _link, _code = user, verification_link, token.code

        def _send_verification():
            try:
                from apps.notifications.services import NotificationService

                NotificationService.send(
                    user=_user,
                    notification_type="verify_email",
                    context={
                        "verification_link": _link,
                        "code": _code,
                    },
                    force_channels=["email"],
                )
            except Exception as e:
                logger.error(
                    "auth.verification.send_failed",
                    user_id=str(_user.id),
                    error=str(e),
                )

        transaction.on_commit(_send_verification)

        logger.info(
            "auth.verification.scheduled",
            user_id=str(user.id),
            token_id=str(token.token),
        )

        # Audit: Verification email scheduled
        AuditService.log(
            action=AuditLog.Action.VERIFICATION_SENT,
            actor=user,
            resource=token,
            request=request,
        )

        return token

    @staticmethod
    @transaction.atomic
    def verify_by_token(
        token_uuid: uuid.UUID, request: HttpRequest | None = None
    ) -> "User":
        """
        Verify email using magic link token.

        Args:
            token_uuid: UUID token from verification link
            request: HTTP request for audit context (optional)

        Returns:
            Verified User instance

        Raises:
            TokenInvalid: Token not found or already used
            TokenExpired: Token has expired
        """
        token = (
            EmailVerificationToken.objects.filter(token=token_uuid, is_used=False)
            .select_related("user")
            .first()
        )

        if not token:
            logger.warning(
                "auth.verification.invalid_token",
                token=str(token_uuid),
            )
            raise TokenInvalid(message="Invalid verification link")

        if not token.is_valid:
            logger.warning(
                "auth.verification.expired_token",
                token_id=str(token.token),
                user_id=str(token.user_id),
            )
            raise TokenExpired(message="Verification link has expired")

        # Mark token as used
        token.mark_used()

        # Verify user
        user = token.user
        UserService.verify_email(user=user)

        logger.info(
            "auth.verification.success",
            user_id=str(user.id),
            method="link",
        )

        # Audit: Email verified
        AuditService.log(
            action=AuditLog.Action.EMAIL_VERIFIED,
            actor=user,
            resource=user,
            request=request,
            details={"method": "link"},
        )

        # Send welcome notification
        VerificationService._send_welcome_notification(user)

        return user

    @staticmethod
    @transaction.atomic
    def verify_by_code(
        email: str, code: str, request: HttpRequest | None = None
    ) -> "User":
        """
        Verify email using 6-digit code.

        Args:
            email: User's email address
            code: 6-digit verification code
            request: HTTP request for audit context (optional)

        Returns:
            Verified User instance

        Raises:
            TokenInvalid: Code not found or already used
            TokenExpired: Code has expired
        """
        # Find token by code and email
        token = (
            EmailVerificationToken.objects.filter(
                email__iexact=email.strip(), code=code, is_used=False
            )
            .select_related("user")
            .first()
        )

        if not token:
            logger.warning(
                "auth.verification.invalid_code",
                email_hash=hash(email),
            )
            raise TokenInvalid(message="Invalid verification code")

        if not token.is_valid:
            logger.warning(
                "auth.verification.expired_code",
                token_id=str(token.token),
                user_id=str(token.user_id),
            )
            raise TokenExpired(message="Verification code has expired")

        # Mark token as used
        token.mark_used()

        # Verify user
        user = token.user
        UserService.verify_email(user=user)

        logger.info(
            "auth.verification.success",
            user_id=str(user.id),
            method="code",
        )

        # Audit: Email verified
        AuditService.log(
            action=AuditLog.Action.EMAIL_VERIFIED,
            actor=user,
            resource=user,
            request=request,
            details={"method": "code"},
        )

        # Send welcome notification
        VerificationService._send_welcome_notification(user)

        return user

    @staticmethod
    def resend_verification(
        user, request: HttpRequest | None = None
    ) -> EmailVerificationToken | None:
        """
        Resend verification email.

        Rate limiting should be applied at the view level.

        Args:
            user: User to resend verification to
            request: HTTP request for audit context (optional)

        Returns:
            New EmailVerificationToken or None if already verified
        """
        if user.is_verified:
            return None

        return VerificationService.create_token(user=user, request=request)

    @staticmethod
    def _send_welcome_notification(user) -> None:
        """Send welcome notification after verification."""
        try:
            from apps.notifications.services import NotificationService

            NotificationService.send(
                user=user,
                notification_type="welcome",
                context={},  # user_name auto-added by channel
            )

        except Exception as e:
            # Don't fail verification due to notification error
            logger.error(
                "auth.welcome.send_failed",
                user_id=str(user.id),
                error=str(e),
            )
