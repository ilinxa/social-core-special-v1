"""
Auth Admin
==========
Django admin configuration for authentication models.
"""

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from apps.auth.models import (
    DeviceSession,
    EmailVerificationToken,
    OAuthConnection,
    PasswordResetToken,
    RefreshToken,
)


@admin.register(RefreshToken)
class RefreshTokenAdmin(admin.ModelAdmin):
    """Admin for refresh tokens."""

    list_display = [
        "id",
        "user_email",
        "device_id",
        "status_display",
        "expires_at",
        "created_at",
    ]
    list_filter = [
        "is_revoked",
        "revoked_reason",
        "created_at",
    ]
    search_fields = [
        "user__email",
        "device_id",
    ]
    readonly_fields = [
        "id",
        "token_hash",
        "jti",
        "created_at",
        "updated_at",
    ]
    raw_id_fields = ["user", "replaced_by"]
    ordering = ["-created_at"]

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = "User"

    def status_display(self, obj):
        if obj.is_revoked:
            return format_html(
                '<span style="color: red;">Revoked ({})</span>', obj.revoked_reason
            )
        elif obj.replaced_by:
            return format_html('<span style="color: orange;">Rotated</span>')
        elif obj.expires_at < timezone.now():
            return format_html('<span style="color: gray;">Expired</span>')
        else:
            return format_html('<span style="color: green;">Active</span>')

    status_display.short_description = "Status"

    def has_add_permission(self, request):
        return False  # Tokens should not be created manually


@admin.register(DeviceSession)
class DeviceSessionAdmin(admin.ModelAdmin):
    """Admin for device sessions."""

    list_display = [
        "id",
        "user_email",
        "device_name",
        "device_type",
        "ip_address",
        "is_active",
        "last_activity",
    ]
    list_filter = [
        "is_active",
        "device_type",
        "created_at",
    ]
    search_fields = [
        "user__email",
        "device_name",
        "device_id",
        "ip_address",
    ]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
    ]
    raw_id_fields = ["user", "current_token"]
    ordering = ["-last_activity"]

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = "User"

    actions = ["revoke_sessions"]

    @admin.action(description="Revoke selected sessions")
    def revoke_sessions(self, request, queryset):
        for session in queryset.filter(is_active=True):
            if session.current_token:
                session.current_token.revoke(reason="admin")
            session.is_active = False
            session.save(update_fields=["is_active"])


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    """Admin for email verification tokens."""

    list_display = [
        "user_email",
        "email",
        "code",
        "status_display",
        "expires_at",
        "created_at",
    ]
    list_filter = [
        "is_used",
        "created_at",
    ]
    search_fields = [
        "user__email",
        "email",
        "code",
    ]
    readonly_fields = [
        "token",
        "code",
        "created_at",
        "updated_at",
    ]
    raw_id_fields = ["user"]
    ordering = ["-created_at"]

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = "User"

    def status_display(self, obj):
        if obj.is_used:
            return format_html('<span style="color: green;">Used</span>')
        elif obj.expires_at < timezone.now():
            return format_html('<span style="color: gray;">Expired</span>')
        else:
            return format_html('<span style="color: blue;">Pending</span>')

    status_display.short_description = "Status"


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    """Admin for password reset tokens."""

    list_display = [
        "user_email",
        "status_display",
        "ip_address",
        "expires_at",
        "created_at",
    ]
    list_filter = [
        "is_used",
        "created_at",
    ]
    search_fields = [
        "user__email",
        "ip_address",
    ]
    readonly_fields = [
        "token",
        "created_at",
        "updated_at",
    ]
    raw_id_fields = ["user"]
    ordering = ["-created_at"]

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = "User"

    def status_display(self, obj):
        if obj.is_used:
            return format_html('<span style="color: green;">Used</span>')
        elif obj.expires_at < timezone.now():
            return format_html('<span style="color: gray;">Expired</span>')
        else:
            return format_html('<span style="color: blue;">Pending</span>')

    status_display.short_description = "Status"


@admin.register(OAuthConnection)
class OAuthConnectionAdmin(admin.ModelAdmin):
    """Admin for OAuth connections."""

    list_display = [
        "user_email",
        "provider",
        "provider_email",
        "created_at",
    ]
    list_filter = [
        "provider",
        "created_at",
    ]
    search_fields = [
        "user__email",
        "provider_email",
        "provider_uid",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
    ]
    raw_id_fields = ["user"]
    ordering = ["-created_at"]

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = "User"
