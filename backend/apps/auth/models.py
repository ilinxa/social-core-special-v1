"""
Auth Models
===========
Database models for authentication: tokens, sessions, and OAuth connections.

Models:
    - RefreshToken: JWT refresh tokens (stored as hash)
    - DeviceSession: User device/session tracking
    - EmailVerificationToken: Email verification (magic link + code)
    - PasswordResetToken: Password reset tokens
    - OAuthConnection: OAuth provider connections

Security:
    - Refresh tokens stored as SHA256 hash only
    - Single-use tokens with rotation tracking
    - Device sessions for management UI
"""

import hashlib
import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.feature_config import feature_config
from apps.core.models import TimeStampedModel, UUIDModel

# =============================================================================
# REFRESH TOKEN
# =============================================================================


class RefreshToken(UUIDModel, TimeStampedModel):
    """
    Refresh tokens for JWT authentication.

    Security:
        - Token value is NEVER stored - only SHA256 hash
        - Single-use: rotated on every refresh
        - Linked list: replaced_by tracks rotation chain
        - Reuse detection: if replaced token is used, revoke all
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="refresh_tokens",
    )

    # Token identification (hash, not actual token)
    token_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="SHA256 hash of the actual token",
    )

    # JWT ID - included in access tokens to enable invalidation
    jti = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
        help_text="JWT ID for access token invalidation",
    )

    # Expiration
    expires_at = models.DateTimeField(db_index=True)

    # Device/session info
    device_id = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Client-provided device identifier",
    )
    device_info = models.JSONField(default=dict, help_text="User agent, platform, etc.")
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    # Status
    is_revoked = models.BooleanField(default=False, db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class RevokedReason(models.TextChoices):
        LOGOUT = "logout", "User Logout"
        LOGOUT_ALL = "logout_all", "Logout All Sessions"
        PASSWORD_CHANGE = "password_change", "Password Changed"
        SESSION_LIMIT = "session_limit", "Session Limit Exceeded"
        SECURITY = "security", "Security Event"
        ADMIN = "admin", "Admin Revocation"
        TOKEN_REUSE = "token_reuse", "Token Reuse Detected"

    revoked_reason = models.CharField(
        max_length=50,
        blank=True,
        choices=RevokedReason.choices,
    )

    # Rotation tracking
    replaced_by = models.OneToOneField(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replaces",
        help_text="The new token that replaced this one",
    )

    class Meta:
        db_table = "auth_refresh_tokens"
        verbose_name = "refresh token"
        verbose_name_plural = "refresh tokens"
        indexes = [
            models.Index(fields=["user", "is_revoked", "expires_at"]),
            models.Index(fields=["device_id", "user"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        status = "revoked" if self.is_revoked else "active"
        return f"RefreshToken({self.user_id}, {status})"

    @property
    def is_valid(self) -> bool:
        """Check if token can be used."""
        return (
            not self.is_revoked
            and self.expires_at > timezone.now()
            and self.replaced_by is None
        )

    @staticmethod
    def hash_token(token: str) -> str:
        """Hash a token for storage."""
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    def create_token(
        cls, user, device_id: str = "", device_info: dict = None, ip_address: str = None
    ) -> tuple["RefreshToken", str]:
        """
        Create a new refresh token.

        Returns:
            Tuple[RefreshToken, str]: The model instance and the raw token value
        """
        # Generate random token
        raw_token = secrets.token_urlsafe(32)

        # Get lifetime from settings
        lifetime_seconds = getattr(settings, "JWT_AUTH", {}).get(
            "REFRESH_TOKEN_LIFETIME", 604800
        )  # Default 7 days

        # Create instance with hash
        instance = cls.objects.create(
            user=user,
            token_hash=cls.hash_token(raw_token),
            expires_at=timezone.now() + timedelta(seconds=lifetime_seconds),
            device_id=device_id,
            device_info=device_info or {},
            ip_address=ip_address,
        )

        return instance, raw_token

    def revoke(self, reason: str = "logout") -> None:
        """Revoke this token."""
        self.is_revoked = True
        self.revoked_at = timezone.now()
        self.revoked_reason = reason
        self.save(update_fields=["is_revoked", "revoked_at", "revoked_reason"])


# =============================================================================
# DEVICE SESSION
# =============================================================================


class DeviceSession(UUIDModel, TimeStampedModel):
    """
    Track active device sessions for management UI.

    Users can view and revoke their active sessions from settings.
    """

    class DeviceType(models.TextChoices):
        WEB = "web", "Web Browser"
        IOS = "ios", "iOS App"
        ANDROID = "android", "Android App"
        DESKTOP = "desktop", "Desktop App"
        UNKNOWN = "unknown", "Unknown"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="device_sessions",
    )

    device_id = models.CharField(max_length=255, db_index=True)
    device_name = models.CharField(max_length=255, blank=True)
    device_type = models.CharField(
        max_length=20, choices=DeviceType.choices, default=DeviceType.UNKNOWN
    )

    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True)

    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, db_index=True)

    # Link to current refresh token
    current_token = models.OneToOneField(
        RefreshToken,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="session",
    )

    class Meta:
        db_table = "auth_device_sessions"
        verbose_name = "device session"
        verbose_name_plural = "device sessions"
        indexes = [
            models.Index(fields=["user", "is_active", "last_activity"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "device_id"],
                name="auth_device_session_user_device_uniq",
            ),
        ]
        ordering = ["-last_activity"]

    def __str__(self):
        return f"{self.device_name or self.device_type} - {self.user_id}"


# =============================================================================
# EMAIL VERIFICATION TOKEN
# =============================================================================


class EmailVerificationToken(TimeStampedModel):
    """
    Tokens for email verification.

    Supports both magic link (UUID) and 6-digit code.

    Constraints:
        - Only one active (unused, unexpired) token per user
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="verification_tokens",
    )

    # Magic link token
    token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)

    # 6-digit code
    code = models.CharField(max_length=6, db_index=True)

    # Email being verified (might differ from user.email for email change)
    email = models.EmailField()

    expires_at = models.DateTimeField()

    is_used = models.BooleanField(default=False, db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "auth_verification_tokens"
        verbose_name = "email verification token"
        verbose_name_plural = "email verification tokens"
        indexes = [
            models.Index(fields=["user", "is_used", "expires_at"]),
            models.Index(fields=["code", "email", "is_used"]),
        ]
        constraints = [
            # Only one active (unused) verification token per user
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_used=False),
                name="one_active_verification_token_per_user",
            ),
        ]

    def __str__(self):
        return f"Verification({self.user_id}, {'used' if self.is_used else 'pending'})"

    @property
    def is_valid(self) -> bool:
        """Check if token is valid (not used and not expired)."""
        return not self.is_used and self.expires_at > timezone.now()

    @staticmethod
    def generate_code() -> str:
        """Generate 6-digit verification code."""
        return "".join(secrets.choice("0123456789") for _ in range(6))

    @classmethod
    def create_for_user(cls, user, email: str = None) -> "EmailVerificationToken":
        """
        Create verification token for user.

        Invalidates any existing active tokens first.
        """
        # Invalidate existing tokens
        cls.objects.filter(user=user, is_used=False).update(is_used=True)

        expiry_minutes = feature_config.get_value(
            "auth.verification.expiry_minutes", 15
        )
        return cls.objects.create(
            user=user,
            email=email or user.email,
            code=cls.generate_code(),
            expires_at=timezone.now() + timedelta(minutes=expiry_minutes),
        )

    def mark_used(self) -> None:
        """Mark token as used."""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=["is_used", "used_at"])


# =============================================================================
# PASSWORD RESET TOKEN
# =============================================================================


class PasswordResetToken(TimeStampedModel):
    """
    Tokens for password reset.

    Constraints:
        - Only one active (unused, unexpired) reset token per user
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )

    token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    expires_at = models.DateTimeField()

    is_used = models.BooleanField(default=False, db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "auth_password_reset_tokens"
        verbose_name = "password reset token"
        verbose_name_plural = "password reset tokens"
        indexes = [
            models.Index(fields=["token", "is_used"]),
        ]
        constraints = [
            # Only one active (unused) reset token per user
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_used=False),
                name="one_active_password_reset_token_per_user",
            ),
        ]

    def __str__(self):
        return f"PasswordReset({self.user_id}, {'used' if self.is_used else 'pending'})"

    @property
    def is_valid(self) -> bool:
        """Check if token is valid."""
        return not self.is_used and self.expires_at > timezone.now()

    @classmethod
    def create_for_user(cls, user, ip_address: str = None) -> "PasswordResetToken":
        """
        Create password reset token for user.

        Invalidates any existing active tokens first.
        """
        # Invalidate existing tokens
        cls.objects.filter(user=user, is_used=False).update(is_used=True)

        expiry_minutes = feature_config.get_value(
            "auth.password_reset.expiry_minutes", 60
        )
        return cls.objects.create(
            user=user,
            expires_at=timezone.now() + timedelta(minutes=expiry_minutes),
            ip_address=ip_address,
        )

    def mark_used(self) -> None:
        """Mark token as used."""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=["is_used", "used_at"])


# =============================================================================
# GOVERNANCE OTP TOKEN
# =============================================================================


class GovernanceOTPToken(TimeStampedModel):
    """
    Short-lived OTP tokens for governance console step-up authentication.

    Used when a user with global permissions needs to access the gconsole.
    Supports email-based 6-digit code verification as an alternative to
    password re-entry.

    Constraints:
        - Only one active (unused, unexpired) OTP per user
        - Max attempts tracked to prevent brute-force
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="governance_otp_tokens",
    )

    code = models.CharField(max_length=6, db_index=True)
    email = models.EmailField()
    expires_at = models.DateTimeField()

    is_used = models.BooleanField(default=False, db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "auth_governance_otp"
        verbose_name = "governance OTP token"
        verbose_name_plural = "governance OTP tokens"
        indexes = [
            models.Index(fields=["user", "is_used", "expires_at"]),
            models.Index(fields=["code", "email", "is_used"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_used=False),
                name="one_active_governance_otp_per_user",
            ),
        ]

    def __str__(self):
        return f"GovernanceOTP({self.user_id}, {'used' if self.is_used else 'pending'})"

    @property
    def is_valid(self) -> bool:
        """Check if OTP is valid (not used and not expired)."""
        return not self.is_used and self.expires_at > timezone.now()

    @property
    def is_max_attempts_reached(self) -> bool:
        """Check if max verification attempts have been exceeded."""
        max_attempts = feature_config.get_value("auth.governance.otp_max_attempts", 5)
        return self.attempts >= max_attempts

    @staticmethod
    def generate_code(length: int = None) -> str:
        """Generate a random numeric OTP code."""
        code_length = length or feature_config.get_value(
            "auth.governance.otp_code_length", 6
        )
        return "".join(secrets.choice("0123456789") for _ in range(code_length))

    @classmethod
    def create_for_user(cls, user) -> "GovernanceOTPToken":
        """
        Create governance OTP for user.

        Invalidates any existing active OTPs first.
        """
        cls.objects.filter(user=user, is_used=False).update(is_used=True)

        expiry_seconds = feature_config.get_value(
            "auth.governance.otp_expiry_seconds", 300
        )
        return cls.objects.create(
            user=user,
            email=user.email,
            code=cls.generate_code(),
            expires_at=timezone.now() + timedelta(seconds=expiry_seconds),
        )

    def increment_attempts(self) -> None:
        """Increment failed verification attempts."""
        self.attempts += 1
        self.save(update_fields=["attempts"])

    def mark_used(self) -> None:
        """Mark OTP as used."""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=["is_used", "used_at"])


# =============================================================================
# OAUTH CONNECTION
# =============================================================================


class OAuthConnection(TimeStampedModel):
    """
    OAuth provider connections for social login.

    Allows users to link their accounts with OAuth providers.
    """

    class Provider(models.TextChoices):
        GOOGLE = "google", "Google"
        APPLE = "apple", "Apple"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="oauth_connections",
    )

    provider = models.CharField(max_length=20, choices=Provider.choices, db_index=True)

    # Provider's unique user ID
    provider_uid = models.CharField(max_length=255)

    # Provider tokens (encrypted in production via custom field if needed)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)

    # Provider profile data
    provider_data = models.JSONField(
        default=dict, help_text="Raw data from provider (name, email, etc.)"
    )

    # Email from provider (for linking logic)
    provider_email = models.EmailField(blank=True)

    class Meta:
        db_table = "auth_oauth_connections"
        verbose_name = "OAuth connection"
        verbose_name_plural = "OAuth connections"
        indexes = [
            models.Index(fields=["user", "provider"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_uid"],
                name="auth_oauth_provider_uid_uniq",
            ),
        ]

    def __str__(self):
        return f"{self.provider} - {self.user_id}"
