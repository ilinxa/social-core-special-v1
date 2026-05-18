# apps/auth/services/governance_service.py
"""
Governance Auth Service
=======================
Step-up authentication for the Governance Console (gconsole).

Supports two authentication methods:
    - Password re-entry
    - Email OTP (6-digit code)

Both methods issue a short-lived governance-scoped JWT that grants
access to governance endpoints. The token has token_scope="governance"
and a configurable TTL (default 30 minutes).

Security:
    - Account lockout applies (shared with login lockout)
    - OTP brute-force protection via per-token attempt counter
    - No refresh token issued — re-authenticate on expiry
    - Governance token uses independent JTI (not linked to RefreshToken)
"""

import uuid
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone

from apps.auth.models import GovernanceOTPToken
from apps.core.constants import AccountType
from apps.core.exceptions import (
    AccountLocked,
    InvalidCredentials,
    PermissionDenied,
    TokenExpired,
    TokenInvalid,
)
from apps.core.feature_config import feature_config
from apps.core.observability import get_logger
from apps.core.observability.audit import AuditLog, AuditService
from apps.core.utils.jwt import encode_token
from apps.core.utils.password import verify_password
from apps.rbac.selectors import MembershipSelector, PermissionSelector

logger = get_logger(__name__)


@dataclass
class GovernanceToken:
    """Result of a successful governance step-up authentication."""

    access_token: str
    expires_in: int


class GovernanceAuthService:
    """Service for governance console step-up authentication."""

    # ------------------------------------------------------------------
    # PUBLIC METHODS
    # ------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def authenticate_with_password(
        *,
        user,
        password: str,
        request: HttpRequest | None = None,
    ) -> GovernanceToken:
        """
        Step-up authentication via password re-entry.

        Args:
            user: The authenticated user (from request.user).
            password: The user's password for re-verification.
            request: HTTP request for audit context.

        Returns:
            GovernanceToken with short-lived JWT.

        Raises:
            AccountLocked: If the account is locked out.
            InvalidCredentials: If the password is wrong.
            PermissionDenied: If the user lacks global permissions.
        """
        GovernanceAuthService._check_lockout(user, request)
        GovernanceAuthService._verify_password(user, password, request)
        GovernanceAuthService._check_global_permissions(user, request)

        # Reset lockout on success
        if user.failed_login_attempts:
            user.failed_login_attempts = 0
            user.locked_until = None
            user.save(update_fields=["failed_login_attempts", "locked_until"])

        token = GovernanceAuthService._issue_governance_token(user)

        logger.info(
            "auth.governance.step_up.success",
            user_id=str(user.id),
            method="password",
        )

        AuditService.log(
            action=AuditLog.Action.GOVERNANCE_AUTHENTICATED,
            actor=user,
            request=request,
            details={"method": "password"},
        )

        return token

    @staticmethod
    def send_otp(
        *,
        user,
        request: HttpRequest | None = None,
    ) -> None:
        """
        Send a governance OTP code to the user's verified email.

        Args:
            user: The authenticated user.
            request: HTTP request for audit context.

        Raises:
            PermissionDenied: If the user lacks global permissions.
        """
        GovernanceAuthService._check_global_permissions(user, request)

        otp = GovernanceOTPToken.create_for_user(user)

        logger.info(
            "auth.governance.otp.sent",
            user_id=str(user.id),
        )

        # Defer email delivery until transaction commits
        _user = user
        _code = otp.code

        def _send_otp_email():
            from apps.notifications.services import NotificationService

            NotificationService.send(
                user=_user,
                notification_type="governance_otp",
                context={"code": _code},
                force_channels=["email"],
                scope_type="platform",
            )

        transaction.on_commit(_send_otp_email)

    @staticmethod
    @transaction.atomic
    def verify_otp(
        *,
        user,
        code: str,
        request: HttpRequest | None = None,
    ) -> GovernanceToken:
        """
        Verify a governance OTP code and issue a governance token.

        Args:
            user: The authenticated user.
            code: The 6-digit OTP code.
            request: HTTP request for audit context.

        Returns:
            GovernanceToken with short-lived JWT.

        Raises:
            TokenInvalid: If code is wrong or no active OTP.
            TokenExpired: If OTP has expired.
            PermissionDenied: If max attempts exceeded or user lacks permissions.
        """
        # Find active OTP for this user
        otp = (
            GovernanceOTPToken.objects.filter(
                user=user,
                is_used=False,
            )
            .order_by("-created_at")
            .first()
        )

        if not otp:
            logger.warning(
                "auth.governance.otp.failed",
                user_id=str(user.id),
                reason="no_active_otp",
            )
            raise TokenInvalid(message="No active governance OTP found")

        # Check expiry
        if not otp.is_valid:
            logger.warning(
                "auth.governance.otp.failed",
                user_id=str(user.id),
                reason="otp_expired",
            )
            raise TokenExpired(message="Governance OTP has expired")

        # Check max attempts
        if otp.is_max_attempts_reached:
            otp.mark_used()  # Invalidate to force new OTP
            logger.warning(
                "auth.governance.otp.failed",
                user_id=str(user.id),
                reason="max_attempts",
            )
            raise PermissionDenied(
                message="Too many failed OTP attempts. Request a new code."
            )

        # Verify code
        if otp.code != code:
            otp.increment_attempts()
            logger.warning(
                "auth.governance.otp.failed",
                user_id=str(user.id),
                reason="invalid_code",
                attempts=otp.attempts,
            )
            raise TokenInvalid(message="Invalid governance OTP code")

        # Success
        otp.mark_used()
        GovernanceAuthService._check_global_permissions(user, request)

        token = GovernanceAuthService._issue_governance_token(user)

        logger.info(
            "auth.governance.step_up.success",
            user_id=str(user.id),
            method="otp",
        )

        AuditService.log(
            action=AuditLog.Action.GOVERNANCE_AUTHENTICATED,
            actor=user,
            request=request,
            details={"method": "otp"},
        )

        return token

    @staticmethod
    def has_any_global_permission(user) -> bool:
        """
        Check if user has at least one global_only or platform_and_global
        scoped permission via their platform membership.

        Used by:
            - GovernanceAuthService (before issuing tokens)
            - GovernanceTokenRequired (on every governance request)
        """
        from apps.organization.platform.models import PlatformAccount

        platform = PlatformAccount.objects.first()
        if not platform:
            return False

        membership = MembershipSelector.get_active_membership_for_user_account(
            user=user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        )
        if not membership:
            return False

        permissions = PermissionSelector.get_permissions_for_membership(
            membership_id=membership.id,
        )
        return any(
            scope in ("global_only", "platform_and_global")
            for _code, scope in permissions
        )

    # ------------------------------------------------------------------
    # PRIVATE METHODS
    # ------------------------------------------------------------------

    @staticmethod
    def _check_lockout(user, request=None):
        """Check if account is locked out. Raises AccountLocked if so."""
        if user.locked_until and user.locked_until > timezone.now():
            remaining = int((user.locked_until - timezone.now()).total_seconds())
            logger.warning(
                "auth.governance.step_up.failed",
                user_id=str(user.id),
                reason="account_locked",
            )
            AuditService.log_failure(
                action=AuditLog.Action.GOVERNANCE_AUTHENTICATED,
                reason="account_locked",
                actor=user,
                request=request,
            )
            raise AccountLocked(details={"retry_after": remaining})

    @staticmethod
    def _verify_password(user, password, request=None):
        """Verify password. Increments lockout counter on failure."""
        if not verify_password(password, user.password):
            logger.warning(
                "auth.governance.step_up.failed",
                user_id=str(user.id),
                reason="invalid_password",
            )

            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            max_attempts = feature_config.get_value(
                "auth.lockout.max_failed_attempts", 10
            )
            if user.failed_login_attempts >= max_attempts:
                lockout_duration = feature_config.get_value(
                    "auth.lockout.duration", 900
                )
                user.locked_until = timezone.now() + timedelta(seconds=lockout_duration)
            user.save(update_fields=["failed_login_attempts", "locked_until"])

            AuditService.log_failure(
                action=AuditLog.Action.GOVERNANCE_AUTHENTICATED,
                reason="invalid_password",
                actor=user,
                request=request,
            )
            raise InvalidCredentials()

    @staticmethod
    def _check_global_permissions(user, request=None):
        """Check user has governance-level permissions. Raises PermissionDenied if not."""
        if not GovernanceAuthService.has_any_global_permission(user):
            logger.warning(
                "auth.governance.step_up.failed",
                user_id=str(user.id),
                reason="no_global_permissions",
            )
            AuditService.log_failure(
                action=AuditLog.Action.GOVERNANCE_AUTHENTICATED,
                reason="no_global_permissions",
                actor=user,
                request=request,
            )
            raise PermissionDenied(message="You do not have governance access")

    @staticmethod
    def _issue_governance_token(user) -> GovernanceToken:
        """Create a short-lived JWT with governance scope."""
        expires_in = feature_config.get_value("auth.governance.token_lifetime", 1800)
        jti = uuid.uuid4()

        access_token = encode_token(
            payload={
                "user_id": str(user.id),
                "jti": str(jti),
                "email": user.email,
                "is_verified": user.is_verified,
                "token_type": "access",
                "token_scope": "governance",
            },
            expires_in=expires_in,
        )

        return GovernanceToken(
            access_token=access_token,
            expires_in=expires_in,
        )
