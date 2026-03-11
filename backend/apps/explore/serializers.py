"""
Explore Serializers — Output representations for search results.

Dedicated serializers for explore endpoints. These are intentionally separate
from the model serializers in users/ and organization/ since explore cards
show a different subset of fields (e.g., search_rank, no settings/audit fields).
"""

from typing import Optional

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.core.serializers import BaseOutputSerializer
from apps.explore.models import SuggestedTag
from apps.organization.business.models import BusinessAccount, BusinessProfile
from apps.users.models import User, UserProfile


# =============================================================================
# Business Search Results
# =============================================================================


class ExploreBusinessProfileOutput(BaseOutputSerializer):
    """Business profile fields shown on search result cards."""

    class Meta:
        model = BusinessProfile
        fields = [
            "display_name",
            "tagline",
            "logo",
            "industry",
            "company_size",
            "tags",
            "website",
            "is_public",
        ]
        read_only_fields = fields


class ExploreBusinessOutput(BaseOutputSerializer):
    """Business search result with profile and search rank."""

    profile = ExploreBusinessProfileOutput(read_only=True)
    is_verified = serializers.SerializerMethodField()
    search_rank = serializers.FloatField(read_only=True, default=0.0)

    class Meta:
        model = BusinessAccount
        fields = [
            "id",
            "slug",
            "legal_name",
            "country",
            "city",
            "business_type",
            "is_platform_branch",
            "open_member_request",
            "is_verified",
            "profile",
            "search_rank",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.BooleanField())
    def get_is_verified(self, obj) -> bool:
        from apps.core.constants import VerificationStatus
        return obj.verification_status == VerificationStatus.VERIFIED


# =============================================================================
# User Search Results
# =============================================================================


class ExploreUserProfileOutput(BaseOutputSerializer):
    """User profile fields shown on search result cards."""

    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            "first_name",
            "last_name",
            "bio",
            "avatar_url",
            "country",
            "city",
            "tags",
            "is_public",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_avatar_url(self, obj) -> Optional[str]:
        if obj.avatar:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None


class ExploreUserOutput(BaseOutputSerializer):
    """User search result with profile and search rank."""

    profile = ExploreUserProfileOutput(read_only=True)
    display_name = serializers.SerializerMethodField()
    search_rank = serializers.FloatField(read_only=True, default=0.0)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "is_verified",
            "display_name",
            "profile",
            "search_rank",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.CharField())
    def get_display_name(self, obj) -> str:
        if hasattr(obj, "profile"):
            return obj.profile.display_name
        return obj.email.split("@")[0]


# =============================================================================
# Combined (All tab)
# =============================================================================


class ExploreCombinedOutput(serializers.Serializer):
    """Response for the combined 'All' tab."""

    users = ExploreUserOutput(many=True)
    businesses = ExploreBusinessOutput(many=True)
    users_count = serializers.IntegerField()
    businesses_count = serializers.IntegerField()


# =============================================================================
# Tag Suggestions
# =============================================================================


class SuggestedTagOutput(BaseOutputSerializer):
    """Tag autocomplete suggestion."""

    class Meta:
        model = SuggestedTag
        fields = [
            "id",
            "name",
            "slug",
            "category",
            "usage_count",
        ]
        read_only_fields = fields


# =============================================================================
# City List
# =============================================================================


class CityListOutput(serializers.Serializer):
    """City list response for a given country."""

    country = serializers.CharField()
    cities = serializers.ListField(child=serializers.CharField())
