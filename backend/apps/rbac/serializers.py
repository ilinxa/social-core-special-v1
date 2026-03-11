# apps/rbac/serializers.py
"""
RBAC Serializers - Input validation and output representation.

Follows the layered architecture:
- Input serializers: Validate incoming data
- Output serializers: Format data for API responses
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

from apps.core.constants import AccountType, PermissionScope, MembershipStatus
from apps.rbac.models import Permission, Role, RolePermission, Membership

User = get_user_model()


# =============================================================================
# OUTPUT SERIALIZERS
# =============================================================================

class PermissionOutputSerializer(serializers.ModelSerializer):
    """Output serializer for Permission."""

    class Meta:
        model = Permission
        fields = [
            "id",
            "code",
            "name",
            "description",
            "category",
            "applicable_scopes",
        ]
        read_only_fields = fields


class RolePermissionOutputSerializer(serializers.ModelSerializer):
    """Output serializer for RolePermission with nested permission."""

    permission = PermissionOutputSerializer(read_only=True)

    class Meta:
        model = RolePermission
        fields = [
            "id",
            "permission",
            "scope",
        ]
        read_only_fields = fields


class RoleOutputSerializer(serializers.ModelSerializer):
    """Output serializer for Role."""

    member_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "account_type",
            "account_id",
            "level",
            "is_system_role",
            "description",
            "member_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class RoleDetailOutputSerializer(serializers.ModelSerializer):
    """Detailed output serializer for Role with permissions."""

    role_permissions = RolePermissionOutputSerializer(many=True, read_only=True)
    permission_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "account_type",
            "account_id",
            "level",
            "is_system_role",
            "description",
            "role_permissions",
            "permission_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_permission_count(self, obj) -> int:
        return obj.role_permissions.count()


class MemberUserOutputSerializer(serializers.ModelSerializer):
    """Minimal user info for membership lists."""

    display_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "display_name",
            "avatar_url",
        ]
        read_only_fields = fields

    def get_display_name(self, obj) -> str:
        if hasattr(obj, "profile"):
            return obj.profile.display_name
        return obj.email.split("@")[0]

    def get_avatar_url(self, obj):
        if hasattr(obj, "profile") and obj.profile.avatar:
            return obj.profile.avatar.url
        return None


class MembershipOutputSerializer(serializers.ModelSerializer):
    """Output serializer for Membership."""

    user = MemberUserOutputSerializer(read_only=True)
    role = RoleOutputSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = [
            "id",
            "user",
            "account_type",
            "account_id",
            "role",
            "is_owner",
            "status",
            "joined_at",
            "status_changed_at",
            "status_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class MembershipListOutputSerializer(serializers.ModelSerializer):
    """Lightweight output serializer for membership lists."""

    user = MemberUserOutputSerializer(read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)
    role_level = serializers.IntegerField(source="role.level", read_only=True)

    class Meta:
        model = Membership
        fields = [
            "id",
            "user",
            "role_name",
            "role_level",
            "is_owner",
            "status",
            "joined_at",
        ]
        read_only_fields = fields


class MyMembershipOutputSerializer(serializers.ModelSerializer):
    """Output serializer for user's own memberships."""

    role = RoleOutputSerializer(read_only=True)
    permissions = serializers.SerializerMethodField()
    account_name = serializers.SerializerMethodField()
    account_slug = serializers.SerializerMethodField()
    account_max_members = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = [
            "id",
            "account_type",
            "account_id",
            "account_name",
            "account_slug",
            "account_max_members",
            "role",
            "is_owner",
            "status",
            "joined_at",
            "permissions",
        ]
        read_only_fields = fields

    def get_permissions(self, obj) -> list:
        """Return list of permission codes for this membership."""
        from apps.rbac.selectors import PermissionSelector
        permissions = PermissionSelector.get_permissions_for_membership(
            membership_id=obj.id
        )
        return [{"code": code, "scope": scope} for code, scope in permissions]

    def get_account_name(self, obj) -> str:
        """Return human-readable account name."""
        if obj.account_type == AccountType.BUSINESS:
            from apps.organization.business.models import BusinessAccount
            try:
                account = BusinessAccount.objects.get(id=obj.account_id)
                return account.legal_name
            except BusinessAccount.DoesNotExist:
                return ""
        return "Platform"

    def get_account_slug(self, obj) -> str:
        """Return account slug (business only, empty string for platform)."""
        if obj.account_type == AccountType.BUSINESS:
            from apps.organization.business.models import BusinessAccount
            try:
                account = BusinessAccount.objects.get(id=obj.account_id)
                return account.slug
            except BusinessAccount.DoesNotExist:
                return ""
        return ""

    def get_account_max_members(self, obj) -> int:
        """Return max_members for the account this membership belongs to."""
        if obj.account_type == AccountType.BUSINESS:
            from apps.organization.business.models import BusinessAccount
            try:
                return BusinessAccount.objects.values_list(
                    "max_members", flat=True,
                ).get(id=obj.account_id)
            except BusinessAccount.DoesNotExist:
                return 0
        elif obj.account_type == AccountType.PLATFORM:
            from apps.organization.platform.models import PlatformAccount
            try:
                return PlatformAccount.objects.values_list(
                    "max_members", flat=True,
                ).get(id=obj.account_id)
            except PlatformAccount.DoesNotExist:
                return 0
        return 0


# =============================================================================
# INPUT SERIALIZERS
# =============================================================================

class RoleCreateInputSerializer(serializers.Serializer):
    """Input serializer for creating a role."""

    name = serializers.CharField(max_length=100)
    level = serializers.IntegerField(min_value=1, max_value=10)
    description = serializers.CharField(required=False, allow_blank=True, default="")


class RoleUpdateInputSerializer(serializers.Serializer):
    """Input serializer for updating a role."""

    name = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(required=False, allow_blank=True)


class RolePermissionAddInputSerializer(serializers.Serializer):
    """Input serializer for adding a permission to a role."""

    permission_id = serializers.UUIDField()
    scope = serializers.ChoiceField(choices=PermissionScope.choices)


class RolePermissionRemoveInputSerializer(serializers.Serializer):
    """Input serializer for removing a permission from a role."""

    permission_id = serializers.UUIDField()


class MembershipRoleChangeInputSerializer(serializers.Serializer):
    """Input serializer for changing a member's role."""

    role_id = serializers.UUIDField()


class MembershipStatusChangeInputSerializer(serializers.Serializer):
    """Input serializer for changing a member's status."""

    status = serializers.ChoiceField(choices=[
        MembershipStatus.SUSPENDED,
        MembershipStatus.BANNED,
        MembershipStatus.REMOVED,
        MembershipStatus.ACTIVE,
    ])
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class MemberActionReasonInputSerializer(serializers.Serializer):
    """Input serializer for suspend/remove/ban actions that only require an optional reason."""

    reason = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=1000,
    )
