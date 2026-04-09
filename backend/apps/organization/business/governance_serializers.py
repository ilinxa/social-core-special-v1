# apps/organization/business/governance_serializers.py
"""
Governance Serializers - Input/output for governance console endpoints.

These serializers provide governance-specific views of business data,
including fields hidden from public APIs (member_count, created_by email).
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.core.serializers import BaseInputSerializer, BaseOutputSerializer
from apps.organization.business.models import BusinessAccount
from apps.organization.business.serializers import BusinessProfileOutput

User = get_user_model()


class GovernanceBusinessListOutput(BaseOutputSerializer):
    """List output for governance — includes fields hidden from public."""

    profile = BusinessProfileOutput(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    verification_status_display = serializers.CharField(
        source="get_verification_status_display", read_only=True
    )
    business_type_display = serializers.CharField(
        source="get_business_type_display", read_only=True
    )
    member_count = serializers.IntegerField(read_only=True)
    created_by_email = serializers.SerializerMethodField()

    class Meta:
        model = BusinessAccount
        fields = [
            "id",
            "slug",
            "legal_name",
            "country",
            "city",
            "business_type",
            "business_type_display",
            "status",
            "status_display",
            "verification_status",
            "verification_status_display",
            "is_platform_branch",
            "member_count",
            "created_by_email",
            "profile",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_created_by_email(self, obj):
        if hasattr(obj, "created_by") and obj.created_by:
            return obj.created_by.email
        return None


class GovernanceBusinessDetailOutput(BaseOutputSerializer):
    """Detail output with governance-specific fields."""

    profile = BusinessProfileOutput(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    verification_status_display = serializers.CharField(
        source="get_verification_status_display", read_only=True
    )
    business_type_display = serializers.CharField(
        source="get_business_type_display", read_only=True
    )
    member_count = serializers.IntegerField(read_only=True)
    owner_email = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()

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
            "member_count",
            "owner_email",
            "owner_name",
            "profile",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_owner_email(self, obj):
        owner = self._get_owner(obj)
        return owner.email if owner else None

    def get_owner_name(self, obj):
        owner = self._get_owner(obj)
        if not owner:
            return None
        return owner.get_full_name() or owner.username

    def _get_owner(self, obj):
        if hasattr(obj, "_owner"):
            return obj._owner
        from apps.core.constants import AccountType
        from apps.rbac.selectors import MembershipSelector

        membership = MembershipSelector.get_owner_membership(
            account_type=AccountType.BUSINESS,
            account_id=obj.id,
        )
        owner = membership.user if membership else None
        obj._owner = owner
        return owner


class GovernanceSuspendInput(BaseInputSerializer):
    """Input for governance-initiated business suspension."""

    reason = serializers.CharField(required=True, max_length=1000)


class GovernanceTransferOwnershipInput(BaseInputSerializer):
    """Input for governance-initiated forced ownership transfer."""

    new_owner_id = serializers.UUIDField(required=True)
    reason = serializers.CharField(required=False, max_length=1000, allow_blank=True)
