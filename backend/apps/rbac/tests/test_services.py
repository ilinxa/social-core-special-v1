# apps/rbac/tests/test_services.py
"""
Tests for RBAC services.

Tests cover:
- build_actor_context: Create ActorContext from membership
- initialize_business_account: Create business roles + owner membership
- initialize_platform_account: Create platform predefined roles
- create_membership: Create new member with role
- change_member_role: Change member's role
- update_membership_status: Suspend/ban/remove member
- member_leave: Member voluntarily leaves
- create_custom_role: Create custom role
- delete_role: Delete custom role
- add_permission_to_role: Add permission to role
- remove_permission_from_role: Remove permission from role
"""

import pytest
from uuid import uuid4

from django.core.cache import cache

from apps.core.constants import AccountType, PermissionScope, MembershipStatus
from apps.core.exceptions import (
    NotFound, ConflictError, PermissionDenied, BusinessRuleViolation, ValidationError
)
from apps.core.types import ActorContext
from apps.rbac.models import Permission, Role, RolePermission, Membership
from apps.rbac.services import RBACService
from apps.rbac.selectors import RoleSelector, MembershipSelector
from apps.rbac.tests.conftest import skip_if_sqlite, skip_if_locmem_cache
from apps.rbac.tests.factories import (
    BusinessAccountFactory, PlatformAccountFactory, UserFactory,
)


@pytest.mark.django_db
class TestBuildActorContext:
    """Tests for RBACService.build_actor_context."""

    def test_build_actor_context_success(self, role_with_permissions, user):
        """Test building actor context from active membership."""
        membership = Membership.objects.create(
            user=user,
            account_type=role_with_permissions.account_type,
            account_id=role_with_permissions.account_id,
            role=role_with_permissions,
            is_owner=False,
            status=MembershipStatus.ACTIVE,
        )
        cache.clear()

        context = RBACService.build_actor_context(membership=membership)

        assert context.user_id == user.id
        assert context.account_type == role_with_permissions.account_type
        assert context.account_id == role_with_permissions.account_id
        assert context.membership_id == membership.id
        assert context.role_id == role_with_permissions.id
        assert context.role_name == role_with_permissions.name
        assert context.role_level == role_with_permissions.level
        assert context.is_owner is False
        # Should have permissions from role
        assert len(context.permissions_snapshot) == 2

    def test_build_actor_context_inactive_membership_denied(self, role, user):
        """Test that inactive membership raises PermissionDenied."""
        membership = Membership.objects.create(
            user=user,
            account_type=role.account_type,
            account_id=role.account_id,
            role=role,
            status=MembershipStatus.SUSPENDED,
        )

        with pytest.raises(PermissionDenied) as exc_info:
            RBACService.build_actor_context(membership=membership)
        assert "not active" in str(exc_info.value.message)

    def test_build_actor_context_owner_membership(self, owner_role, user):
        """Test building actor context for owner membership."""
        membership = Membership.objects.create(
            user=user,
            account_type=owner_role.account_type,
            account_id=owner_role.account_id,
            role=owner_role,
            is_owner=True,
            status=MembershipStatus.ACTIVE,
        )

        context = RBACService.build_actor_context(membership=membership)

        assert context.is_owner is True
        assert context.role_level == 0


@pytest.mark.django_db
class TestInitializeBusinessAccount:
    """Tests for RBACService.initialize_business_account."""

    def test_initialize_business_account(self, business, user):
        """Test initializing a new business account with RBAC."""
        membership = RBACService.initialize_business_account(
            business_id=business.id,
            owner=user,
        )

        # Check owner membership
        assert membership.user == user
        assert membership.account_type == AccountType.BUSINESS
        assert membership.account_id == business.id
        assert membership.is_owner is True
        assert membership.status == MembershipStatus.ACTIVE

        # Check Owner role created
        owner_role = membership.role
        assert owner_role.name == "Owner"
        assert owner_role.level == 0
        assert owner_role.is_system_role is True

        # Check Base Member role created
        base_role = RoleSelector.get_base_member_role(
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        )
        assert base_role.name == "Base Member"
        assert base_role.level == 10
        assert base_role.is_system_role is True

    def test_initialize_business_account_with_permissions(self, business, user):
        """Test that owner role gets business-scope permissions."""
        # Create some permissions first
        perm = Permission.objects.create(
            code="test_business_perm",
            name="Test Perm",
            category="test",
            applicable_scopes=["business"],
        )

        membership = RBACService.initialize_business_account(
            business_id=business.id,
            owner=user,
        )

        # Owner role should have the business permission
        owner_perms = RolePermission.objects.filter(role=membership.role)
        assert owner_perms.filter(permission=perm).exists()


@pytest.mark.django_db
class TestInitializePlatformAccount:
    """Tests for RBACService.initialize_platform_account."""

    def test_initialize_platform_account(self, platform):
        """Test initializing platform account with predefined roles."""
        # Create some permissions first
        Permission.objects.create(
            code="platform_test_perm",
            name="Platform Test",
            category="test",
            applicable_scopes=["platform_only", "global_only"],
        )

        RBACService.initialize_platform_account(platform_id=platform.id)

        # Check Platform Owner role created
        owner_role = Role.objects.get(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            level=0,
        )
        assert owner_role.name == "Platform Owner"
        assert owner_role.is_system_role is True

        # Check Platform Admin role created
        admin_role = Role.objects.get(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            level=2,
        )
        assert admin_role.name == "Platform Admin"
        assert admin_role.is_system_role is False

        # Check Global Moderator role created
        mod_role = Role.objects.get(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            level=5,
        )
        assert mod_role.name == "Global Moderator"
        assert mod_role.is_system_role is False

        # Check Base Member role created
        base_role = Role.objects.get(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            level=10,
        )
        assert base_role.name == "Base Member"
        assert base_role.is_system_role is True

        # Total: 4 roles created
        total_roles = Role.objects.filter(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        ).count()
        assert total_roles == 4


@pytest.mark.django_db
class TestCreateMembership:
    """Tests for RBACService.create_membership."""

    def test_create_membership_with_role(self, business, role, base_member_role, another_user):
        """Test creating a membership with a specific role."""
        membership = RBACService.create_membership(
            user=another_user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            role_id=role.id,
        )

        assert membership.user == another_user
        assert membership.role == role
        assert membership.is_owner is False
        assert membership.status == MembershipStatus.ACTIVE

    def test_create_membership_fallback_to_base_member(self, business, base_member_role, another_user):
        """Test that membership falls back to Base Member role when role_id is None."""
        membership = RBACService.create_membership(
            user=another_user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            role_id=None,
        )

        assert membership.role == base_member_role

    def test_create_membership_duplicate_denied(self, membership):
        """Test that duplicate membership is denied."""
        with pytest.raises(ConflictError) as exc_info:
            RBACService.create_membership(
                user=membership.user,
                account_type=membership.account_type,
                account_id=membership.account_id,
            )
        assert "already a member" in str(exc_info.value.message)

    def test_create_membership_reactivates_removed(self, business, base_member_role, another_user):
        """Test that creating membership for a removed member reactivates them."""
        # Create and then remove the membership
        membership = RBACService.create_membership(
            user=another_user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        )
        membership.status = MembershipStatus.REMOVED
        membership.save(update_fields=["status"])

        # Re-creating should reactivate, not raise ConflictError
        reactivated = RBACService.create_membership(
            user=another_user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        )

        assert reactivated.id == membership.id
        assert reactivated.status == MembershipStatus.ACTIVE
        assert reactivated.role == base_member_role

    def test_create_membership_suspended_still_conflicts(self, business, base_member_role, another_user):
        """Test that suspended members still raise ConflictError."""
        membership = RBACService.create_membership(
            user=another_user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        )
        membership.status = MembershipStatus.SUSPENDED
        membership.save(update_fields=["status"])

        with pytest.raises(ConflictError):
            RBACService.create_membership(
                user=another_user,
                account_type=AccountType.BUSINESS,
                account_id=business.id,
            )


@pytest.mark.django_db
class TestChangeMemberRole:
    """Tests for RBACService.change_member_role."""

    def test_change_member_role_success(
        self, business_with_members, admin_role,
        can_change_member_role_permission
    ):
        """Test changing a member's role."""
        owner = business_with_members["owner_membership"]
        target = business_with_members["member1_membership"]

        # Give owner role the permission
        RolePermission.objects.create(
            role=owner.role,
            permission=can_change_member_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner)

        membership = RBACService.change_member_role(
            membership_id=target.id,
            new_role_id=admin_role.id,
            actor_context=actor_context,
        )

        assert membership.role == admin_role

    def test_change_member_role_without_permission(self, business_with_members, admin_role):
        """Test changing role without permission fails."""
        owner = business_with_members["owner_membership"]
        target = business_with_members["member1_membership"]

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner)

        with pytest.raises(PermissionDenied):
            RBACService.change_member_role(
                membership_id=target.id,
                new_role_id=admin_role.id,
                actor_context=actor_context,
            )


@pytest.mark.django_db
class TestUpdateMembershipStatus:
    """Tests for RBACService.update_membership_status."""

    def test_suspend_member(
        self, business_with_members, can_suspend_member_permission
    ):
        """Test suspending a member."""
        owner = business_with_members["owner_membership"]
        target = business_with_members["member1_membership"]

        # Give owner role the permission
        RolePermission.objects.create(
            role=owner.role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner)

        membership = RBACService.update_membership_status(
            membership_id=target.id,
            new_status=MembershipStatus.SUSPENDED,
            actor_context=actor_context,
            reason="Violation of terms",
        )

        assert membership.status == MembershipStatus.SUSPENDED
        assert membership.status_reason == "Violation of terms"
        assert membership.status_changed_by_id == owner.user_id

    def test_ban_member(
        self, business_with_members, can_ban_member_permission
    ):
        """Test banning a member."""
        owner = business_with_members["owner_membership"]
        target = business_with_members["member1_membership"]

        RolePermission.objects.create(
            role=owner.role,
            permission=can_ban_member_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner)

        membership = RBACService.update_membership_status(
            membership_id=target.id,
            new_status=MembershipStatus.BANNED,
            actor_context=actor_context,
        )

        assert membership.status == MembershipStatus.BANNED

    def test_reactivate_member(
        self, business_with_members, can_suspend_member_permission
    ):
        """Test reactivating a suspended member."""
        owner = business_with_members["owner_membership"]
        target = business_with_members["member1_membership"]
        target.status = MembershipStatus.SUSPENDED
        target.save()

        RolePermission.objects.create(
            role=owner.role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner)

        membership = RBACService.update_membership_status(
            membership_id=target.id,
            new_status=MembershipStatus.ACTIVE,
            actor_context=actor_context,
        )

        assert membership.status == MembershipStatus.ACTIVE


@pytest.mark.django_db
class TestMemberLeave:
    """Tests for RBACService.member_leave."""

    def test_member_leave_success(self, business_with_members):
        """Test member voluntarily leaving."""
        member = business_with_members["member1_membership"]

        membership = RBACService.member_leave(
            membership_id=member.id,
            user=member.user,
        )

        assert membership.status == MembershipStatus.LEFT
        assert membership.status_changed_by == member.user

    def test_owner_cannot_leave(self, business_with_members):
        """Test that owner cannot leave."""
        owner = business_with_members["owner_membership"]

        with pytest.raises(BusinessRuleViolation) as exc_info:
            RBACService.member_leave(
                membership_id=owner.id,
                user=owner.user,
            )
        assert "owner" in str(exc_info.value.message).lower()

    def test_cannot_leave_other_membership(self, business_with_members, user_factory):
        """Test that user cannot leave another user's membership."""
        member = business_with_members["member1_membership"]
        # Create a random user who is NOT the owner of member1_membership
        random_user = user_factory()

        with pytest.raises(PermissionDenied) as exc_info:
            RBACService.member_leave(
                membership_id=member.id,
                user=random_user,
            )
        assert "own membership" in str(exc_info.value.message)


@pytest.mark.django_db
class TestCreateCustomRole:
    """Tests for RBACService.create_custom_role."""

    def test_create_custom_role(self, business, owner_membership, can_create_role_permission):
        """Test creating a custom role."""
        # Grant the owner the permission to create roles
        RolePermission.objects.create(
            role=owner_membership.role,
            permission=can_create_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner_membership)

        role = RBACService.create_custom_role(
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            name="Manager",
            level=5,
            description="Manager role",
            actor_context=actor_context,
        )

        assert role.name == "Manager"
        assert role.level == 5
        assert role.is_system_role is False
        assert role.description == "Manager role"

    def test_cannot_create_level_0_role(self, business, owner_membership, can_create_role_permission):
        """Test that level 0 is reserved."""
        # Grant the owner the permission to create roles
        RolePermission.objects.create(
            role=owner_membership.role,
            permission=can_create_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner_membership)

        with pytest.raises(PermissionDenied) as exc_info:
            RBACService.create_custom_role(
                account_type=AccountType.BUSINESS,
                account_id=business.id,
                name="Fake Owner",
                level=0,
                actor_context=actor_context,
            )
        assert "reserved" in str(exc_info.value.message)

    def test_duplicate_role_name_denied(self, business, role, owner_membership, can_create_role_permission):
        """Test that duplicate role name is denied."""
        # Grant the owner the permission to create roles
        RolePermission.objects.create(
            role=owner_membership.role,
            permission=can_create_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner_membership)

        with pytest.raises(ConflictError) as exc_info:
            RBACService.create_custom_role(
                account_type=AccountType.BUSINESS,
                account_id=business.id,
                name=role.name,
                level=6,
                actor_context=actor_context,
            )
        assert "already exists" in str(exc_info.value.message)

    def test_create_role_without_permission_denied(self, business, owner_membership):
        """Test that creating role without permission is denied."""
        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner_membership)

        with pytest.raises(PermissionDenied) as exc_info:
            RBACService.create_custom_role(
                account_type=AccountType.BUSINESS,
                account_id=business.id,
                name="Manager",
                level=5,
                actor_context=actor_context,
            )
        assert "can_create_role" in str(exc_info.value.message)


@pytest.mark.django_db
class TestDeleteRole:
    """Tests for RBACService.delete_role."""

    def test_delete_custom_role(self, business, owner_membership, can_delete_role_permission):
        """Test deleting a custom role."""
        # Grant the owner the permission to delete roles
        RolePermission.objects.create(
            role=owner_membership.role,
            permission=can_delete_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        # Create a custom role
        custom_role = Role.objects.create(
            name="To Delete",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
            is_system_role=False,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner_membership)

        RBACService.delete_role(
            role_id=custom_role.id,
            actor_context=actor_context,
        )

        # Role should be soft-deleted
        custom_role.refresh_from_db()
        assert custom_role.is_deleted is True

    def test_cannot_delete_system_role(self, business, owner_role, owner_membership, can_delete_role_permission):
        """Test that system roles cannot be deleted."""
        # Grant the owner the permission to delete roles
        RolePermission.objects.create(
            role=owner_membership.role,
            permission=can_delete_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner_membership)

        with pytest.raises(PermissionDenied) as exc_info:
            RBACService.delete_role(
                role_id=owner_role.id,
                actor_context=actor_context,
            )
        assert "System roles" in str(exc_info.value.message)

    def test_cannot_delete_role_with_members(
        self, business, manager_role, owner_membership, another_user, can_delete_role_permission
    ):
        """Test that role with active members cannot be deleted."""
        # Grant the owner the permission to delete roles
        RolePermission.objects.create(
            role=owner_membership.role,
            permission=can_delete_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        # Assign someone to the role
        Membership.objects.create(
            user=another_user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            role=manager_role,
            status=MembershipStatus.ACTIVE,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner_membership)

        with pytest.raises(BusinessRuleViolation) as exc_info:
            RBACService.delete_role(
                role_id=manager_role.id,
                actor_context=actor_context,
            )
        assert "active member" in str(exc_info.value.message)

    def test_delete_role_without_permission_denied(self, business, owner_membership):
        """Test that deleting role without permission is denied."""
        # Create a custom role
        custom_role = Role.objects.create(
            name="To Delete",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
            is_system_role=False,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner_membership)

        with pytest.raises(PermissionDenied) as exc_info:
            RBACService.delete_role(
                role_id=custom_role.id,
                actor_context=actor_context,
            )
        assert "can_delete_role" in str(exc_info.value.message)


@pytest.mark.django_db
class TestAddPermissionToRole:
    """Tests for RBACService.add_permission_to_role."""

    def test_add_permission_to_role(self, role, permission):
        """Test adding a permission to a role."""
        role_perm = RBACService.add_permission_to_role(
            role_id=role.id,
            permission_id=permission.id,
            scope=PermissionScope.BUSINESS,
        )

        assert role_perm.role == role
        assert role_perm.permission == permission
        assert role_perm.scope == PermissionScope.BUSINESS

    def test_invalid_scope_denied(self, role):
        """Test that invalid scope is denied."""
        # Create permission that only allows business scope
        perm = Permission.objects.create(
            code="business_only_perm",
            name="Business Only",
            category="test",
            applicable_scopes=["business"],
        )

        with pytest.raises(ValidationError) as exc_info:
            RBACService.add_permission_to_role(
                role_id=role.id,
                permission_id=perm.id,
                scope=PermissionScope.GLOBAL_ONLY,
            )
        assert "not valid" in str(exc_info.value.message)

    def test_duplicate_permission_denied(self, role, permission):
        """Test that duplicate permission assignment is denied."""
        RBACService.add_permission_to_role(
            role_id=role.id,
            permission_id=permission.id,
            scope=PermissionScope.BUSINESS,
        )

        with pytest.raises(ConflictError) as exc_info:
            RBACService.add_permission_to_role(
                role_id=role.id,
                permission_id=permission.id,
                scope=PermissionScope.BUSINESS,
            )
        assert "already assigned" in str(exc_info.value.message)


@pytest.mark.django_db
class TestRemovePermissionFromRole:
    """Tests for RBACService.remove_permission_from_role."""

    def test_remove_permission_from_role(self, role, permission):
        """Test removing a permission from a role."""
        RolePermission.objects.create(
            role=role,
            permission=permission,
            scope=PermissionScope.BUSINESS,
        )

        RBACService.remove_permission_from_role(
            role_id=role.id,
            permission_id=permission.id,
        )

        assert not RolePermission.objects.filter(
            role=role, permission=permission
        ).exists()

    def test_remove_nonexistent_permission_denied(self, role, permission):
        """Test that removing non-assigned permission is denied."""
        with pytest.raises(NotFound) as exc_info:
            RBACService.remove_permission_from_role(
                role_id=role.id,
                permission_id=permission.id,
            )
        assert "not assigned" in str(exc_info.value.message)


@pytest.mark.django_db
@skip_if_locmem_cache
class TestPermissionCacheInvalidation:
    """Tests for permission cache invalidation in services."""

    def test_change_role_invalidates_cache(
        self, business_with_members, admin_role, can_change_member_role_permission
    ):
        """Test that changing role invalidates permission cache."""
        owner = business_with_members["owner_membership"]
        target = business_with_members["member1_membership"]

        RolePermission.objects.create(
            role=owner.role,
            permission=can_change_member_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()

        # Build context to populate cache
        RBACService.build_actor_context(membership=target)

        # Verify cache is set
        cache_key = f"membership_permissions:{target.id}"
        assert cache.get(cache_key) is not None

        # Change role
        actor_context = RBACService.build_actor_context(membership=owner)
        RBACService.change_member_role(
            membership_id=target.id,
            new_role_id=admin_role.id,
            actor_context=actor_context,
        )

        # Cache should be invalidated
        assert cache.get(cache_key) is None

    def test_add_permission_invalidates_role_cache(self, role, permission, user):
        """Test that adding permission invalidates cache for all members with role."""
        # Create membership with the role
        membership = Membership.objects.create(
            user=user,
            account_type=role.account_type,
            account_id=role.account_id,
            role=role,
            status=MembershipStatus.ACTIVE,
        )

        cache.clear()

        # Build context to populate cache
        RBACService.build_actor_context(membership=membership)

        # Verify cache is set
        cache_key = f"membership_permissions:{membership.id}"
        assert cache.get(cache_key) is not None

        # Add permission to role
        RBACService.add_permission_to_role(
            role_id=role.id,
            permission_id=permission.id,
            scope=PermissionScope.BUSINESS,
        )

        # Cache should be invalidated
        assert cache.get(cache_key) is None


@pytest.mark.django_db
class TestRestoreMembership:
    """Tests for RBACService.restore_membership."""

    def test_restore_membership_success(
        self, business_with_members, can_remove_member_permission
    ):
        """Test restoring a soft-deleted membership."""
        owner = business_with_members["owner_membership"]
        target = business_with_members["member1_membership"]

        # Give owner the permission
        RolePermission.objects.create(
            role=owner.role,
            permission=can_remove_member_permission,
            scope=PermissionScope.BUSINESS,
        )

        # Soft delete the membership
        target.is_deleted = True
        target.status = MembershipStatus.REMOVED
        target.save()

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner)

        # Restore the membership
        membership = RBACService.restore_membership(
            membership_id=target.id,
            actor_context=actor_context,
        )

        assert membership.is_deleted is False
        assert membership.status == MembershipStatus.ACTIVE

    def test_restore_membership_already_active_denied(
        self, business_with_members, can_remove_member_permission
    ):
        """Test that restoring an already active membership is denied."""
        owner = business_with_members["owner_membership"]
        target = business_with_members["member1_membership"]

        # Give owner the permission
        RolePermission.objects.create(
            role=owner.role,
            permission=can_remove_member_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner)

        # Membership is already active, should fail
        with pytest.raises(ConflictError) as exc_info:
            RBACService.restore_membership(
                membership_id=target.id,
                actor_context=actor_context,
            )
        assert "not deleted" in str(exc_info.value.message).lower()


@pytest.mark.django_db
class TestUpdateRole:
    """Tests for RBACService.update_role."""

    def test_update_role_name(
        self, business, owner_membership, can_edit_role_permission
    ):
        """Test updating a role's name."""
        # Grant the owner the permission to edit roles
        RolePermission.objects.create(
            role=owner_membership.role,
            permission=can_edit_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        # Create a custom role
        custom_role = Role.objects.create(
            name="Manager",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
            is_system_role=False,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner_membership)

        role = RBACService.update_role(
            role_id=custom_role.id,
            name="Senior Manager",
            actor_context=actor_context,
        )

        assert role.name == "Senior Manager"

    def test_update_role_description(
        self, business, owner_membership, can_edit_role_permission
    ):
        """Test updating a role's description."""
        # Grant the owner the permission to edit roles
        RolePermission.objects.create(
            role=owner_membership.role,
            permission=can_edit_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        # Create a custom role
        custom_role = Role.objects.create(
            name="Manager",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
            description="Old description",
            is_system_role=False,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner_membership)

        role = RBACService.update_role(
            role_id=custom_role.id,
            description="New description",
            actor_context=actor_context,
        )

        assert role.description == "New description"

    def test_update_role_without_permission_denied(
        self, business, owner_membership
    ):
        """Test that updating a role without permission is denied."""
        # Create a custom role
        custom_role = Role.objects.create(
            name="Manager",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
            is_system_role=False,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner_membership)

        with pytest.raises(PermissionDenied) as exc_info:
            RBACService.update_role(
                role_id=custom_role.id,
                name="New Name",
                actor_context=actor_context,
            )
        assert "can_edit_role" in str(exc_info.value.message)

    def test_update_system_role_denied(
        self, business, owner_role, owner_membership, can_edit_role_permission
    ):
        """Test that system roles cannot be updated."""
        # Grant the owner the permission to edit roles
        RolePermission.objects.create(
            role=owner_membership.role,
            permission=can_edit_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner_membership)

        with pytest.raises(PermissionDenied) as exc_info:
            RBACService.update_role(
                role_id=owner_role.id,
                name="New Owner Name",
                actor_context=actor_context,
            )
        assert "system role" in str(exc_info.value.message).lower()


@pytest.mark.django_db
class TestCreateMembershipQuota:
    """Tests for member quota enforcement in RBACService.create_membership."""

    def test_create_membership_blocked_when_business_at_quota(
        self, user, another_user, base_member_role,
    ):
        """Test that creating a membership fails when business is at max_members."""
        business = BusinessAccountFactory(max_members=1, created_by=user)
        owner_role = Role.objects.create(
            name="Owner", account_type=AccountType.BUSINESS,
            account_id=business.id, level=0, is_system_role=True,
        )
        Role.objects.create(
            name="Base Member", account_type=AccountType.BUSINESS,
            account_id=business.id, level=10, is_system_role=True,
        )
        Membership.objects.create(
            user=user, account_type=AccountType.BUSINESS,
            account_id=business.id, role=owner_role,
            is_owner=True, status=MembershipStatus.ACTIVE,
        )

        with pytest.raises(BusinessRuleViolation) as exc_info:
            RBACService.create_membership(
                user=another_user,
                account_type=AccountType.BUSINESS,
                account_id=business.id,
            )
        assert exc_info.value.details["rule"] == "member_quota_exceeded"

    def test_create_membership_allowed_when_business_below_quota(
        self, user, another_user,
    ):
        """Test that creating a membership succeeds when below max_members."""
        business = BusinessAccountFactory(max_members=6, created_by=user)
        owner_role = Role.objects.create(
            name="Owner", account_type=AccountType.BUSINESS,
            account_id=business.id, level=0, is_system_role=True,
        )
        Role.objects.create(
            name="Base Member", account_type=AccountType.BUSINESS,
            account_id=business.id, level=10, is_system_role=True,
        )
        Membership.objects.create(
            user=user, account_type=AccountType.BUSINESS,
            account_id=business.id, role=owner_role,
            is_owner=True, status=MembershipStatus.ACTIVE,
        )

        membership = RBACService.create_membership(
            user=another_user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        )
        assert membership.user == another_user
        assert membership.status == MembershipStatus.ACTIVE

    def test_create_membership_blocked_when_exactly_at_quota(
        self, user, another_user, third_user,
    ):
        """Test that membership is blocked when count equals max_members."""
        business = BusinessAccountFactory(max_members=2, created_by=user)
        owner_role = Role.objects.create(
            name="Owner", account_type=AccountType.BUSINESS,
            account_id=business.id, level=0, is_system_role=True,
        )
        base_role = Role.objects.create(
            name="Base Member", account_type=AccountType.BUSINESS,
            account_id=business.id, level=10, is_system_role=True,
        )
        Membership.objects.create(
            user=user, account_type=AccountType.BUSINESS,
            account_id=business.id, role=owner_role,
            is_owner=True, status=MembershipStatus.ACTIVE,
        )
        Membership.objects.create(
            user=another_user, account_type=AccountType.BUSINESS,
            account_id=business.id, role=base_role,
            is_owner=False, status=MembershipStatus.ACTIVE,
        )

        with pytest.raises(BusinessRuleViolation) as exc_info:
            RBACService.create_membership(
                user=third_user,
                account_type=AccountType.BUSINESS,
                account_id=business.id,
            )
        assert exc_info.value.details["rule"] == "member_quota_exceeded"

    def test_create_membership_unlimited_when_zero(
        self, user, another_user,
    ):
        """Test that max_members=0 means unlimited."""
        business = BusinessAccountFactory(max_members=0, created_by=user)
        owner_role = Role.objects.create(
            name="Owner", account_type=AccountType.BUSINESS,
            account_id=business.id, level=0, is_system_role=True,
        )
        Role.objects.create(
            name="Base Member", account_type=AccountType.BUSINESS,
            account_id=business.id, level=10, is_system_role=True,
        )
        Membership.objects.create(
            user=user, account_type=AccountType.BUSINESS,
            account_id=business.id, role=owner_role,
            is_owner=True, status=MembershipStatus.ACTIVE,
        )

        membership = RBACService.create_membership(
            user=another_user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        )
        assert membership.user == another_user

    def test_create_membership_blocked_when_platform_at_quota(
        self, user, another_user,
    ):
        """Test that platform membership is blocked when at max_members."""
        platform = PlatformAccountFactory()
        platform.max_members = 2
        platform.save()
        owner_role = Role.objects.create(
            name="Platform Owner", account_type=AccountType.PLATFORM,
            account_id=platform.id, level=0, is_system_role=True,
        )
        Role.objects.create(
            name="Platform Admin", account_type=AccountType.PLATFORM,
            account_id=platform.id, level=2, is_system_role=True,
        )
        Membership.objects.create(
            user=user, account_type=AccountType.PLATFORM,
            account_id=platform.id, role=owner_role,
            is_owner=True, status=MembershipStatus.ACTIVE,
        )
        admin_role = Role.objects.create(
            name="Admin Role", account_type=AccountType.PLATFORM,
            account_id=platform.id, level=3, is_system_role=False,
        )
        Membership.objects.create(
            user=another_user, account_type=AccountType.PLATFORM,
            account_id=platform.id, role=admin_role,
            is_owner=False, status=MembershipStatus.ACTIVE,
        )

        third = UserFactory(is_verified=True)
        with pytest.raises(BusinessRuleViolation) as exc_info:
            RBACService.create_membership(
                user=third,
                account_type=AccountType.PLATFORM,
                account_id=platform.id,
                role_id=admin_role.id,
            )
        assert exc_info.value.details["rule"] == "member_quota_exceeded"

    def test_create_membership_allowed_when_platform_below_quota(
        self, user, another_user,
    ):
        """Test that platform membership succeeds below max_members."""
        platform = PlatformAccountFactory()  # factory default max_members=5
        owner_role = Role.objects.create(
            name="Platform Owner", account_type=AccountType.PLATFORM,
            account_id=platform.id, level=0, is_system_role=True,
        )
        admin_role = Role.objects.create(
            name="Platform Admin", account_type=AccountType.PLATFORM,
            account_id=platform.id, level=2, is_system_role=True,
        )
        Membership.objects.create(
            user=user, account_type=AccountType.PLATFORM,
            account_id=platform.id, role=owner_role,
            is_owner=True, status=MembershipStatus.ACTIVE,
        )

        membership = RBACService.create_membership(
            user=another_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role_id=admin_role.id,
        )
        assert membership.user == another_user


# =============================================================================
# PLATFORM SERVICE TESTS
# =============================================================================


@pytest.mark.django_db
class TestPlatformBuildActorContext:
    """Tests for RBACService.build_actor_context with platform memberships."""

    def test_build_platform_owner_context(self, platform_owner_membership):
        """Build actor context from platform owner membership."""
        context = RBACService.build_actor_context(membership=platform_owner_membership)

        assert context.user_id == platform_owner_membership.user_id
        assert context.account_type == AccountType.PLATFORM
        assert context.is_owner is True
        assert context.role_level == 0

    def test_build_platform_admin_context(self, platform_admin_membership):
        """Build actor context from platform admin membership."""
        cache.clear()
        context = RBACService.build_actor_context(membership=platform_admin_membership)

        assert context.account_type == AccountType.PLATFORM
        assert context.is_owner is False
        assert context.role_level == 2
        assert context.role_name == "Platform Admin"

    def test_build_platform_context_with_permissions(
        self, platform_owner_membership, platform_owner_role,
    ):
        """Platform membership with permissions builds correct snapshot."""
        perm = Permission.objects.create(
            code="test_plat_ctx_perm",
            name="Test Platform Context Perm",
            category="test",
            applicable_scopes=["platform_only"],
        )
        RolePermission.objects.create(
            role=platform_owner_role,
            permission=perm,
            scope=PermissionScope.PLATFORM_ONLY,
        )
        cache.clear()

        context = RBACService.build_actor_context(membership=platform_owner_membership)

        codes = [p[0] for p in context.permissions_snapshot]
        assert "test_plat_ctx_perm" in codes

    def test_suspended_platform_membership_denied(self, platform, platform_admin_role, another_user):
        """Suspended platform membership cannot build context."""
        suspended = Membership.objects.create(
            user=another_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role=platform_admin_role,
            status=MembershipStatus.SUSPENDED,
        )

        with pytest.raises(PermissionDenied) as exc_info:
            RBACService.build_actor_context(membership=suspended)
        assert "not active" in str(exc_info.value.message)


@pytest.mark.django_db
class TestPlatformCreateMembership:
    """Tests for RBACService.create_membership with platform accounts."""

    def test_create_platform_membership_with_role(
        self, platform, platform_admin_role, platform_base_member_role, another_user,
    ):
        """Create a platform membership with specific role."""
        membership = RBACService.create_membership(
            user=another_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role_id=platform_admin_role.id,
        )

        assert membership.user == another_user
        assert membership.role == platform_admin_role
        assert membership.account_type == AccountType.PLATFORM
        assert membership.is_owner is False
        assert membership.status == MembershipStatus.ACTIVE

    def test_create_platform_membership_fallback_to_base(
        self, platform, platform_base_member_role, another_user,
    ):
        """Falls back to Base Member role when role_id is None."""
        membership = RBACService.create_membership(
            user=another_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role_id=None,
        )

        assert membership.role == platform_base_member_role

    def test_create_platform_membership_duplicate_denied(
        self, platform_owner_membership,
    ):
        """Duplicate platform membership is denied."""
        with pytest.raises(ConflictError) as exc_info:
            RBACService.create_membership(
                user=platform_owner_membership.user,
                account_type=platform_owner_membership.account_type,
                account_id=platform_owner_membership.account_id,
            )
        assert "already a member" in str(exc_info.value.message)

    def test_create_platform_membership_reactivates_removed(
        self, platform, platform_base_member_role, another_user,
    ):
        """Removed platform members are reactivated on re-create."""
        membership = RBACService.create_membership(
            user=another_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        )
        membership.status = MembershipStatus.REMOVED
        membership.save(update_fields=["status"])

        reactivated = RBACService.create_membership(
            user=another_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        )

        assert reactivated.id == membership.id
        assert reactivated.status == MembershipStatus.ACTIVE


@pytest.mark.django_db
class TestPlatformChangeMemberRole:
    """Tests for RBACService.change_member_role with platform accounts."""

    def test_change_platform_member_role(
        self, platform_with_members, global_moderator_role, can_change_member_role_permission,
    ):
        """Platform owner can change platform member's role."""
        owner = platform_with_members["owner_membership"]
        target = platform_with_members["member_membership"]

        RolePermission.objects.create(
            role=owner.role,
            permission=can_change_member_role_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner)

        membership = RBACService.change_member_role(
            membership_id=target.id,
            new_role_id=platform_with_members["admin_role"].id,
            actor_context=actor_context,
        )

        assert membership.role == platform_with_members["admin_role"]

    def test_change_platform_member_role_without_permission(
        self, platform_with_members,
    ):
        """Changing platform role without permission fails."""
        owner = platform_with_members["owner_membership"]
        target = platform_with_members["member_membership"]

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner)

        with pytest.raises(PermissionDenied):
            RBACService.change_member_role(
                membership_id=target.id,
                new_role_id=platform_with_members["admin_role"].id,
                actor_context=actor_context,
            )


@pytest.mark.django_db
class TestPlatformUpdateMembershipStatus:
    """Tests for RBACService.update_membership_status with platform accounts."""

    def test_suspend_platform_member(
        self, platform_with_members, can_suspend_member_permission,
    ):
        """Platform owner can suspend platform member."""
        owner = platform_with_members["owner_membership"]
        target = platform_with_members["member_membership"]

        RolePermission.objects.create(
            role=owner.role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner)

        membership = RBACService.update_membership_status(
            membership_id=target.id,
            new_status=MembershipStatus.SUSPENDED,
            actor_context=actor_context,
            reason="Platform violation",
        )

        assert membership.status == MembershipStatus.SUSPENDED
        assert membership.status_reason == "Platform violation"

    def test_ban_platform_member(
        self, platform_with_members, can_ban_member_permission,
    ):
        """Platform owner can ban platform member."""
        owner = platform_with_members["owner_membership"]
        target = platform_with_members["member_membership"]

        RolePermission.objects.create(
            role=owner.role,
            permission=can_ban_member_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner)

        membership = RBACService.update_membership_status(
            membership_id=target.id,
            new_status=MembershipStatus.BANNED,
            actor_context=actor_context,
        )

        assert membership.status == MembershipStatus.BANNED

    def test_reactivate_platform_member(
        self, platform_with_members, can_suspend_member_permission,
    ):
        """Platform owner can reactivate suspended member."""
        owner = platform_with_members["owner_membership"]
        target = platform_with_members["member_membership"]
        target.status = MembershipStatus.SUSPENDED
        target.save()

        RolePermission.objects.create(
            role=owner.role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner)

        membership = RBACService.update_membership_status(
            membership_id=target.id,
            new_status=MembershipStatus.ACTIVE,
            actor_context=actor_context,
        )

        assert membership.status == MembershipStatus.ACTIVE


@pytest.mark.django_db
class TestPlatformMemberLeave:
    """Tests for RBACService.member_leave with platform accounts."""

    def test_platform_member_leave(self, platform_with_members):
        """Platform member can leave."""
        member = platform_with_members["member_membership"]

        membership = RBACService.member_leave(
            membership_id=member.id,
            user=member.user,
        )

        assert membership.status == MembershipStatus.LEFT

    def test_platform_owner_cannot_leave(self, platform_with_members):
        """Platform owner cannot leave."""
        owner = platform_with_members["owner_membership"]

        with pytest.raises(BusinessRuleViolation) as exc_info:
            RBACService.member_leave(
                membership_id=owner.id,
                user=owner.user,
            )
        assert "owner" in str(exc_info.value.message).lower()

    def test_platform_cannot_leave_other_membership(self, platform_with_members, user_factory):
        """User cannot leave another user's platform membership."""
        member = platform_with_members["member_membership"]
        random_user = user_factory()

        with pytest.raises(PermissionDenied) as exc_info:
            RBACService.member_leave(
                membership_id=member.id,
                user=random_user,
            )
        assert "own membership" in str(exc_info.value.message)


@pytest.mark.django_db
class TestPlatformCreateCustomRole:
    """Tests for RBACService.create_custom_role with platform accounts."""

    def test_create_custom_platform_role(
        self, platform, platform_owner_membership, can_create_role_permission,
    ):
        """Create custom platform role."""
        RolePermission.objects.create(
            role=platform_owner_membership.role,
            permission=can_create_role_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=platform_owner_membership)

        role = RBACService.create_custom_role(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            name="Content Reviewer",
            level=7,
            description="Reviews platform content",
            actor_context=actor_context,
        )

        assert role.name == "Content Reviewer"
        assert role.level == 7
        assert role.is_system_role is False
        assert role.account_type == AccountType.PLATFORM

    def test_create_platform_role_without_permission(
        self, platform, platform_owner_membership,
    ):
        """Creating platform role without permission is denied."""
        cache.clear()
        actor_context = RBACService.build_actor_context(membership=platform_owner_membership)

        with pytest.raises(PermissionDenied) as exc_info:
            RBACService.create_custom_role(
                account_type=AccountType.PLATFORM,
                account_id=platform.id,
                name="Unauthorized Role",
                level=5,
                actor_context=actor_context,
            )
        assert "can_create_role" in str(exc_info.value.message)

    def test_duplicate_platform_role_name(
        self, platform, platform_owner_membership, platform_admin_role, can_create_role_permission,
    ):
        """Duplicate platform role name is denied."""
        RolePermission.objects.create(
            role=platform_owner_membership.role,
            permission=can_create_role_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=platform_owner_membership)

        with pytest.raises(ConflictError) as exc_info:
            RBACService.create_custom_role(
                account_type=AccountType.PLATFORM,
                account_id=platform.id,
                name=platform_admin_role.name,
                level=6,
                actor_context=actor_context,
            )
        assert "already exists" in str(exc_info.value.message)


@pytest.mark.django_db
class TestPlatformDeleteRole:
    """Tests for RBACService.delete_role with platform accounts."""

    def test_delete_custom_platform_role(
        self, platform, platform_owner_membership, can_delete_role_permission,
    ):
        """Delete custom platform role."""
        RolePermission.objects.create(
            role=platform_owner_membership.role,
            permission=can_delete_role_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        custom_role = Role.objects.create(
            name="To Delete Plat",
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            level=7,
            is_system_role=False,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=platform_owner_membership)

        RBACService.delete_role(
            role_id=custom_role.id,
            actor_context=actor_context,
        )

        custom_role.refresh_from_db()
        assert custom_role.is_deleted is True

    def test_cannot_delete_system_platform_role(
        self, platform_owner_membership, platform_owner_role, can_delete_role_permission,
    ):
        """System platform roles cannot be deleted."""
        RolePermission.objects.create(
            role=platform_owner_membership.role,
            permission=can_delete_role_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=platform_owner_membership)

        with pytest.raises(PermissionDenied) as exc_info:
            RBACService.delete_role(
                role_id=platform_owner_role.id,
                actor_context=actor_context,
            )
        assert "System roles" in str(exc_info.value.message)

    def test_cannot_delete_platform_role_with_members(
        self, platform_with_members, can_delete_role_permission,
    ):
        """Platform role with active members cannot be deleted."""
        owner = platform_with_members["owner_membership"]
        admin_role = platform_with_members["admin_role"]

        RolePermission.objects.create(
            role=owner.role,
            permission=can_delete_role_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner)

        with pytest.raises(BusinessRuleViolation) as exc_info:
            RBACService.delete_role(
                role_id=admin_role.id,
                actor_context=actor_context,
            )
        assert "active member" in str(exc_info.value.message)


@pytest.mark.django_db
class TestPlatformUpdateRole:
    """Tests for RBACService.update_role with platform accounts."""

    def test_update_platform_role_name(
        self, platform, platform_owner_membership, can_edit_role_permission,
    ):
        """Update platform role name."""
        RolePermission.objects.create(
            role=platform_owner_membership.role,
            permission=can_edit_role_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        custom_role = Role.objects.create(
            name="Content Mod",
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            level=6,
            is_system_role=False,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=platform_owner_membership)

        role = RBACService.update_role(
            role_id=custom_role.id,
            name="Senior Content Mod",
            actor_context=actor_context,
        )

        assert role.name == "Senior Content Mod"

    def test_update_platform_system_role_denied(
        self, platform_owner_membership, platform_owner_role, can_edit_role_permission,
    ):
        """System platform roles cannot be updated."""
        RolePermission.objects.create(
            role=platform_owner_membership.role,
            permission=can_edit_role_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=platform_owner_membership)

        with pytest.raises(PermissionDenied) as exc_info:
            RBACService.update_role(
                role_id=platform_owner_role.id,
                name="New Name",
                actor_context=actor_context,
            )
        assert "system role" in str(exc_info.value.message).lower()


@pytest.mark.django_db
class TestPlatformAddPermissionToRole:
    """Tests for RBACService.add_permission_to_role with platform roles."""

    def test_add_platform_permission(self, platform_admin_role):
        """Add platform_only permission to platform role."""
        perm = Permission.objects.create(
            code="test_plat_add_perm",
            name="Test Add Perm",
            category="test",
            applicable_scopes=["platform_only"],
        )

        role_perm = RBACService.add_permission_to_role(
            role_id=platform_admin_role.id,
            permission_id=perm.id,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        assert role_perm.role == platform_admin_role
        assert role_perm.permission == perm
        assert role_perm.scope == PermissionScope.PLATFORM_ONLY

    def test_invalid_scope_for_platform_role(self, platform_admin_role):
        """Invalid scope denied for platform role."""
        perm = Permission.objects.create(
            code="test_plat_only_scope",
            name="Platform Only Scope",
            category="test",
            applicable_scopes=["platform_only"],
        )

        with pytest.raises(ValidationError) as exc_info:
            RBACService.add_permission_to_role(
                role_id=platform_admin_role.id,
                permission_id=perm.id,
                scope=PermissionScope.BUSINESS,
            )
        assert "not valid" in str(exc_info.value.message)


@pytest.mark.django_db
class TestPlatformRestoreMembership:
    """Tests for RBACService.restore_membership with platform accounts."""

    def test_restore_platform_membership(
        self, platform_with_members, can_remove_member_permission,
    ):
        """Restore deleted platform membership."""
        owner = platform_with_members["owner_membership"]
        target = platform_with_members["member_membership"]

        RolePermission.objects.create(
            role=owner.role,
            permission=can_remove_member_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        target.is_deleted = True
        target.status = MembershipStatus.REMOVED
        target.save()

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner)

        membership = RBACService.restore_membership(
            membership_id=target.id,
            actor_context=actor_context,
        )

        assert membership.is_deleted is False
        assert membership.status == MembershipStatus.ACTIVE
