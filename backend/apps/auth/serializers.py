"""
Auth Serializers
================
Serializers for authentication API endpoints.

Categories:
    - Registration and login
    - Token management
    - Email verification
    - Password management
    - Session management
    - OAuth
"""

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.auth.models import DeviceSession

# =============================================================================
# REGISTRATION & LOGIN
# =============================================================================


class RegisterSerializer(serializers.Serializer):
    """Registration input."""

    email = serializers.EmailField(help_text="User's email address")
    username = serializers.RegexField(
        regex=r"^[a-zA-Z0-9_]{5,30}$",
        help_text="Username (5-30 alphanumeric characters or underscores)",
    )
    password = serializers.CharField(
        min_length=8, write_only=True, help_text="Password (min 8 characters)"
    )
    referred_by = serializers.CharField(
        required=False, allow_blank=True, help_text="Referral code (optional)"
    )

    # Device info (optional, for session tracking)
    device_id = serializers.CharField(
        required=False, default="", help_text="Unique device identifier"
    )
    device_type = serializers.ChoiceField(
        choices=["web", "ios", "android", "desktop", "unknown"],
        required=False,
        default="unknown",
        help_text="Device type",
    )
    device_name = serializers.CharField(
        required=False, default="", help_text="Device name (e.g., 'Chrome on Windows')"
    )


class LoginSerializer(serializers.Serializer):
    """Login input."""

    email = serializers.EmailField(help_text="User's email address")
    password = serializers.CharField(write_only=True, help_text="Password")

    # Device info
    device_id = serializers.CharField(
        required=False, default="", help_text="Unique device identifier"
    )
    device_type = serializers.ChoiceField(
        choices=["web", "ios", "android", "desktop", "unknown"],
        required=False,
        default="unknown",
        help_text="Device type",
    )
    device_name = serializers.CharField(
        required=False, default="", help_text="Device name"
    )


class TokenResponseSerializer(serializers.Serializer):
    """Token pair response."""

    access_token = serializers.CharField(help_text="JWT access token")
    refresh_token = serializers.CharField(
        required=False,  # Not included for web clients (in cookie)
        help_text="Refresh token (only for mobile clients)",
    )
    access_expires_in = serializers.IntegerField(
        help_text="Access token lifetime in seconds"
    )
    refresh_expires_in = serializers.IntegerField(
        help_text="Refresh token lifetime in seconds"
    )
    token_type = serializers.CharField(default="Bearer", help_text="Token type")


class AuthResponseSerializer(serializers.Serializer):
    """Full authentication response."""

    user = serializers.SerializerMethodField()
    tokens = TokenResponseSerializer()
    is_new_user = serializers.BooleanField(required=False, default=False)

    @extend_schema_field(serializers.DictField())
    def get_user(self, obj):
        from apps.users.serializers import UserOutputSerializer

        return UserOutputSerializer(obj["user"]).data


# =============================================================================
# TOKEN MANAGEMENT
# =============================================================================


class RefreshTokenSerializer(serializers.Serializer):
    """Refresh token input."""

    refresh_token = serializers.CharField(
        required=False, help_text="Refresh token"  # Can be in cookie for web clients
    )

    # Device info for updated session
    device_id = serializers.CharField(
        required=False, default="", help_text="Device identifier"
    )
    device_type = serializers.ChoiceField(
        choices=["web", "ios", "android", "desktop", "unknown"],
        required=False,
        default="unknown",
    )
    device_name = serializers.CharField(required=False, default="")


class LogoutSerializer(serializers.Serializer):
    """Logout input."""

    refresh_token = serializers.CharField(
        required=False, help_text="Refresh token to revoke"  # Can be in cookie
    )


# =============================================================================
# EMAIL VERIFICATION
# =============================================================================


class VerifyEmailCodeSerializer(serializers.Serializer):
    """Email verification with code."""

    email = serializers.EmailField(help_text="Email address to verify")
    code = serializers.CharField(
        min_length=6, max_length=6, help_text="6-digit verification code"
    )


class VerifyEmailTokenSerializer(serializers.Serializer):
    """Email verification with magic link token (URL param)."""

    pass  # Token is in URL


class ResendVerificationSerializer(serializers.Serializer):
    """Resend verification email."""

    email = serializers.EmailField(help_text="Email address to send verification to")


# =============================================================================
# PASSWORD MANAGEMENT
# =============================================================================


class PasswordResetRequestSerializer(serializers.Serializer):
    """Request password reset."""

    email = serializers.EmailField(help_text="Email address for password reset")


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Confirm password reset with new password."""

    token = serializers.UUIDField(help_text="Password reset token")
    new_password = serializers.CharField(
        min_length=8, write_only=True, help_text="New password (min 8 characters)"
    )


class PasswordChangeSerializer(serializers.Serializer):
    """Change password (authenticated)."""

    current_password = serializers.CharField(
        write_only=True, help_text="Current password"
    )
    new_password = serializers.CharField(
        min_length=8, write_only=True, help_text="New password (min 8 characters)"
    )


# =============================================================================
# SESSION MANAGEMENT
# =============================================================================


class DeviceSessionSerializer(serializers.ModelSerializer):
    """Device session output."""

    is_current = serializers.SerializerMethodField()

    class Meta:
        model = DeviceSession
        fields = [
            "id",
            "device_id",
            "device_name",
            "device_type",
            "ip_address",
            "location",
            "last_activity",
            "is_active",
            "is_current",
            "created_at",
        ]

    @extend_schema_field(serializers.BooleanField())
    def get_is_current(self, obj) -> bool:
        """Check if this is the current session."""
        request = self.context.get("request")
        if not request or not hasattr(request, "auth"):
            return False
        # Compare JTI from access token with session's token
        payload = request.auth
        if payload and obj.current_token:
            return str(obj.current_token.jti) == payload.get("jti")
        return False


# =============================================================================
# OAUTH
# =============================================================================


class OAuthInitSerializer(serializers.Serializer):
    """OAuth initialization input."""

    redirect_to = serializers.CharField(
        required=False, help_text="URL to redirect to after OAuth"
    )

    def validate_redirect_to(self, value):
        if not value:
            return value
        from urllib.parse import urlparse

        from django.conf import settings

        allowed_origins = getattr(
            settings, "ALLOWED_REDIRECT_ORIGINS", [settings.FRONTEND_URL]
        )
        parsed = urlparse(value)
        if not parsed.scheme or not parsed.netloc:
            raise serializers.ValidationError("Must be an absolute URL.")
        origin = f"{parsed.scheme}://{parsed.netloc}"
        for allowed in allowed_origins:
            ap = urlparse(allowed)
            if origin == f"{ap.scheme}://{ap.netloc}":
                return value
        raise serializers.ValidationError("Redirect URL not in allowed origins.")

    # Device info
    device_id = serializers.CharField(required=False, default="")
    device_type = serializers.ChoiceField(
        choices=["web", "ios", "android", "desktop", "unknown"],
        required=False,
        default="unknown",
    )
    device_name = serializers.CharField(required=False, default="")


class OAuthInitResponseSerializer(serializers.Serializer):
    """OAuth initialization response."""

    authorization_url = serializers.URLField(
        help_text="URL to redirect user to for OAuth"
    )


class OAuthCallbackSerializer(serializers.Serializer):
    """OAuth callback input."""

    code = serializers.CharField(help_text="Authorization code")
    state = serializers.CharField(help_text="State parameter for CSRF protection")
    # For Apple: user data is only sent on first authorization
    user = serializers.CharField(
        required=False, help_text="User data (Apple only, first sign-in)"
    )


# =============================================================================
# COMMON RESPONSES
# =============================================================================


class MessageSerializer(serializers.Serializer):
    """Simple message response."""

    message = serializers.CharField()


class LogoutAllResponseSerializer(serializers.Serializer):
    """Response for logout all endpoint."""

    message = serializers.CharField()
    sessions_revoked = serializers.IntegerField(
        help_text="Number of sessions that were revoked"
    )


class ErrorSerializer(serializers.Serializer):
    """Error response."""

    message = serializers.CharField()
    code = serializers.CharField()
    details = serializers.DictField(required=False)


# =============================================================================
# GOVERNANCE STEP-UP AUTH
# =============================================================================


class GovernancePasswordAuthSerializer(serializers.Serializer):
    """Governance step-up auth via password re-entry."""

    password = serializers.CharField(write_only=True, help_text="Current password")


class GovernanceOTPVerifySerializer(serializers.Serializer):
    """Governance step-up auth via email OTP code."""

    code = serializers.CharField(
        max_length=6, min_length=6, help_text="6-digit OTP code"
    )


class GovernanceTokenResponseSerializer(serializers.Serializer):
    """Governance token response (no refresh token)."""

    access = serializers.CharField(help_text="Governance-scoped JWT")
    expires_in = serializers.IntegerField(help_text="Token lifetime in seconds")
