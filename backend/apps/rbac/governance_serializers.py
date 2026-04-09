# apps/rbac/governance_serializers.py
"""
Governance Member Serializers - Input/output for governance console member endpoints.

These serializers provide governance-specific views of membership data,
including cross-account context (account name, slug) in the output.
"""

from django.db.models import Case, CharField, OuterRef, Subquery, Value, When
from rest_framework import serializers

from apps.core.serializers import BaseInputSerializer, BaseOutputSerializer
from apps.rbac.models import Membership
from apps.rbac.serializers import MemberUserOutputSerializer


class GovernanceMemberListOutput(BaseOutputSerializer):
    """Member listing for governance — includes account context."""

    user = MemberUserOutputSerializer(read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)
    role_level = serializers.IntegerField(source="role.level", read_only=True)
    account_name = serializers.CharField(read_only=True)
    account_slug = serializers.CharField(read_only=True, allow_null=True)

    class Meta:
        model = Membership
        fields = [
            "id",
            "user",
            "account_type",
            "account_id",
            "account_name",
            "account_slug",
            "role_name",
            "role_level",
            "is_owner",
            "status",
            "status_reason",
            "status_changed_at",
            "joined_at",
        ]
        read_only_fields = fields


class GovernanceMemberDetailOutput(BaseOutputSerializer):
    """Full member detail for governance."""

    user = MemberUserOutputSerializer(read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)
    role_level = serializers.IntegerField(source="role.level", read_only=True)
    account_name = serializers.CharField(read_only=True)
    account_slug = serializers.CharField(read_only=True, allow_null=True)

    class Meta:
        model = Membership
        fields = [
            "id",
            "user",
            "account_type",
            "account_id",
            "account_name",
            "account_slug",
            "role_name",
            "role_level",
            "is_owner",
            "status",
            "status_reason",
            "status_changed_at",
            "joined_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class GovernanceMemberActionInput(BaseInputSerializer):
    """Input for governance member enforcement actions."""

    action = serializers.ChoiceField(choices=["suspend", "ban", "remove", "reactivate"])
    reason = serializers.CharField(
        required=False,
        max_length=1000,
        allow_blank=True,
        default="",
    )

    def validate(self, data):
        action = data.get("action")
        reason = data.get("reason", "").strip()
        if action in ("suspend", "ban", "remove") and not reason:
            raise serializers.ValidationError(
                {"reason": "A reason is required for this action."}
            )
        return data


def annotate_account_context(qs):
    """Annotate membership queryset with account_name and account_slug."""
    from apps.organization.business.models import BusinessAccount
    from apps.organization.platform.models import PlatformProfile

    business_name_sq = Subquery(
        BusinessAccount.all_objects.filter(id=OuterRef("account_id")).values(
            "legal_name"
        )[:1]
    )
    platform_name_sq = Subquery(
        PlatformProfile.objects.filter(platform_id=OuterRef("account_id")).values(
            "name"
        )[:1]
    )

    return qs.annotate(
        account_name=Case(
            When(account_type="business", then=business_name_sq),
            When(account_type="platform", then=platform_name_sq),
            default=Value("Unknown"),
            output_field=CharField(),
        ),
        account_slug=Case(
            When(
                account_type="business",
                then=Subquery(
                    BusinessAccount.all_objects.filter(
                        id=OuterRef("account_id")
                    ).values("slug")[:1]
                ),
            ),
            default=Value(None),
            output_field=CharField(),
        ),
    )
