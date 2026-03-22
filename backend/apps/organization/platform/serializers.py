# apps/organization/platform/serializers.py
"""
Platform Serializers - Input validation and output representation.

Design:
- Input serializers: Validate request data (no model binding)
- Output serializers: Format response data (model-based)
"""

from rest_framework import serializers

from apps.core.serializers import BaseInputSerializer, BaseOutputSerializer
from apps.organization.platform.models import PlatformAccount, PlatformProfile

# =============================================================================
# INPUT SERIALIZERS
# =============================================================================


class PlatformConfigureInput(BaseInputSerializer):
    """Input for initial platform configuration."""

    name = serializers.CharField(max_length=255, help_text="Platform name")
    settings = serializers.JSONField(
        required=False, default=dict, help_text="Platform-wide settings"
    )


class PlatformSettingsUpdateInput(BaseInputSerializer):
    """Input for updating platform settings."""

    settings = serializers.JSONField(
        required=False, help_text="Settings to merge with existing"
    )
    open_member_request = serializers.BooleanField(required=False)


class PlatformProfileUpdateInput(BaseInputSerializer):
    """Input for updating platform profile."""

    name = serializers.CharField(max_length=255, required=False)
    tagline = serializers.CharField(max_length=500, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    logo = serializers.ImageField(required=False, allow_null=True)
    favicon = serializers.ImageField(required=False, allow_null=True)
    primary_color = serializers.RegexField(
        regex=r"^#[0-9A-Fa-f]{6}$",
        required=False,
        help_text="Hex color code (e.g., #000000)",
    )
    secondary_color = serializers.RegexField(
        regex=r"^#[0-9A-Fa-f]{6}$",
        required=False,
        help_text="Hex color code (e.g., #ffffff)",
    )
    contact_email = serializers.EmailField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(
        max_length=20, required=False, allow_blank=True
    )
    address = serializers.CharField(required=False, allow_blank=True)
    social_links = serializers.JSONField(required=False)


# =============================================================================
# OUTPUT SERIALIZERS
# =============================================================================


class PlatformProfileOutput(BaseOutputSerializer):
    """Output representation for PlatformProfile."""

    class Meta:
        model = PlatformProfile
        fields = [
            "name",
            "tagline",
            "description",
            "logo",
            "favicon",
            "primary_color",
            "secondary_color",
            "contact_email",
            "contact_phone",
            "address",
            "social_links",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class PlatformAccountOutput(BaseOutputSerializer):
    """Output representation for PlatformAccount."""

    profile = PlatformProfileOutput(read_only=True)

    class Meta:
        model = PlatformAccount
        fields = [
            "id",
            "is_configured",
            "max_members",
            "open_member_request",
            "settings",
            "profile",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class PlatformAccountMinimalOutput(BaseOutputSerializer):
    """Minimal output for PlatformAccount (without nested profile)."""

    class Meta:
        model = PlatformAccount
        fields = [
            "id",
            "is_configured",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
