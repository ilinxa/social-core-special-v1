# apps/rbac/tests/test_selectors.py
"""
Tests for RBAC selectors.

Tests cover:
- PermissionSelector: get_all, get_by_id, get_by_code, get_permissions_for_membership
- RoleSelector: get_by_id, get_roles_for_account, get_owner_role, get_base_member_role
- MembershipSelector: get_by_id, get_for_user_account, get_memberships_for_account
- Cache invalidation
"""

import pytest
from uuid import uuid4
from django.core.cache import cache

from apps.core.constants import AccountType, PermissionScope, MembershipStatus
from apps.core.exceptions import NotFound
from apps.rbac.models import Permission, Role, RolePermission, Membership
from apps.rbac.selectors import PermissionSelector, RoleSelector, MembershipSelector
from apps.rbac.tests.conftest import skip_if_locmem_cache


@pytest.mark.django_db
class TestPermissionSelector:
    """Tests for PermissionSelector."""

    def test_get_all_permissions(self, permission):
        """Test getting all permissions."""
        permissions = PermissionSelector.get_all_permissions()
        assert permissions.count() >= 1
        assert permission in permissions

    def test_get_permission_by_id(self, permission):
        """Test getting permission by ID."""
        result = PermissionSelector.get_permission_by_id(permission_id=permission.id)
        assert result == permission

    def test_get_permission_by_id_not_found(self):
        """Test getting non-existent permission by ID."""
        with pytest.raises(NotFound) as exc_info:
            PermissionSelector.get_permission_by_id(permission_id=uuid4())
        assert exc_info.value.details.get("resource") == "Permission"

    def test_get_permission_by_code(self, permission):
        """Test getting permission by code."""
        result = PermissionSelector.get_permission_by_code(code=permission.code)
        assert result == permission

    def test_get_permission_by_code_not_found(self):
        """Test getting non-existent permission by code."""
        with pytest.raises(NotFound) as exc_info:
            PermissionSelector.get_permission_by_code(code="nonexistent_permission")
        assert exc_info.value.details.get("resource") == "Permission"

    def test_get_permissions_by_category(self, db):
        """Test getting permissions by category."""
        Permission.objects.create(
            code="cat_test_1",
            name="Cat Test 1",
            category="test_category",
            applicable_scopes=["business"],
        )
        Permission.objects.create(
            code="cat_test_2",
            name="Cat Test 2",
            category="test_category",
            applicable_scopes=["business"],
        )
        Permission.objects.create(
            code="other_cat",
            name="Other",
            category="other_category",
            applicable_scopes=["business"],
        )

        result = PermissionSelector.get_permissions_by_category(category="test_category")
        assert result.count() == 2

    def test_get_permissions_for_membership(self, role_with_permissions, user):
        """Test getting permissions for a membership."""
        membership = Membership.objects.create(
            user=user,
            account_type=role_with_permissions.account_type,
            account_id=role_with_permissions.account_id,
            role=role_with_permissions,
            status=MembershipStatus.ACTIVE,
        )

        # Clear cache first
        cache.clear()

        permissions = PermissionSelector.get_permissions_for_membership(
            membership_id=membership.id
        )

        assert len(permissions) == 2
        # Returns list of (code, scope) tuples
        codes = [p[0] for p in permissions]
        assert "can_view_members" in codes
        assert "can_change_member_role" in codes

    def test_get_permissions_for_inactive_membership(self, role, user):
        """Test that inactive membership returns empty permissions."""
        membership = Membership.objects.create(
            user=user,
            account_type=role.account_type,
            account_id=role.account_id,
            role=role,
            status=MembershipStatus.SUSPENDED,
        )

        permissions = PermissionSelector.get_permissions_for_membership(
            membership_id=membership.id
        )
        assert permissions == []

    def test_get_permissions_caching(self, role_with_permissions, user):
        """Test that permissions are cached."""
        membership = Membership.objects.create(
            user=user,
            account_type=role_with_permissions.account_type,
            account_id=role_with_permissions.account_id,
            role=role_with_permissions,
            status=MembershipStatus.ACTIVE,
        )

        cache.clear()

        # First call should set cache
        permissions1 = PermissionSelector.get_permissions_for_membership(
            membership_id=membership.id
        )

        # Second call should use cache
        permissions2 = PermissionSelector.get_permissions_for_membership(
            membership_id=membership.id
        )

        assert permissions1 == permissions2

    @skip_if_locmem_cache
    def test_invalidate_membership_permissions(self, role_with_permissions, user):
        """Test invalidating membership permissions cache."""
        membership = Membership.objects.create(
            user=user,
            account_type=role_with_permissions.account_type,
            account_id=role_with_permissions.account_id,
            role=role_with_permissions,
            status=MembershipStatus.ACTIVE,
        )

        cache.clear()

        # Set cache
        PermissionSelector.get_permissions_for_membership(membership_id=membership.id)

        # Verify cache is set
        cache_key = f"membership_permissions:{membership.id}"
        assert cache.get(cache_key) is not None

        # Invalidate
        PermissionSelector.invalidate_membership_permissions(membership_id=membership.id)

        # Verify cache is cleared
        assert cache.get(cache_key) is None

    def test_invalidate_role_permissions(self, role_with_permissions, user, another_user):
        """Test invalidating permissions for all memberships with a role."""
        m1 = Membership.objects.create(
            user=user,
            account_type=role_with_permissions.account_type,
            account_id=role_with_permissions.account_id,
            role=role_with_permissions,
            status=MembershipStatus.ACTIVE,
        )
        m2 = Membership.objects.create(
            user=another_user,
            account_type=role_with_permissions.account_type,
            account_id=role_with_permissions.account_id,
            role=role_with_permissions,
            status=MembershipStatus.ACTIVE,
        )

        cache.clear()

        # Set cache for both
        PermissionSelector.get_permissions_for_membership(membership_id=m1.id)
        PermissionSelector.get_permissions_for_membership(membership_id=m2.id)

        # Invalidate by role
        PermissionSelector.invalidate_role_permissions(role_id=role_with_permissions.id)

        # Both caches should be cleared
        assert cache.get(f"membership_permissions:{m1.id}") is None
        assert cache.get(f"membership_permissions:{m2.id}") is None


@pytest.mark.django_db
class TestRoleSelector:
    """Tests for RoleSelector."""

    def test_get_role_by_id(self, role):
        """Test getting role by ID."""
        result = RoleSelector.get_role_by_id(role_id=role.id)
        assert result == role

    def test_get_role_by_id_not_found(self):
        """Test getting non-existent role by ID."""
        with pytest.raises(NotFound) as exc_info:
            RoleSelector.get_role_by_id(role_id=uuid4())
        assert exc_info.value.details.get("resource") == "Role"

    def test_get_roles_for_account(self, business):
        """Test getting all roles for an account."""
        Role.objects.create(
            name="Role 1",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=2,
        )
        Role.objects.create(
            name="Role 2",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
        )

        roles = RoleSelector.get_roles_for_account(
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        )
        assert roles.count() == 2
        # Should be ordered by level
        assert list(roles.values_list("level", flat=True)) == [2, 5]

    def test_get_roles_for_account_exclude_system(self, business):
        """Test excluding system roles."""
        Role.objects.create(
            name="Owner",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=0,
            is_system_role=True,
        )
        Role.objects.create(
            name="Custom Role",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
            is_system_role=False,
        )

        roles = RoleSelector.get_roles_for_account(
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            include_system=False,
        )
        assert roles.count() == 1
        assert roles.first().name == "Custom Role"

    def test_get_owner_role(self, owner_role):
        """Test getting owner role for an account."""
        result = RoleSelector.get_owner_role(
            account_type=owner_role.account_type,
            account_id=owner_role.account_id,
        )
        assert result == owner_role
        assert result.level == 0
        assert result.is_system_role is True

    def test_get_owner_role_not_found(self, business):
        """Test getting owner role when it doesn't exist."""
        with pytest.raises(NotFound):
            RoleSelector.get_owner_role(
                account_type=AccountType.BUSINESS,
                account_id=business.id,
            )

    def test_get_base_member_role(self, base_member_role):
        """Test getting base member role for an account."""
        result = RoleSelector.get_base_member_role(
            account_type=base_member_role.account_type,
            account_id=base_member_role.account_id,
        )
        assert result == base_member_role
        assert result.name == "Base Member"
        assert result.is_system_role is True

    def test_get_base_member_role_not_found(self, business):
        """Test getting base member role when it doesn't exist."""
        with pytest.raises(NotFound):
            RoleSelector.get_base_member_role(
                account_type=AccountType.BUSINESS,
                account_id=business.id,
            )

    def test_get_role_permissions(self, role_with_permissions):
        """Test getting permissions assigned to a role."""
        role_perms = RoleSelector.get_role_permissions(role_id=role_with_permissions.id)
        assert role_perms.count() == 2


@pytest.mark.django_db
class TestMembershipSelector:
    """Tests for MembershipSelector."""

    def test_get_membership_by_id(self, membership):
        """Test getting membership by ID."""
        result = MembershipSelector.get_membership_by_id(membership_id=membership.id)
        assert result == membership

    def test_get_membership_by_id_not_found(self):
        """Test getting non-existent membership by ID."""
        with pytest.raises(NotFound) as exc_info:
            MembershipSelector.get_membership_by_id(membership_id=uuid4())
        assert exc_info.value.details.get("resource") == "Membership"

    def test_get_membership_for_user_account(self, membership):
        """Test getting user's membership in an account."""
        result = MembershipSelector.get_membership_for_user_account(
            user=membership.user,
            account_type=membership.account_type,
            account_id=membership.account_id,
        )
        assert result == membership

    def test_get_membership_for_user_account_not_found(self, user, business):
        """Test getting membership when user is not a member."""
        result = MembershipSelector.get_membership_for_user_account(
            user=user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        )
        assert result is None

    def test_get_active_membership_for_user_account(self, membership):
        """Test getting user's active membership."""
        result = MembershipSelector.get_active_membership_for_user_account(
            user=membership.user,
            account_type=membership.account_type,
            account_id=membership.account_id,
        )
        assert result == membership

    def test_get_active_membership_excludes_suspended(self, user, role):
        """Test that suspended memberships are not returned as active."""
        membership = Membership.objects.create(
            user=user,
            account_type=role.account_type,
            account_id=role.account_id,
            role=role,
            status=MembershipStatus.SUSPENDED,
        )
        result = MembershipSelector.get_active_membership_for_user_account(
            user=user,
            account_type=role.account_type,
            account_id=role.account_id,
        )
        assert result is None

    def test_get_memberships_for_account(self, business_with_members):
        """Test getting all memberships for an account."""
        business = business_with_members["business"]
        memberships = MembershipSelector.get_memberships_for_account(
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        )
        assert memberships.count() == 3

    def test_get_memberships_for_account_with_status_filter(self, business_with_members):
        """Test filtering memberships by status."""
        member1 = business_with_members["member1_membership"]
        member1.status = MembershipStatus.SUSPENDED
        member1.save()

        business = business_with_members["business"]
        suspended = MembershipSelector.get_memberships_for_account(
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            status=MembershipStatus.SUSPENDED,
            include_all_statuses=True,
        )
        assert suspended.count() == 1

    def test_get_memberships_for_account_include_all_statuses(self, business_with_members):
        """Test including all statuses."""
        member1 = business_with_members["member1_membership"]
        member1.status = MembershipStatus.BANNED
        member1.save()

        business = business_with_members["business"]

        # Without include_all_statuses
        active_only = MembershipSelector.get_memberships_for_account(
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        )
        assert active_only.count() == 2

        # With include_all_statuses
        all_statuses = MembershipSelector.get_memberships_for_account(
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            include_all_statuses=True,
        )
        assert all_statuses.count() == 3

    def test_get_memberships_for_user(self, user, business, another_business):
        """Test getting all memberships for a user."""
        role1 = Role.objects.create(
            name="R1",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
        )
        role2 = Role.objects.create(
            name="R2",
            account_type=AccountType.BUSINESS,
            account_id=another_business.id,
            level=5,
        )
        Membership.objects.create(
            user=user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            role=role1,
            status=MembershipStatus.ACTIVE,
        )
        Membership.objects.create(
            user=user,
            account_type=AccountType.BUSINESS,
            account_id=another_business.id,
            role=role2,
            status=MembershipStatus.ACTIVE,
        )

        memberships = MembershipSelector.get_memberships_for_user(user=user)
        assert memberships.count() == 2

    def test_get_memberships_for_user_include_pending_approval(
        self, user, business, another_business
    ):
        """Pending-approval memberships are included when flag is set."""
        role1 = Role.objects.create(
            name="R1PA",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
        )
        role2 = Role.objects.create(
            name="R2PA",
            account_type=AccountType.BUSINESS,
            account_id=another_business.id,
            level=5,
        )
        Membership.objects.create(
            user=user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            role=role1,
            status=MembershipStatus.ACTIVE,
        )
        Membership.objects.create(
            user=user,
            account_type=AccountType.BUSINESS,
            account_id=another_business.id,
            role=role2,
            status=MembershipStatus.PENDING_APPROVAL,
        )

        # Default: only active
        active_only = MembershipSelector.get_memberships_for_user(user=user)
        assert active_only.count() == 1

        # With pending_approval included
        with_pending = MembershipSelector.get_memberships_for_user(
            user=user, include_pending_approval=True,
        )
        assert with_pending.count() == 2
        statuses = set(with_pending.values_list("status", flat=True))
        assert statuses == {"active", "pending_approval"}

    def test_get_owner_membership(self, owner_membership):
        """Test getting owner membership for an account."""
        result = MembershipSelector.get_owner_membership(
            account_type=owner_membership.account_type,
            account_id=owner_membership.account_id,
        )
        assert result == owner_membership
        assert result.is_owner is True

    def test_get_owner_membership_not_found(self, business):
        """Test getting owner membership when no owner exists."""
        result = MembershipSelector.get_owner_membership(
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        )
        assert result is None

    def test_count_active_members(self, business_with_members):
        """Test counting active members."""
        business = business_with_members["business"]
        count = MembershipSelector.count_active_members(
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        )
        assert count == 3

    def test_count_active_members_excludes_suspended(self, business_with_members):
        """Test that suspended members are not counted."""
        member1 = business_with_members["member1_membership"]
        member1.status = MembershipStatus.SUSPENDED
        member1.save()

        business = business_with_members["business"]
        count = MembershipSelector.count_active_members(
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        )
        assert count == 2

    def test_is_user_member_of_account(self, membership):
        """Test checking if user is member of account."""
        result = MembershipSelector.is_user_member_of_account(
            user=membership.user,
            account_type=membership.account_type,
            account_id=membership.account_id,
        )
        assert result is True

    def test_is_user_member_of_account_not_member(self, user, business):
        """Test checking membership for non-member."""
        result = MembershipSelector.is_user_member_of_account(
            user=user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        )
        assert result is False

    def test_is_user_owner_of_account(self, owner_membership):
        """Test checking if user is owner of account."""
        result = MembershipSelector.is_user_owner_of_account(
            user=owner_membership.user,
            account_type=owner_membership.account_type,
            account_id=owner_membership.account_id,
        )
        assert result is True

    def test_is_user_owner_of_account_not_owner(self, membership):
        """Test checking ownership for non-owner."""
        result = MembershipSelector.is_user_owner_of_account(
            user=membership.user,
            account_type=membership.account_type,
            account_id=membership.account_id,
        )
        assert result is False

    def test_get_users_with_permission(self, business):
        """Test finding users who have a specific permission in an account."""
        from apps.users.tests.factories import UserFactory

        perm = Permission.objects.create(
            code="test_perm_for_selector",
            name="Test Perm",
            description="Test",
            category="test",
            applicable_scopes=["business"],
        )
        role = Role.objects.create(
            name="Approver",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
        )
        RolePermission.objects.create(role=role, permission=perm, scope="business")

        user_with_perm = UserFactory()
        Membership.objects.create(
            user=user_with_perm,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            role=role,
            status=MembershipStatus.ACTIVE,
        )

        result = MembershipSelector.get_users_with_permission(
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            permission_code="test_perm_for_selector",
        )
        assert len(result) == 1
        assert result[0].id == user_with_perm.id

    def test_get_users_with_permission_excludes_inactive(self, business):
        """Test that suspended memberships are excluded."""
        from apps.users.tests.factories import UserFactory

        perm = Permission.objects.create(
            code="test_perm_inactive",
            name="Test Inactive",
            description="Test",
            category="test",
            applicable_scopes=["business"],
        )
        role = Role.objects.create(
            name="InactiveRole",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
        )
        RolePermission.objects.create(role=role, permission=perm, scope="business")

        suspended_user = UserFactory()
        Membership.objects.create(
            user=suspended_user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            role=role,
            status=MembershipStatus.SUSPENDED,
        )

        result = MembershipSelector.get_users_with_permission(
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            permission_code="test_perm_inactive",
        )
        assert len(result) == 0

    def test_get_users_with_permission_no_match(self, business):
        """Test empty result when no users have the permission."""
        result = MembershipSelector.get_users_with_permission(
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            permission_code="nonexistent_permission",
        )
        assert result == []


# ==========================================================================
# Platform Selector Tests
# ==========================================================================


@pytest.mark.django_db
class TestPlatformSelectors:
    """Tests verifying selectors work correctly for platform account_type."""

    def test_get_roles_for_platform(self, platform_with_members):
        """get_roles_for_account works for platform."""
        platform = platform_with_members["platform"]
        roles = RoleSelector.get_roles_for_account(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        )
        role_names = [r.name for r in roles]
        assert "Platform Owner" in role_names
        assert "Platform Admin" in role_names
        assert "Base Member" in role_names

    def test_get_memberships_for_platform(self, platform_with_members):
        """get_memberships_for_account works for platform."""
        platform = platform_with_members["platform"]
        memberships = MembershipSelector.get_memberships_for_account(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        )
        assert len(memberships) == 3

    def test_count_active_platform_members(self, platform_with_members):
        """count_active_members works for platform."""
        platform = platform_with_members["platform"]
        count = MembershipSelector.count_active_members(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        )
        assert count == 3

    def test_get_platform_owner_role(self, platform_with_members):
        """get_owner_role works for platform."""
        platform = platform_with_members["platform"]
        owner_role = RoleSelector.get_owner_role(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        )
        assert owner_role.name == "Platform Owner"
        assert owner_role.level == 0

    def test_get_platform_base_member_role(self, platform_with_members):
        """get_base_member_role works for platform."""
        platform = platform_with_members["platform"]
        base_role = RoleSelector.get_base_member_role(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        )
        assert base_role.name == "Base Member"
        assert base_role.level == 10

    def test_get_users_with_platform_permission(self, platform_with_members):
        """get_users_with_permission works for platform."""
        platform = platform_with_members["platform"]
        owner = platform_with_members["owner_membership"]

        perm = Permission.objects.create(
            code="test_platform_perm",
            name="Test Platform Perm",
            description="For test",
            category="test",
            applicable_scopes=["platform_only"],
        )
        RolePermission.objects.create(
            role=owner.role,
            permission=perm,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        result = MembershipSelector.get_users_with_permission(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            permission_code="test_platform_perm",
        )
        assert len(result) == 1
        assert result[0] == owner.user


@pytest.mark.django_db
class TestPlatformMembershipSelector:
    """Additional platform membership selector tests — mirrors TestMembershipSelector."""

    def test_get_platform_membership_by_id(self, platform_owner_membership):
        """get_membership_by_id works for platform membership."""
        result = MembershipSelector.get_membership_by_id(
            membership_id=platform_owner_membership.id,
        )
        assert result == platform_owner_membership
        assert result.account_type == AccountType.PLATFORM

    def test_get_platform_membership_for_user_account(self, platform_owner_membership, platform):
        """get_membership_for_user_account works for platform."""
        result = MembershipSelector.get_membership_for_user_account(
            user=platform_owner_membership.user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        )
        assert result == platform_owner_membership

    def test_get_platform_membership_not_member(self, platform, another_user):
        """get_membership_for_user_account returns None for non-member."""
        result = MembershipSelector.get_membership_for_user_account(
            user=another_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        )
        assert result is None

    def test_get_active_platform_membership(self, platform_owner_membership, platform):
        """get_active_membership_for_user_account works for platform."""
        result = MembershipSelector.get_active_membership_for_user_account(
            user=platform_owner_membership.user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        )
        assert result == platform_owner_membership

    def test_get_active_platform_excludes_suspended(
        self, platform, platform_admin_role, another_user,
    ):
        """Suspended platform memberships are not returned as active."""
        Membership.objects.create(
            user=another_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role=platform_admin_role,
            status=MembershipStatus.SUSPENDED,
        )
        result = MembershipSelector.get_active_membership_for_user_account(
            user=another_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        )
        assert result is None

    def test_get_platform_memberships_with_status_filter(self, platform_with_members):
        """Filter platform memberships by status."""
        member = platform_with_members["member_membership"]
        member.status = MembershipStatus.SUSPENDED
        member.save()

        platform = platform_with_members["platform"]
        suspended = MembershipSelector.get_memberships_for_account(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            status=MembershipStatus.SUSPENDED,
            include_all_statuses=True,
        )
        assert suspended.count() == 1

    def test_get_platform_memberships_include_all_statuses(self, platform_with_members):
        """Include all statuses for platform memberships."""
        member = platform_with_members["member_membership"]
        member.status = MembershipStatus.BANNED
        member.save()

        platform = platform_with_members["platform"]

        active_only = MembershipSelector.get_memberships_for_account(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        )
        assert active_only.count() == 2

        all_statuses = MembershipSelector.get_memberships_for_account(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            include_all_statuses=True,
        )
        assert all_statuses.count() == 3

    def test_is_user_platform_member(self, platform_owner_membership, platform):
        """is_user_member_of_account for platform returns True."""
        result = MembershipSelector.is_user_member_of_account(
            user=platform_owner_membership.user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        )
        assert result is True

    def test_is_user_not_platform_member(self, platform, another_user):
        """is_user_member_of_account for non-member returns False."""
        result = MembershipSelector.is_user_member_of_account(
            user=another_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        )
        assert result is False

    def test_is_user_platform_owner(self, platform_owner_membership, platform):
        """is_user_owner_of_account for platform owner returns True."""
        result = MembershipSelector.is_user_owner_of_account(
            user=platform_owner_membership.user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        )
        assert result is True

    def test_is_user_not_platform_owner(self, platform_admin_membership, platform):
        """is_user_owner_of_account for non-owner returns False."""
        result = MembershipSelector.is_user_owner_of_account(
            user=platform_admin_membership.user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        )
        assert result is False

    def test_get_platform_owner_membership(self, platform_owner_membership, platform):
        """get_owner_membership returns platform owner."""
        result = MembershipSelector.get_owner_membership(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        )
        assert result == platform_owner_membership
        assert result.is_owner is True

    def test_count_active_platform_excludes_suspended(self, platform_with_members):
        """count_active_members excludes suspended platform members."""
        member = platform_with_members["member_membership"]
        member.status = MembershipStatus.SUSPENDED
        member.save()

        platform = platform_with_members["platform"]
        count = MembershipSelector.count_active_members(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        )
        assert count == 2

    def test_get_users_with_platform_permission_excludes_inactive(self, platform_with_members):
        """Suspended platform members excluded from permission query."""
        platform = platform_with_members["platform"]
        admin = platform_with_members["admin_membership"]

        perm = Permission.objects.create(
            code="test_plat_inactive_perm",
            name="Test Inactive",
            category="test",
            applicable_scopes=["platform_only"],
        )
        RolePermission.objects.create(
            role=admin.role,
            permission=perm,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        # Suspend the admin
        admin.status = MembershipStatus.SUSPENDED
        admin.save()

        result = MembershipSelector.get_users_with_permission(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            permission_code="test_plat_inactive_perm",
        )
        assert len(result) == 0


@pytest.mark.django_db
class TestPlatformRoleSelector:
    """Additional platform role selector tests — mirrors TestRoleSelector."""

    def test_get_platform_roles_exclude_system(self, platform_with_members):
        """Exclude system roles for platform."""
        platform = platform_with_members["platform"]

        # Create a custom non-system role
        Role.objects.create(
            name="Custom Platform Role",
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            level=7,
            is_system_role=False,
        )

        roles = RoleSelector.get_roles_for_account(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            include_system=False,
        )
        for role in roles:
            assert role.is_system_role is False

    def test_get_platform_role_permissions(self, platform_admin_role):
        """Get permissions assigned to a platform role."""
        perm = Permission.objects.create(
            code="test_plat_role_perm",
            name="Plat Role Perm",
            category="test",
            applicable_scopes=["platform_only"],
        )
        RolePermission.objects.create(
            role=platform_admin_role,
            permission=perm,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        role_perms = RoleSelector.get_role_permissions(role_id=platform_admin_role.id)
        assert role_perms.count() >= 1

    def test_get_platform_owner_role_not_found(self, platform):
        """Get owner role when it doesn't exist raises NotFound."""
        # Delete all platform roles
        Role.objects.filter(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        ).delete()

        with pytest.raises(NotFound):
            RoleSelector.get_owner_role(
                account_type=AccountType.PLATFORM,
                account_id=platform.id,
            )

    def test_get_platform_roles_ordered_by_level(self, platform_with_members):
        """Platform roles are ordered by level."""
        platform = platform_with_members["platform"]
        roles = RoleSelector.get_roles_for_account(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        )
        levels = list(roles.values_list("level", flat=True))
        assert levels == sorted(levels)
