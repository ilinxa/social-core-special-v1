# apps/organization/business/serializers.py
"""
Business Serializers - Input validation and output representation.

Design:
- Input serializers: Validate request data (no model binding)
- Output serializers: Format response data (model-based)
"""

from rest_framework import serializers

from apps.core.constants import BusinessType, CompanySize
from apps.core.serializers import BaseInputSerializer, BaseOutputSerializer
from apps.core.visibility.serializers import VisibilityAwareSerializerMixin
from apps.organization.business.models import BusinessAccount, BusinessProfile

# =============================================================================
# INPUT SERIALIZERS
# =============================================================================


class BusinessCreateInput(BaseInputSerializer):
    """Input for creating a business."""

    legal_name = serializers.CharField(max_length=255, help_text="Legal business name")
    country = serializers.CharField(
        max_length=2,
        help_text="ISO 3166-1 alpha-2 country code",
    )
    slug = serializers.SlugField(
        max_length=100,
        required=False,
        allow_blank=True,
        help_text="URL slug (auto-generated if not provided)",
    )
    business_type = serializers.ChoiceField(
        choices=BusinessType.choices,
        required=False,
        help_text="Type of business",
    )
    registration_number = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )
    tax_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    legal_address = serializers.CharField(required=False, allow_blank=True)
    display_name = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Display name for profile (defaults to legal_name)",
    )


class BusinessUpdateInput(BaseInputSerializer):
    """Input for updating a business."""

    legal_name = serializers.CharField(max_length=255, required=False)
    registration_number = serializers.CharField(
        max_length=100, required=False, allow_blank=True
    )
    tax_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    country = serializers.CharField(max_length=2, required=False)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    legal_address = serializers.CharField(required=False, allow_blank=True)
    business_type = serializers.ChoiceField(
        choices=BusinessType.choices, required=False
    )
    settings = serializers.JSONField(required=False)
    open_member_request = serializers.BooleanField(required=False)

    def validate_city(self, value):
        """Validate city against predefined city list when country is provided."""
        if not value:
            return value
        country = self.initial_data.get("country", "")
        if country:
            from apps.core.utils.city_data import is_valid_city

            if not is_valid_city(country, value):
                raise serializers.ValidationError(
                    f'"{value}" is not a valid city for country "{country}".'
                )
        return value


class BusinessSlugUpdateInput(BaseInputSerializer):
    """Input for changing business slug."""

    slug = serializers.SlugField(max_length=100, help_text="New URL slug")


class BusinessSuspendInput(BaseInputSerializer):
    """Input for suspending a business."""

    reason = serializers.CharField(help_text="Reason for suspension")


class BusinessProfileUpdateInput(BaseInputSerializer):
    """Input for updating business profile."""

    display_name = serializers.CharField(max_length=255, required=False)
    tagline = serializers.CharField(max_length=500, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    logo = serializers.ImageField(required=False, allow_null=True)
    cover_image = serializers.ImageField(required=False, allow_null=True)
    website = serializers.URLField(required=False, allow_blank=True)
    contact_email = serializers.EmailField(required=False, allow_blank=True)
    contact_phone = serializers.CharField(
        max_length=20, required=False, allow_blank=True
    )
    industry = serializers.CharField(max_length=100, required=False, allow_blank=True)
    company_size = serializers.ChoiceField(
        choices=CompanySize.choices, required=False, allow_blank=True
    )
    founded_year = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1800,
        max_value=2100,
    )
    social_links = serializers.JSONField(required=False)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        max_length=20,
    )
    is_public = serializers.BooleanField(required=False)


# =============================================================================
# OUTPUT SERIALIZERS
# =============================================================================


class BusinessProfileOutput(VisibilityAwareSerializerMixin, BaseOutputSerializer):
    """Output representation for BusinessProfile.

    Uses VisibilityAwareSerializerMixin to filter T2 fields (contact_email,
    contact_phone) based on viewer access level.
    """

    visibility_registry = "business_profile"

    class Meta:
        model = BusinessProfile
        fields = [
            "display_name",
            "tagline",
            "description",
            "logo",
            "cover_image",
            "website",
            "contact_email",
            "contact_phone",
            "industry",
            "company_size",
            "founded_year",
            "social_links",
            "tags",
            "is_public",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class BusinessAccountOutput(VisibilityAwareSerializerMixin, BaseOutputSerializer):
    """Output representation for BusinessAccount.

    Uses VisibilityAwareSerializerMixin to filter T3 fields (registration_number,
    tax_id, legal_address, settings, max_members) based on viewer access + RBAC.
    """

    visibility_registry = "business_account"

    profile = BusinessProfileOutput(read_only=True)
    business_type_display = serializers.CharField(
        source="get_business_type_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    verification_status_display = serializers.CharField(
        source="get_verification_status_display", read_only=True
    )

    class Meta:
        model = BusinessAccount
        fields = [
            "id",
            "slug",
            "legal_name",
            "registration_number",
            "tax_id",
            "country",
            "city",
            "legal_address",
            "business_type",
            "business_type_display",
            "status",
            "status_display",
            "verification_status",
            "verification_status_display",
            "verified_at",
            "is_platform_branch",
            "max_members",
            "open_member_request",
            "settings",
            "profile",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class BusinessAccountListOutput(BaseOutputSerializer):
    """Minimal output for business listing."""

    profile = BusinessProfileOutput(read_only=True)

    class Meta:
        model = BusinessAccount
        fields = [
            "id",
            "slug",
            "legal_name",
            "country",
            "city",
            "business_type",
            "status",
            "verification_status",
            "is_platform_branch",
            "max_members",
            "open_member_request",
            "profile",
            "created_at",
        ]
        read_only_fields = fields


class BusinessAccountMinimalOutput(BaseOutputSerializer):
    """Minimal output without profile (for nested use)."""

    class Meta:
        model = BusinessAccount
        fields = [
            "id",
            "slug",
            "legal_name",
            "status",
        ]
        read_only_fields = fields
