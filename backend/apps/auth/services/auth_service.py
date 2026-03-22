"""
Auth Service
============
Core authentication service for login, logout, and token management.

Responsibilities:
    - User login with credential validation
    - Token pair creation and rotation
    - Session management and limits
    - Logout (single and all sessions)
    - Access token validation

Security:
    - Refresh tokens stored as SHA256 hash
    - Token rotation on every refresh (single-use)
    - Token reuse detection triggers full revocation
    - Session limits enforced per user
    - JTI blacklist for immediate access token revocation
"""

import uuid
from dataclasses import dataclass
from typing import Tuple

from django.conf import settings
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone

from apps.auth.models import DeviceSession, RefreshToken
from apps.core.exceptions import (
    AccountInactive,
    AccountLocked,
    AccountNotVerified,
    InvalidCredentials,
    TokenExpired,
    TokenInvalid,
)

# Observability
from apps.core.observability import get_logger
from apps.core.observability.audit import AuditLog, AuditService
from apps.core.utils.jwt import decode_token, encode_token
from apps.core.utils.password import verify_password
from apps.users.selectors import UserSelector

logger = get_logger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class TokenPair:
    """Response containing access and refresh tokens."""

    access_token: str
    refresh_token: str
    access_expires_in: int
    refresh_expires_in: int


@dataclass
class DeviceInfo:
    """Information about the client device."""

    device_id: str
    device_type: str = "unknown"
    device_name: str = ""
    user_agent: str = ""
    ip_address: str | None = None


# =============================================================================
# AUTH SERVICE
# =============================================================================


class AuthService:
    """
    Core authentication service.

    All authentication operations (login, logout, token management)
    should go through this service.
    """

    @staticmethod
    @transaction.atomic
    def login(
        *,
        email: str,
        password: str,
        device_info: DeviceInfo,
        require_verified: bool = False,
        request: HttpRequest | None = None,
    ) -> Tuple["User", TokenPair, DeviceSession]:
        """
        Authenticate user and create session.

        Args:
            email: User's email address
            password: Plain text password
            device_info: Client device information
            require_verified: If True, require email verification
            request: HTTP request for audit context (optional)

        Returns:
            Tuple of (User, TokenPair, DeviceSession)

        Raises:
            InvalidCredentials: Wrong email or password
            AccountInactive: Account is deactivated
            AccountNotVerified: Email not verified (if required)
        """
        # Get user
        user = UserSelector.get_by_email_or_none(email=email, with_profile=True)
        if not user:
            logger.warning(
                "auth.login.failed",
                email_hash=hash(email),
                reason="user_not_found",
            )
            # Audit: Failed login (user not found)
            AuditService.log_failure(
                action=AuditLog.Action.LOGIN_FAILED,
                reason="user_not_found",
                request=request,
                details={"email_hash": hash(email)},
            )
            raise InvalidCredentials()

        # Check account lockout (before password check to prevent timing attacks)
        if user.locked_until and user.locked_until > timezone.now():
            remaining = int((user.locked_until - timezone.now()).total_seconds())
            logger.warning(
                "auth.login.failed",
                user_id=str(user.id),
                reason="account_locked",
            )
            AuditService.log_failure(
                action=AuditLog.Action.LOGIN_FAILED,
                reason="account_locked",
                actor=user,
                request=request,
            )
            raise AccountLocked(details={"retry_after": remaining})

        # Verify password
        if not verify_password(password, user.password):
            logger.warning(
                "auth.login.failed",
                user_id=str(user.id),
                reason="invalid_password",
            )
            # Increment failed attempt counter
            from datetime import timedelta

            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            max_attempts = getattr(settings, "AUTH_MAX_FAILED_ATTEMPTS", 10)
            if user.failed_login_attempts >= max_attempts:
                lockout_duration = getattr(settings, "AUTH_LOCKOUT_DURATION", 900)
                user.locked_until = timezone.now() + timedelta(seconds=lockout_duration)
                logger.warning(
                    "auth.login.account_locked",
                    user_id=str(user.id),
                    attempts=user.failed_login_attempts,
                )
            user.save(update_fields=["failed_login_attempts", "locked_until"])

            # Audit: Failed login (wrong password)
            AuditService.log_failure(
                action=AuditLog.Action.LOGIN_FAILED,
                reason="invalid_password",
                actor=user,
                request=request,
            )
            raise InvalidCredentials()

        # Check account status
        if not user.is_active:
            logger.warning(
                "auth.login.failed",
                user_id=str(user.id),
                reason="account_inactive",
            )
            # Audit: Failed login (inactive account)
            AuditService.log_failure(
                action=AuditLog.Action.LOGIN_FAILED,
                reason="account_inactive",
                actor=user,
                request=request,
            )
            raise AccountInactive()

        # Check verification if required
        if require_verified and not user.is_verified:
            logger.warning(
                "auth.login.failed",
                user_id=str(user.id),
                reason="not_verified",
            )
            # Audit: Failed login (not verified)
            AuditService.log_failure(
                action=AuditLog.Action.LOGIN_FAILED,
                reason="email_not_verified",
                actor=user,
                request=request,
            )
            raise AccountNotVerified()

        # Reset lockout counter on successful login
        if user.failed_login_attempts > 0 or user.locked_until:
            user.failed_login_attempts = 0
            user.locked_until = None
            user.save(update_fields=["failed_login_attempts", "locked_until"])

        # Create or update device session
        session, is_new_device = AuthService._get_or_create_session(user, device_info)

        # Enforce session limit
        AuthService._enforce_session_limit(user, session)

        # Create tokens
        tokens = AuthService._create_token_pair(user, session, device_info)

        # Update last login
        from apps.users.services import UserService

        UserService.update_last_login(user=user)

        logger.info(
            "auth.login.success",
            user_id=str(user.id),
            device_type=device_info.device_type,
            is_new_device=is_new_device,
            ip_address=device_info.ip_address,
        )

        # Audit: Successful login
        AuditService.log(
            action=AuditLog.Action.LOGIN_SUCCESS,
            actor=user,
            resource=session,
            request=request,
            details={
                "device_type": device_info.device_type,
                "device_name": device_info.device_name,
                "is_new_device": is_new_device,
            },
        )

        # Audit: Session created (if new device)
        if is_new_device:
            AuditService.log(
                action=AuditLog.Action.SESSION_CREATED,
                actor=user,
                resource=session,
                request=request,
                details={
                    "device_type": device_info.device_type,
                    "device_name": device_info.device_name,
                    "device_id": device_info.device_id,
                },
            )

        # Send new device notification (deferred until transaction commits)
        if is_new_device:
            _user, _di = user, device_info
            transaction.on_commit(
                lambda: AuthService._send_new_login_notification(_user, _di)
            )

        return user, tokens, session

    @staticmethod
    def refresh_tokens(
        *,
        refresh_token: str,
        device_info: DeviceInfo,
        request: HttpRequest | None = None,
    ) -> TokenPair:
        """
        Rotate refresh token and issue new access token.

        Security checks (token reuse detection) run outside the atomic block
        so that logout_all persists even when the method raises an exception.
        The actual token rotation runs inside an atomic block for consistency.

        Args:
            refresh_token: The current refresh token
            device_info: Client device information
            request: HTTP request for audit context (optional)

        Returns:
            New TokenPair

        Raises:
            TokenInvalid: Token not found, revoked, or already rotated
            TokenExpired: Token expired
        """
        # --- Security checks (outside transaction so logout_all persists) ---
        token_hash = RefreshToken.hash_token(refresh_token)
        db_token = (
            RefreshToken.objects.filter(token_hash=token_hash)
            .select_related("user", "session")
            .first()
        )

        if not db_token:
            logger.warning("auth.refresh.failed", reason="token_not_found")
            raise TokenInvalid()

        # Check if revoked
        if db_token.is_revoked:
            # Possible token theft - revoke all user tokens
            logger.warning(
                "auth.refresh.revoked_token_reuse",
                user_id=str(db_token.user_id),
                token_id=str(db_token.id),
            )
            # Audit: Security incident - revoked token reuse
            AuditService.log_failure(
                action=AuditLog.Action.TOKEN_REFRESH,
                reason="revoked_token_reuse",
                actor=db_token.user,
                request=request,
                details={"security_incident": True, "action_taken": "logout_all"},
            )
            AuthService.logout_all(
                user=db_token.user, reason="token_reuse", request=request
            )
            raise TokenInvalid(message="Token has been revoked")

        # Check if already rotated (possible replay attack)
        if db_token.replaced_by:
            logger.warning(
                "auth.refresh.token_replay_detected",
                user_id=str(db_token.user_id),
                token_id=str(db_token.id),
            )
            # Audit: Security incident - token replay
            AuditService.log_failure(
                action=AuditLog.Action.TOKEN_REFRESH,
                reason="token_replay_detected",
                actor=db_token.user,
                request=request,
                details={"security_incident": True, "action_taken": "logout_all"},
            )
            # Token reuse detected - revoke all user tokens for security
            AuthService.logout_all(
                user=db_token.user, reason="token_reuse", request=request
            )
            raise TokenInvalid(message="Token has already been used")

        # Check expiration
        if db_token.expires_at < timezone.now():
            logger.info(
                "auth.refresh.token_expired",
                user_id=str(db_token.user_id),
            )
            raise TokenExpired()

        # Check user status
        if not db_token.user.is_active:
            raise AccountInactive()

        # --- Token rotation (inside transaction for consistency) ---
        with transaction.atomic():
            # Re-fetch with lock to prevent race conditions
            # Note: select_for_update() cannot be combined with
            # select_related() on nullable FKs (causes LEFT OUTER JOIN
            # which PostgreSQL rejects with NotSupportedError).
            db_token = (
                RefreshToken.objects.select_for_update()
                .filter(pk=db_token.pk, is_revoked=False, replaced_by__isnull=True)
                .select_related("user")
                .first()
            )

            if not db_token:
                # Race condition: token was revoked/replaced between checks
                raise TokenInvalid()

            # Get session
            session = getattr(db_token, "session", None)

            # Create new token (rotation)
            new_token, raw_token = RefreshToken.create_token(
                user=db_token.user,
                device_id=device_info.device_id,
                device_info={
                    "type": device_info.device_type,
                    "name": device_info.device_name,
                    "user_agent": device_info.user_agent,
                },
                ip_address=device_info.ip_address,
            )

            # Mark old token as replaced
            db_token.replaced_by = new_token
            db_token.save(update_fields=["replaced_by"])

            # Update session
            if session:
                session.current_token = new_token
                session.last_activity = timezone.now()
                session.ip_address = device_info.ip_address or session.ip_address
                session.save(
                    update_fields=["current_token", "last_activity", "ip_address"]
                )

            # Generate access token
            access_token = AuthService._create_access_token(
                db_token.user, new_token.jti
            )

        jwt_auth = getattr(settings, "JWT_AUTH", {})
        access_lifetime = jwt_auth.get("ACCESS_TOKEN_LIFETIME", 900)
        refresh_lifetime = jwt_auth.get("REFRESH_TOKEN_LIFETIME", 604800)

        logger.info(
            "auth.refresh.success",
            user_id=str(db_token.user_id),
        )

        # Audit: Successful token refresh
        AuditService.log(
            action=AuditLog.Action.TOKEN_REFRESH,
            actor=db_token.user,
            resource=session,
            request=request,
        )

        return TokenPair(
            access_token=access_token,
            refresh_token=raw_token,
            access_expires_in=access_lifetime,
            refresh_expires_in=refresh_lifetime,
        )

    @staticmethod
    def logout(
        *, refresh_token: str, user=None, request: HttpRequest | None = None
    ) -> bool:
        """
        Revoke a single refresh token.

        Args:
            refresh_token: The refresh token to revoke
            user: User performing logout (for audit)
            request: HTTP request for audit context (optional)

        Returns:
            True if token was found and revoked
        """
        token_hash = RefreshToken.hash_token(refresh_token)

        # Get token first to capture user for audit
        db_token = (
            RefreshToken.objects.filter(token_hash=token_hash, is_revoked=False)
            .select_related("user", "session")
            .first()
        )

        if not db_token:
            return False

        # Revoke token
        db_token.is_revoked = True
        db_token.revoked_at = timezone.now()
        db_token.revoked_reason = "logout"
        db_token.save(update_fields=["is_revoked", "revoked_at", "revoked_reason"])

        logger.info("auth.logout.success", user_id=str(db_token.user_id))

        # Audit: Logout
        AuditService.log(
            action=AuditLog.Action.LOGOUT,
            actor=user or db_token.user,
            resource=db_token.session,
            request=request,
        )

        return True

    @staticmethod
    @transaction.atomic
    def logout_all(
        *, user, reason: str = "logout_all", request: HttpRequest | None = None
    ) -> int:
        """
        Revoke all refresh tokens for a user.

        Args:
            user: User to logout
            reason: Reason for logout
            request: HTTP request for audit context (optional)

        Returns:
            Count of revoked tokens
        """
        # Blacklist all active JTIs for immediate access token revocation
        from apps.auth.blacklist import JTIBlacklist

        JTIBlacklist.blacklist_user_tokens(user.id)

        # Revoke all refresh tokens
        count = RefreshToken.objects.filter(user=user, is_revoked=False).update(
            is_revoked=True, revoked_at=timezone.now(), revoked_reason=reason
        )

        # Deactivate all sessions
        DeviceSession.objects.filter(user=user).update(is_active=False)

        logger.info(
            "auth.logout_all",
            user_id=str(user.id),
            tokens_revoked=count,
            reason=reason,
        )

        # Audit: All sessions revoked
        AuditService.log(
            action=AuditLog.Action.ALL_SESSIONS_REVOKED,
            actor=user,
            resource=user,
            request=request,
            details={"sessions_revoked": count, "reason": reason},
        )

        return count

    @staticmethod
    def validate_access_token(token: str) -> Tuple["User", dict]:
        """
        Validate access token and return user.

        Used by JWTAuthentication class.

        Args:
            token: JWT access token

        Returns:
            Tuple of (User, payload dict)

        Raises:
            TokenExpired: Token has expired
            TokenInvalid: Token is invalid or user inactive
        """
        payload = decode_token(token)

        user_id = payload.get("user_id")
        jti = payload.get("jti")
        token_type = payload.get("token_type")

        if not user_id or not jti:
            raise TokenInvalid()

        if token_type != "access":
            raise TokenInvalid(message="Invalid token type")

        # Check JTI blacklist in Redis for immediate revocation
        from apps.auth.blacklist import JTIBlacklist

        if JTIBlacklist.is_blacklisted(jti):
            raise TokenInvalid(message="Token has been revoked")

        # Get user
        user = UserSelector.get_by_id_or_none(user_id=user_id, with_profile=True)
        if not user:
            raise TokenInvalid(message="User not found")

        if not user.is_active:
            raise TokenInvalid(message="User account is deactivated")

        return user, payload

    @staticmethod
    def revoke_session(
        *, user, session_id: str, request: HttpRequest | None = None
    ) -> bool:
        """
        Revoke a specific device session.

        Args:
            user: User who owns the session
            session_id: UUID of the session to revoke
            request: HTTP request for audit context (optional)

        Returns:
            True if session was found and revoked
        """
        try:
            session = DeviceSession.objects.get(
                id=session_id, user=user, is_active=True
            )
        except DeviceSession.DoesNotExist:
            return False

        # Revoke associated token
        if session.current_token:
            session.current_token.revoke(reason="security")
            # Blacklist JTI
            from apps.auth.blacklist import JTIBlacklist

            JTIBlacklist.blacklist(str(session.current_token.jti))

        session.is_active = False
        session.save(update_fields=["is_active"])

        logger.info(
            "auth.session.revoked",
            user_id=str(user.id),
            session_id=session_id,
        )

        # Audit: Session revoked
        AuditService.log(
            action=AuditLog.Action.SESSION_REVOKED,
            actor=user,
            resource=session,
            request=request,
            details={
                "device_type": session.device_type,
                "device_name": session.device_name,
            },
        )

        return True

    # -------------------------------------------------------------------------
    # PRIVATE METHODS
    # -------------------------------------------------------------------------

    @staticmethod
    def _create_access_token(user, jti: uuid.UUID) -> str:
        """Generate JWT access token."""
        jwt_auth = getattr(settings, "JWT_AUTH", {})
        expires_in = jwt_auth.get("ACCESS_TOKEN_LIFETIME", 900)

        return encode_token(
            payload={
                "user_id": str(user.id),
                "jti": str(jti),
                "email": user.email,
                "is_verified": user.is_verified,
                "token_type": "access",
            },
            expires_in=expires_in,
        )

    @staticmethod
    def _create_token_pair(
        user, session: DeviceSession, device_info: DeviceInfo
    ) -> TokenPair:
        """Create access + refresh token pair."""
        # Create refresh token
        refresh_token, raw_refresh = RefreshToken.create_token(
            user=user,
            device_id=device_info.device_id,
            device_info={
                "type": device_info.device_type,
                "name": device_info.device_name,
                "user_agent": device_info.user_agent,
            },
            ip_address=device_info.ip_address,
        )

        # Link to session
        session.current_token = refresh_token
        session.save(update_fields=["current_token"])

        # Create access token
        access_token = AuthService._create_access_token(user, refresh_token.jti)

        jwt_auth = getattr(settings, "JWT_AUTH", {})
        access_lifetime = jwt_auth.get("ACCESS_TOKEN_LIFETIME", 900)
        refresh_lifetime = jwt_auth.get("REFRESH_TOKEN_LIFETIME", 604800)

        return TokenPair(
            access_token=access_token,
            refresh_token=raw_refresh,
            access_expires_in=access_lifetime,
            refresh_expires_in=refresh_lifetime,
        )

    @staticmethod
    def _get_or_create_session(
        user, device_info: DeviceInfo
    ) -> tuple[DeviceSession, bool]:
        """Get or create device session. Returns (session, created) tuple."""
        session, created = DeviceSession.objects.update_or_create(
            user=user,
            device_id=device_info.device_id,
            defaults={
                "device_type": device_info.device_type,
                "device_name": device_info.device_name,
                "user_agent": device_info.user_agent,
                "ip_address": device_info.ip_address,
                "is_active": True,
            },
        )
        return session, created

    @staticmethod
    def _enforce_session_limit(user, current_session: DeviceSession) -> None:
        """
        Enforce max sessions per user.
        Removes oldest sessions if limit exceeded.
        """
        max_sessions = getattr(settings, "AUTH_MAX_SESSIONS_PER_USER", 5)

        active_sessions = (
            DeviceSession.objects.filter(user=user, is_active=True)
            .exclude(id=current_session.id)
            .order_by("-last_activity")
        )

        if active_sessions.count() >= max_sessions:
            # Revoke oldest sessions
            to_revoke = list(active_sessions[max_sessions - 1 :])
            for session in to_revoke:
                if session.current_token:
                    session.current_token.revoke(reason="session_limit")
                session.is_active = False
                session.save(update_fields=["is_active"])

            logger.info(
                "auth.session_limit.enforced",
                extra={
                    "user_id": user.id,
                    "sessions_revoked": len(to_revoke),
                    "max_sessions": max_sessions,
                },
            )

    @staticmethod
    def _send_new_login_notification(user, device_info: DeviceInfo) -> None:
        """Send notification for new device login."""
        try:
            from apps.notifications.services import NotificationService

            NotificationService.send(
                user=user,
                notification_type="new_login",
                context={
                    "device": device_info.device_name or device_info.device_type,
                    "location": "",  # Could derive from IP
                    "ip": device_info.ip_address or "Unknown",
                    "time": timezone.now().isoformat(),
                },
            )
        except Exception as e:
            # Don't fail login due to notification error
            logger.error(
                "auth.notification.failed", extra={"user_id": user.id, "error": str(e)}
            )
