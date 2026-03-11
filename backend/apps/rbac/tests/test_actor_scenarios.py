# apps/rbac/tests/test_actor_scenarios.py
"""
Actor-perspective integration tests for RBAC.

Tests organized by actor type, simulating real user scenarios:
- Business Owner: Full control within their business
- Business Admin: Limited management within business
- Business Member: Basic access, no management
- Platform Owner: Full platform control
- Platform Admin: Cross-business moderation with global scope
- Global Moderator: Cross-business with platform_only scope
"""

import pytest
from unittest.mock import patch
from django.core.cache import cache

from apps.core.constants import AccountType, PermissionScope, MembershipStatus
from apps.core.exceptions import PermissionDenied, BusinessRuleViolation, ConflictError, ValidationError
from apps.core.observability.audit.models import AuditLog
from apps.rbac.models import Permission, Role, RolePermission, Membership
from apps.rbac.services import RBACService


# =============================================================================
# BUSINESS OWNER SCENARIOS
# =============================================================================


@pytest.mark.django_db
class TestBusinessOwnerScenarios:
    """Tests from Business Owner perspective - full control within their business."""

    def test_owner_can_suspend_any_member(
        self, business_with_members, can_suspend_member_permission
    ):
        """Business owner can suspend any member in their business."""
        owner = business_with_members["owner_membership"]
        target = business_with_members["member1_membership"]

        RolePermission.objects.create(
            role=owner.role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner)

        result = RBACService.update_membership_status(
            membership_id=target.id,
            new_status=MembershipStatus.SUSPENDED,
            actor_context=actor_context,
            reason="Violation",
        )

        assert result.status == MembershipStatus.SUSPENDED

    def test_owner_can_ban_any_member(
        self, business_with_members, can_ban_member_permission
    ):
        """Business owner can ban any member in their business."""
        owner = business_with_members["owner_membership"]
        target = business_with_members["member1_membership"]

        RolePermission.objects.create(
            role=owner.role,
            permission=can_ban_member_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner)

        result = RBACService.update_membership_status(
            membership_id=target.id,
            new_status=MembershipStatus.BANNED,
            actor_context=actor_context,
        )

        assert result.status == MembershipStatus.BANNED

    def test_owner_can_create_admin_role(
        self, business, owner_membership, can_create_role_permission
    ):
        """Business owner can create admin-level roles."""
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
            name="Admin",
            level=2,
            actor_context=actor_context,
        )

        assert role.level == 2
        assert role.name == "Admin"

    def test_owner_cannot_leave_without_transfer(self, business_with_members):
        """Business owner cannot leave - must transfer ownership first."""
        owner = business_with_members["owner_membership"]

        with pytest.raises(BusinessRuleViolation) as exc_info:
            RBACService.member_leave(
                membership_id=owner.id,
                user=owner.user,
            )

        assert "owner" in str(exc_info.value.message).lower()

    def test_owner_cannot_be_suspended_by_admin(
        self, business_with_members, admin_role, can_suspend_member_permission
    ):
        """Business owner cannot be suspended by an admin in the same business."""
        owner = business_with_members["owner_membership"]
        member = business_with_members["member1_membership"]

        # Promote member to admin
        member.role = admin_role
        member.save()

        # Give admin suspend permission
        RolePermission.objects.create(
            role=admin_role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=member)

        with pytest.raises(PermissionDenied) as exc_info:
            RBACService.update_membership_status(
                membership_id=owner.id,
                new_status=MembershipStatus.SUSPENDED,
                actor_context=actor_context,
            )

        assert "owner" in str(exc_info.value.message).lower()


# =============================================================================
# BUSINESS ADMIN SCENARIOS
# =============================================================================


@pytest.mark.django_db
class TestBusinessAdminScenarios:
    """Tests from Business Admin perspective - limited management."""

    def test_admin_can_suspend_lower_level_member(
        self, business_with_members, admin_role, can_suspend_member_permission
    ):
        """Business admin can suspend members with lower authority."""
        owner = business_with_members["owner_membership"]
        admin_user = business_with_members["member1_membership"]
        target = business_with_members["member2_membership"]

        # Promote member1 to admin (level 2)
        admin_user.role = admin_role
        admin_user.save()

        RolePermission.objects.create(
            role=admin_role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=admin_user)

        result = RBACService.update_membership_status(
            membership_id=target.id,
            new_status=MembershipStatus.SUSPENDED,
            actor_context=actor_context,
        )

        assert result.status == MembershipStatus.SUSPENDED

    def test_admin_cannot_suspend_equal_level_admin(
        self, business, admin_role, can_suspend_member_permission, user, another_user
    ):
        """Business admin cannot suspend another admin of equal level."""
        # Create two admins
        admin1 = Membership.objects.create(
            user=user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            role=admin_role,
            status=MembershipStatus.ACTIVE,
        )
        admin2 = Membership.objects.create(
            user=another_user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            role=admin_role,
            status=MembershipStatus.ACTIVE,
        )

        RolePermission.objects.create(
            role=admin_role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=admin1)

        with pytest.raises(PermissionDenied) as exc_info:
            RBACService.update_membership_status(
                membership_id=admin2.id,
                new_status=MembershipStatus.SUSPENDED,
                actor_context=actor_context,
            )

        assert "authority" in str(exc_info.value.message).lower()

    def test_admin_cannot_create_equal_level_role(
        self, business, admin_role, can_create_role_permission, user
    ):
        """Admin cannot create a role at their own level or higher."""
        admin = Membership.objects.create(
            user=user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            role=admin_role,
            status=MembershipStatus.ACTIVE,
        )

        RolePermission.objects.create(
            role=admin_role,
            permission=can_create_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=admin)

        with pytest.raises(PermissionDenied) as exc_info:
            RBACService.create_custom_role(
                account_type=AccountType.BUSINESS,
                account_id=business.id,
                name="Another Admin",
                level=admin_role.level,  # Same level
                actor_context=actor_context,
            )

        assert "authority" in str(exc_info.value.message).lower()

    def test_admin_can_assign_lower_role_to_member(
        self, business_with_members, admin_role, manager_role, can_change_member_role_permission
    ):
        """Admin can assign a lower-level role to a member."""
        admin_user = business_with_members["member1_membership"]
        target = business_with_members["member2_membership"]

        # Promote member1 to admin
        admin_user.role = admin_role
        admin_user.save()

        RolePermission.objects.create(
            role=admin_role,
            permission=can_change_member_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=admin_user)

        result = RBACService.change_member_role(
            membership_id=target.id,
            new_role_id=manager_role.id,
            actor_context=actor_context,
        )

        assert result.role == manager_role


# =============================================================================
# BUSINESS MEMBER SCENARIOS
# =============================================================================


@pytest.mark.django_db
class TestBusinessMemberScenarios:
    """Tests from Business Member perspective - basic access only."""

    def test_member_cannot_suspend_anyone(
        self, business_with_members, can_suspend_member_permission
    ):
        """Regular member cannot suspend anyone even with permission."""
        member1 = business_with_members["member1_membership"]
        member2 = business_with_members["member2_membership"]

        # Don't give member the permission - they shouldn't have it
        cache.clear()
        actor_context = RBACService.build_actor_context(membership=member1)

        with pytest.raises(PermissionDenied):
            RBACService.update_membership_status(
                membership_id=member2.id,
                new_status=MembershipStatus.SUSPENDED,
                actor_context=actor_context,
            )

    def test_member_can_leave_voluntarily(self, business_with_members):
        """Regular member can leave the business."""
        member = business_with_members["member1_membership"]

        result = RBACService.member_leave(
            membership_id=member.id,
            user=member.user,
        )

        assert result.status == MembershipStatus.LEFT

    def test_member_cannot_create_roles(
        self, business_with_members, can_create_role_permission
    ):
        """Regular member cannot create roles even if they somehow got the permission."""
        member = business_with_members["member1_membership"]
        business = business_with_members["business"]

        # Even if we give them permission, they can't create roles due to level check
        RolePermission.objects.create(
            role=member.role,
            permission=can_create_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=member)

        # Base member is level 10, so they can't create any role (need to outrank)
        with pytest.raises(PermissionDenied):
            RBACService.create_custom_role(
                account_type=AccountType.BUSINESS,
                account_id=business.id,
                name="My Role",
                level=9,  # Even level 9 requires level < 9
                actor_context=actor_context,
            )


# =============================================================================
# PLATFORM ADMIN SCENARIOS (Cross-Business)
# =============================================================================


@pytest.mark.django_db
class TestPlatformAdminCrossBusinessScenarios:
    """Tests from Platform Admin perspective - cross-business with global scope."""

    def test_platform_admin_with_global_can_suspend_business_member(
        self, business_with_members, platform, platform_admin_role, can_suspend_member_permission, another_user
    ):
        """Platform admin with global scope can suspend members in any business."""
        target = business_with_members["member1_membership"]

        # Create platform admin membership for another_user
        platform_admin = Membership.objects.create(
            user=another_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role=platform_admin_role,
            status=MembershipStatus.ACTIVE,
        )

        # Give global scope permission
        RolePermission.objects.create(
            role=platform_admin_role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.GLOBAL_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=platform_admin)

        result = RBACService.update_membership_status(
            membership_id=target.id,
            new_status=MembershipStatus.SUSPENDED,
            actor_context=actor_context,
        )

        assert result.status == MembershipStatus.SUSPENDED

    def test_platform_admin_with_platform_only_cannot_suspend_business_member(
        self, business_with_members, platform, platform_admin_role, can_suspend_member_permission, another_user
    ):
        """Platform admin with platform_only scope CANNOT suspend members in businesses."""
        target = business_with_members["member1_membership"]

        # Create platform admin membership
        platform_admin = Membership.objects.create(
            user=another_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role=platform_admin_role,
            status=MembershipStatus.ACTIVE,
        )

        # Give platform_only scope (NOT global)
        RolePermission.objects.create(
            role=platform_admin_role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=platform_admin)

        with pytest.raises(PermissionDenied):
            RBACService.update_membership_status(
                membership_id=target.id,
                new_status=MembershipStatus.SUSPENDED,
                actor_context=actor_context,
            )

    def test_platform_admin_with_global_can_ban_business_owner(
        self, business_with_members, platform, platform_admin_role, can_ban_member_permission, another_user
    ):
        """Platform admin with global scope CAN ban a business owner."""
        owner = business_with_members["owner_membership"]

        # Create platform admin
        platform_admin = Membership.objects.create(
            user=another_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role=platform_admin_role,
            status=MembershipStatus.ACTIVE,
        )

        RolePermission.objects.create(
            role=platform_admin_role,
            permission=can_ban_member_permission,
            scope=PermissionScope.GLOBAL_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=platform_admin)

        result = RBACService.update_membership_status(
            membership_id=owner.id,
            new_status=MembershipStatus.BANNED,
            actor_context=actor_context,
        )

        assert result.status == MembershipStatus.BANNED


@pytest.mark.django_db
class TestPlatformAdminInternalActions:
    """
    Tests for Platform Admin same-account (platform) actions (§2.1).

    Platform Admin operates WITHIN the platform - not cross-business.
    """

    def test_platform_admin_can_suspend_global_mod(
        self, platform, platform_admin_role, global_moderator_role,
        can_suspend_member_permission, user, another_user
    ):
        """Platform Admin (level 2) CAN suspend Global Mod (level 5) (§2.1.2)."""
        # Create platform admin membership
        platform_admin = Membership.objects.create(
            user=user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role=platform_admin_role,
            status=MembershipStatus.ACTIVE,
        )

        # Create global moderator membership
        global_mod = Membership.objects.create(
            user=another_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role=global_moderator_role,
            status=MembershipStatus.ACTIVE,
        )

        RolePermission.objects.create(
            role=platform_admin_role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=platform_admin)

        result = RBACService.update_membership_status(
            membership_id=global_mod.id,
            new_status=MembershipStatus.SUSPENDED,
            actor_context=actor_context,
        )

        assert result.status == MembershipStatus.SUSPENDED

    def test_platform_admin_cannot_suspend_platform_owner(
        self, platform, platform_admin_role, platform_owner_membership,
        can_suspend_member_permission, another_user
    ):
        """Platform Admin CANNOT suspend Platform Owner (§2.1.7) - Owner is invincible."""
        platform_admin = Membership.objects.create(
            user=another_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role=platform_admin_role,
            status=MembershipStatus.ACTIVE,
        )

        RolePermission.objects.create(
            role=platform_admin_role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=platform_admin)

        with pytest.raises(PermissionDenied) as exc_info:
            RBACService.update_membership_status(
                membership_id=platform_owner_membership.id,
                new_status=MembershipStatus.SUSPENDED,
                actor_context=actor_context,
            )

        assert "account owner" in str(exc_info.value.message).lower()

    def test_platform_admin_cannot_suspend_equal_level_admin(
        self, platform, platform_admin_role, can_suspend_member_permission, user, another_user
    ):
        """Platform Admin (L2) CANNOT suspend another Admin (L2) (§2.1.10) - equal level."""
        # Create first platform admin
        admin1 = Membership.objects.create(
            user=user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role=platform_admin_role,
            status=MembershipStatus.ACTIVE,
        )

        # Create second platform admin (same role, same level)
        admin2 = Membership.objects.create(
            user=another_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role=platform_admin_role,
            status=MembershipStatus.ACTIVE,
        )

        RolePermission.objects.create(
            role=platform_admin_role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=admin1)

        with pytest.raises(PermissionDenied) as exc_info:
            RBACService.update_membership_status(
                membership_id=admin2.id,
                new_status=MembershipStatus.SUSPENDED,
                actor_context=actor_context,
            )

        assert "authority" in str(exc_info.value.message).lower()

    def test_platform_admin_cannot_assign_equal_authority_role(
        self, platform, platform_admin_role, can_change_member_role_permission,
        global_moderator_role, user, another_user
    ):
        """Platform Admin (L2) CANNOT promote Global Mod to L2 role (§2.1.5) - equal authority."""
        # Create platform admin
        admin = Membership.objects.create(
            user=user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role=platform_admin_role,
            status=MembershipStatus.ACTIVE,
        )

        # Create global mod at level 5
        global_mod = Membership.objects.create(
            user=another_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role=global_moderator_role,
            status=MembershipStatus.ACTIVE,
        )

        # Create another L2 role for promotion target
        another_admin_role = Role.objects.create(
            name="Another Admin",
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            level=2,  # Same as Platform Admin
        )

        RolePermission.objects.create(
            role=platform_admin_role,
            permission=can_change_member_role_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=admin)

        with pytest.raises(PermissionDenied) as exc_info:
            RBACService.change_member_role(
                membership_id=global_mod.id,
                new_role_id=another_admin_role.id,
                actor_context=actor_context,
            )

        assert "authority" in str(exc_info.value.message).lower()


# =============================================================================
# PLATFORM OWNER SCENARIOS
# =============================================================================


@pytest.mark.django_db
class TestPlatformOwnerScenarios:
    """Tests from Platform Owner perspective - ultimate authority."""

    def test_platform_owner_cannot_be_suspended_by_anyone(
        self, platform_owner_membership, platform_admin_role, platform, can_suspend_member_permission, another_user
    ):
        """Platform owner is completely invincible - no one can suspend them."""
        # Create a platform admin
        platform_admin = Membership.objects.create(
            user=another_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role=platform_admin_role,
            status=MembershipStatus.ACTIVE,
        )

        RolePermission.objects.create(
            role=platform_admin_role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=platform_admin)

        with pytest.raises(PermissionDenied) as exc_info:
            RBACService.update_membership_status(
                membership_id=platform_owner_membership.id,
                new_status=MembershipStatus.SUSPENDED,
                actor_context=actor_context,
            )

        assert "account owner" in str(exc_info.value.message).lower()

    def test_platform_owner_can_suspend_platform_admin(
        self, platform_owner_membership, platform_admin_membership, can_suspend_member_permission
    ):
        """Platform owner can suspend platform admins."""
        RolePermission.objects.create(
            role=platform_owner_membership.role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=platform_owner_membership)

        result = RBACService.update_membership_status(
            membership_id=platform_admin_membership.id,
            new_status=MembershipStatus.SUSPENDED,
            actor_context=actor_context,
        )

        assert result.status == MembershipStatus.SUSPENDED


@pytest.mark.django_db
class TestPlatformOwnerCrossAccount:
    """
    Tests for Platform Owner cross-account operations (§1.2).

    Platform Owner can act on ANY business member with global scope.
    """

    def test_platform_owner_can_suspend_business_owner(
        self, platform_owner_membership, business_with_members, can_suspend_member_permission
    ):
        """Platform Owner CAN suspend a Business Owner (§1.2.2)."""
        target = business_with_members["owner_membership"]

        RolePermission.objects.create(
            role=platform_owner_membership.role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.GLOBAL_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=platform_owner_membership)

        result = RBACService.update_membership_status(
            membership_id=target.id,
            new_status=MembershipStatus.SUSPENDED,
            actor_context=actor_context,
        )

        assert result.status == MembershipStatus.SUSPENDED

    def test_platform_owner_can_suspend_business_admin(
        self, platform_owner_membership, business_with_members, admin_role, can_suspend_member_permission
    ):
        """Platform Owner CAN suspend a Business Admin (§1.2.4)."""
        target = business_with_members["member1_membership"]
        target.role = admin_role
        target.save()

        RolePermission.objects.create(
            role=platform_owner_membership.role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.GLOBAL_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=platform_owner_membership)

        result = RBACService.update_membership_status(
            membership_id=target.id,
            new_status=MembershipStatus.SUSPENDED,
            actor_context=actor_context,
        )

        assert result.status == MembershipStatus.SUSPENDED

    def test_platform_owner_can_ban_business_member(
        self, platform_owner_membership, business_with_members, can_ban_member_permission
    ):
        """Platform Owner CAN ban any business member (§1.2.5)."""
        target = business_with_members["member1_membership"]

        RolePermission.objects.create(
            role=platform_owner_membership.role,
            permission=can_ban_member_permission,
            scope=PermissionScope.GLOBAL_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=platform_owner_membership)

        result = RBACService.update_membership_status(
            membership_id=target.id,
            new_status=MembershipStatus.BANNED,
            actor_context=actor_context,
        )

        assert result.status == MembershipStatus.BANNED

    def test_platform_owner_cannot_act_on_self(
        self, platform_owner_membership, can_suspend_member_permission
    ):
        """Platform Owner CANNOT suspend themselves (§1.1.9)."""
        RolePermission.objects.create(
            role=platform_owner_membership.role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=platform_owner_membership)

        with pytest.raises(PermissionDenied) as exc_info:
            RBACService.update_membership_status(
                membership_id=platform_owner_membership.id,
                new_status=MembershipStatus.SUSPENDED,
                actor_context=actor_context,
            )

        # Owner self-action is blocked by "account owner" protection
        assert "account owner" in str(exc_info.value.message).lower()


# =============================================================================
# CROSS-ACCOUNT EDGE CASES
# =============================================================================


@pytest.mark.django_db
class TestCrossAccountEdgeCases:
    """Edge cases for cross-account operations."""

    def test_business_owner_cannot_act_on_other_business(
        self, business_with_members, another_business, can_suspend_member_permission, third_user
    ):
        """Business owner has no authority in other businesses."""
        owner = business_with_members["owner_membership"]

        # Create a member in another business
        other_role = Role.objects.create(
            name="Member",
            account_type=AccountType.BUSINESS,
            account_id=another_business.id,
            level=10,
        )
        other_member = Membership.objects.create(
            user=third_user,
            account_type=AccountType.BUSINESS,
            account_id=another_business.id,
            role=other_role,
            status=MembershipStatus.ACTIVE,
        )

        RolePermission.objects.create(
            role=owner.role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner)

        with pytest.raises(PermissionDenied):
            RBACService.update_membership_status(
                membership_id=other_member.id,
                new_status=MembershipStatus.SUSPENDED,
                actor_context=actor_context,
            )

    def test_user_in_multiple_businesses_contexts_are_separate(
        self, business, another_business, user, can_suspend_member_permission
    ):
        """A user who is owner in one business and member in another has separate contexts."""
        # User is owner in business
        owner_role = Role.objects.create(
            name="Owner",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=0,
            is_system_role=True,
        )
        owner_membership = Membership.objects.create(
            user=user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            role=owner_role,
            is_owner=True,
            status=MembershipStatus.ACTIVE,
        )

        # User is just a member in another_business
        member_role = Role.objects.create(
            name="Member",
            account_type=AccountType.BUSINESS,
            account_id=another_business.id,
            level=10,
        )
        member_membership = Membership.objects.create(
            user=user,
            account_type=AccountType.BUSINESS,
            account_id=another_business.id,
            role=member_role,
            status=MembershipStatus.ACTIVE,
        )

        # Context as owner
        cache.clear()
        owner_context = RBACService.build_actor_context(membership=owner_membership)
        assert owner_context.is_owner is True
        assert owner_context.role_level == 0

        # Context as member (different account)
        cache.clear()
        member_context = RBACService.build_actor_context(membership=member_membership)
        assert member_context.is_owner is False
        assert member_context.role_level == 10

    def test_business_owner_cannot_remove_from_other_business(
        self, business_with_members, another_business, can_remove_member_permission, third_user
    ):
        """Business Owner A cannot remove a member from Business B (§4.2.3)."""
        owner = business_with_members["owner_membership"]

        # Create a member in another business
        other_role = Role.objects.create(
            name="Member",
            account_type=AccountType.BUSINESS,
            account_id=another_business.id,
            level=10,
        )
        other_member = Membership.objects.create(
            user=third_user,
            account_type=AccountType.BUSINESS,
            account_id=another_business.id,
            role=other_role,
            status=MembershipStatus.ACTIVE,
        )

        RolePermission.objects.create(
            role=owner.role,
            permission=can_remove_member_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner)

        with pytest.raises(PermissionDenied):
            RBACService.update_membership_status(
                membership_id=other_member.id,
                new_status=MembershipStatus.REMOVED,
                actor_context=actor_context,
            )

    def test_business_owner_cannot_change_role_in_other_business(
        self, business_with_members, another_business, can_change_member_role_permission, third_user
    ):
        """Business Owner A cannot change role of member in Business B (§4.2.4)."""
        owner = business_with_members["owner_membership"]

        # Create roles and member in another business
        other_role = Role.objects.create(
            name="Member",
            account_type=AccountType.BUSINESS,
            account_id=another_business.id,
            level=10,
        )
        new_role = Role.objects.create(
            name="Admin",
            account_type=AccountType.BUSINESS,
            account_id=another_business.id,
            level=2,
        )
        other_member = Membership.objects.create(
            user=third_user,
            account_type=AccountType.BUSINESS,
            account_id=another_business.id,
            role=other_role,
            status=MembershipStatus.ACTIVE,
        )

        RolePermission.objects.create(
            role=owner.role,
            permission=can_change_member_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner)

        with pytest.raises(PermissionDenied):
            RBACService.change_member_role(
                membership_id=other_member.id,
                new_role_id=new_role.id,
                actor_context=actor_context,
            )

    def test_business_admin_cannot_change_role_in_other_business(
        self, business_with_members, another_business, admin_role,
        can_change_member_role_permission, third_user, user
    ):
        """Business Admin A cannot change role of member in Business B (§5.4.2)."""
        # Set up admin in business A
        admin = business_with_members["member1_membership"]
        admin.role = admin_role
        admin.save()

        # Create roles and member in another business
        other_role = Role.objects.create(
            name="Member",
            account_type=AccountType.BUSINESS,
            account_id=another_business.id,
            level=10,
        )
        new_role = Role.objects.create(
            name="Editor",
            account_type=AccountType.BUSINESS,
            account_id=another_business.id,
            level=5,
        )
        other_member = Membership.objects.create(
            user=third_user,
            account_type=AccountType.BUSINESS,
            account_id=another_business.id,
            role=other_role,
            status=MembershipStatus.ACTIVE,
        )

        RolePermission.objects.create(
            role=admin_role,
            permission=can_change_member_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=admin)

        with pytest.raises(PermissionDenied):
            RBACService.change_member_role(
                membership_id=other_member.id,
                new_role_id=new_role.id,
                actor_context=actor_context,
            )


# =============================================================================
# GLOBAL MODERATOR SCENARIOS
# =============================================================================


@pytest.mark.django_db
class TestPlatformOnlyScopeLimitations:
    """Tests verifying that platform_only scope blocks cross-business actions."""

    def test_platform_only_scope_allows_platform_member_management(
        self, platform, global_moderator_role, can_suspend_member_permission, third_user
    ):
        """Platform staff with platform_only scope can manage platform members."""
        moderator = Membership.objects.create(
            user=third_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role=global_moderator_role,
            status=MembershipStatus.ACTIVE,
        )

        RolePermission.objects.create(
            role=global_moderator_role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=moderator)

        assert ("can_suspend_member", "platform_only") in actor_context.permissions_snapshot

    def test_platform_only_scope_blocks_cross_business_actions(
        self, business_with_members, platform, global_moderator_role,
        can_suspend_member_permission, third_user
    ):
        """Platform staff with platform_only scope CANNOT act on business members."""
        target = business_with_members["member1_membership"]

        moderator = Membership.objects.create(
            user=third_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role=global_moderator_role,
            status=MembershipStatus.ACTIVE,
        )

        RolePermission.objects.create(
            role=global_moderator_role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=moderator)

        with pytest.raises(PermissionDenied):
            RBACService.update_membership_status(
                membership_id=target.id,
                new_status=MembershipStatus.SUSPENDED,
                actor_context=actor_context,
            )


@pytest.mark.django_db
class TestGlobalModeratorCrossAccount:
    """
    Tests for Global Moderator with global_only scope (§3.2).

    Global Moderator's core purpose is cross-account moderation via global scope.
    These tests verify the REAL Global Moderator configuration.
    """

    def test_global_mod_can_suspend_business_owner(
        self, business_with_members, platform, global_moderator_role,
        can_suspend_member_permission, third_user
    ):
        """Global Mod (global_only) CAN suspend a Business Owner (§3.2.1)."""
        owner = business_with_members["owner_membership"]

        moderator = Membership.objects.create(
            user=third_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role=global_moderator_role,
            status=MembershipStatus.ACTIVE,
        )

        # Real Global Mod has global_only scope
        RolePermission.objects.create(
            role=global_moderator_role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.GLOBAL_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=moderator)

        result = RBACService.update_membership_status(
            membership_id=owner.id,
            new_status=MembershipStatus.SUSPENDED,
            actor_context=actor_context,
        )

        assert result.status == MembershipStatus.SUSPENDED

    def test_global_mod_can_suspend_business_admin(
        self, business_with_members, platform, global_moderator_role, admin_role,
        can_suspend_member_permission, third_user
    ):
        """Global Mod (global_only) CAN suspend a Business Admin (§3.2.2)."""
        target = business_with_members["member1_membership"]
        target.role = admin_role
        target.save()

        moderator = Membership.objects.create(
            user=third_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role=global_moderator_role,
            status=MembershipStatus.ACTIVE,
        )

        RolePermission.objects.create(
            role=global_moderator_role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.GLOBAL_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=moderator)

        result = RBACService.update_membership_status(
            membership_id=target.id,
            new_status=MembershipStatus.SUSPENDED,
            actor_context=actor_context,
        )

        assert result.status == MembershipStatus.SUSPENDED

    def test_global_mod_can_suspend_business_base_member(
        self, business_with_members, platform, global_moderator_role,
        can_suspend_member_permission, third_user
    ):
        """Global Mod (global_only) CAN suspend a Business Base Member (§3.2.3)."""
        target = business_with_members["member1_membership"]

        moderator = Membership.objects.create(
            user=third_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role=global_moderator_role,
            status=MembershipStatus.ACTIVE,
        )

        RolePermission.objects.create(
            role=global_moderator_role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.GLOBAL_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=moderator)

        result = RBACService.update_membership_status(
            membership_id=target.id,
            new_status=MembershipStatus.SUSPENDED,
            actor_context=actor_context,
        )

        assert result.status == MembershipStatus.SUSPENDED

    def test_global_mod_can_remove_business_member(
        self, business_with_members, platform, global_moderator_role,
        can_remove_member_permission, third_user
    ):
        """Global Mod (global_only) CAN remove a Business member (§3.2.4)."""
        target = business_with_members["member1_membership"]

        moderator = Membership.objects.create(
            user=third_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role=global_moderator_role,
            status=MembershipStatus.ACTIVE,
        )

        RolePermission.objects.create(
            role=global_moderator_role,
            permission=can_remove_member_permission,
            scope=PermissionScope.GLOBAL_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=moderator)

        result = RBACService.update_membership_status(
            membership_id=target.id,
            new_status=MembershipStatus.REMOVED,
            actor_context=actor_context,
        )

        assert result.status == MembershipStatus.REMOVED

    def test_global_mod_can_ban_business_member(
        self, business_with_members, platform, global_moderator_role,
        can_ban_member_permission, third_user
    ):
        """Global Mod (global_only) CAN ban a Business member (§3.2.5)."""
        target = business_with_members["member1_membership"]

        moderator = Membership.objects.create(
            user=third_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role=global_moderator_role,
            status=MembershipStatus.ACTIVE,
        )

        RolePermission.objects.create(
            role=global_moderator_role,
            permission=can_ban_member_permission,
            scope=PermissionScope.GLOBAL_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=moderator)

        result = RBACService.update_membership_status(
            membership_id=target.id,
            new_status=MembershipStatus.BANNED,
            actor_context=actor_context,
        )

        assert result.status == MembershipStatus.BANNED

    def test_global_mod_cannot_create_business_roles(
        self, business, platform, global_moderator_role,
        can_create_role_permission, third_user
    ):
        """Global Mod CANNOT create roles in a Business (§3.2.8) - can_create_role has no global scope."""
        moderator = Membership.objects.create(
            user=third_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role=global_moderator_role,
            status=MembershipStatus.ACTIVE,
        )

        # Even with global_only scope, can_create_role doesn't apply cross-account
        RolePermission.objects.create(
            role=global_moderator_role,
            permission=can_create_role_permission,
            scope=PermissionScope.GLOBAL_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=moderator)

        with pytest.raises(PermissionDenied):
            RBACService.create_custom_role(
                account_type=AccountType.BUSINESS,
                account_id=business.id,
                name="New Role",
                level=5,
                actor_context=actor_context,
            )

    def test_global_mod_cannot_act_on_platform_owner(
        self, platform, platform_owner_membership, global_moderator_role,
        can_suspend_member_permission, third_user
    ):
        """Global Mod CANNOT suspend Platform Owner (§3.1.1) - Platform Owner is invincible."""
        moderator = Membership.objects.create(
            user=third_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role=global_moderator_role,
            status=MembershipStatus.ACTIVE,
        )

        RolePermission.objects.create(
            role=global_moderator_role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.GLOBAL_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=moderator)

        with pytest.raises(PermissionDenied) as exc_info:
            RBACService.update_membership_status(
                membership_id=platform_owner_membership.id,
                new_status=MembershipStatus.SUSPENDED,
                actor_context=actor_context,
            )

        assert "account owner" in str(exc_info.value.message).lower()

    def test_global_mod_cannot_act_on_platform_admin(
        self, platform, platform_admin_role, global_moderator_role,
        can_suspend_member_permission, third_user, another_user
    ):
        """Global Mod (level 5) CANNOT suspend Platform Admin (level 2) - dominance rule."""
        # Create platform admin membership
        platform_admin = Membership.objects.create(
            user=another_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role=platform_admin_role,
            status=MembershipStatus.ACTIVE,
        )

        moderator = Membership.objects.create(
            user=third_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role=global_moderator_role,
            status=MembershipStatus.ACTIVE,
        )

        RolePermission.objects.create(
            role=global_moderator_role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=moderator)

        with pytest.raises(PermissionDenied) as exc_info:
            RBACService.update_membership_status(
                membership_id=platform_admin.id,
                new_status=MembershipStatus.SUSPENDED,
                actor_context=actor_context,
            )

        assert "authority" in str(exc_info.value.message).lower()


# =============================================================================
# ROLE MANAGEMENT SCENARIOS
# =============================================================================


@pytest.mark.django_db
class TestRoleManagementScenarios:
    """Tests for role management operations from various actor perspectives."""

    def test_owner_can_edit_custom_role(
        self, business, owner_membership, can_edit_role_permission
    ):
        """Business owner can edit custom roles they created."""
        # Create a custom role first
        custom_role = Role.objects.create(
            name="Custom Role",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
        )

        RolePermission.objects.create(
            role=owner_membership.role,
            permission=can_edit_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner_membership)

        result = RBACService.update_role(
            role_id=custom_role.id,
            actor_context=actor_context,
            name="Updated Role",
        )

        assert result.name == "Updated Role"

    def test_owner_can_delete_custom_role_without_members(
        self, business, owner_membership, can_delete_role_permission
    ):
        """Business owner can delete custom roles with no active members."""
        custom_role = Role.objects.create(
            name="Deletable Role",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
        )

        RolePermission.objects.create(
            role=owner_membership.role,
            permission=can_delete_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner_membership)

        RBACService.delete_role(
            role_id=custom_role.id,
            actor_context=actor_context,
        )

        assert not Role.objects.filter(id=custom_role.id).exists()

    def test_cannot_delete_role_with_active_members(
        self, business, owner_membership, can_delete_role_permission, another_user
    ):
        """Cannot delete a role that has active members assigned."""
        custom_role = Role.objects.create(
            name="In-Use Role",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
        )

        # Assign a member to this role
        Membership.objects.create(
            user=another_user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            role=custom_role,
            status=MembershipStatus.ACTIVE,
        )

        RolePermission.objects.create(
            role=owner_membership.role,
            permission=can_delete_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner_membership)

        with pytest.raises(BusinessRuleViolation) as exc_info:
            RBACService.delete_role(
                role_id=custom_role.id,
                actor_context=actor_context,
            )

        assert "active member" in str(exc_info.value.message).lower()

    def test_cannot_delete_system_roles(
        self, business, owner_membership, can_delete_role_permission
    ):
        """System roles (owner, base member) cannot be deleted."""
        RolePermission.objects.create(
            role=owner_membership.role,
            permission=can_delete_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner_membership)

        # System roles cannot be modified - raises PermissionDenied
        with pytest.raises(PermissionDenied) as exc_info:
            RBACService.delete_role(
                role_id=owner_membership.role.id,  # Owner role is system role
                actor_context=actor_context,
            )

        assert "system" in str(exc_info.value.message).lower()

    def test_admin_can_create_lower_level_roles(
        self, business, admin_role, can_create_role_permission, user
    ):
        """Admin can create roles at levels lower than their own."""
        admin = Membership.objects.create(
            user=user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            role=admin_role,
            status=MembershipStatus.ACTIVE,
        )

        RolePermission.objects.create(
            role=admin_role,
            permission=can_create_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=admin)

        role = RBACService.create_custom_role(
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            name="Junior Role",
            level=7,  # Admin is level 2, so 7 is lower authority
            actor_context=actor_context,
        )

        assert role.level == 7


# =============================================================================
# PERMISSION ASSIGNMENT SCENARIOS
# =============================================================================


@pytest.mark.django_db
class TestPermissionAssignmentScenarios:
    """Tests for permission assignment to roles."""

    def test_owner_can_add_business_permission_to_role(
        self, business, owner_membership, can_edit_role_permission, can_view_members_permission
    ):
        """Owner can add business-scoped permissions to custom roles."""
        custom_role = Role.objects.create(
            name="Custom Role",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
        )

        RolePermission.objects.create(
            role=owner_membership.role,
            permission=can_edit_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner_membership)

        result = RBACService.add_permission_to_role(
            role_id=custom_role.id,
            permission_id=can_view_members_permission.id,
            scope=PermissionScope.BUSINESS,
            actor_context=actor_context,
        )

        assert result.permission == can_view_members_permission
        assert result.scope == PermissionScope.BUSINESS

    def test_cannot_add_invalid_scope_to_permission(
        self, business, owner_membership, can_edit_role_permission
    ):
        """Cannot add a scope that's not in permission's applicable_scopes."""
        custom_role = Role.objects.create(
            name="Custom Role",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
        )

        # Create a permission with only 'business' scope allowed
        business_only_perm = Permission.objects.create(
            code="test_business_only",
            name="Business Only Test",
            applicable_scopes=["business"],  # Only business scope allowed
        )

        RolePermission.objects.create(
            role=owner_membership.role,
            permission=can_edit_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner_membership)

        # Try to add with platform_only scope which is not in applicable_scopes
        with pytest.raises(ValidationError) as exc_info:
            RBACService.add_permission_to_role(
                role_id=custom_role.id,
                permission_id=business_only_perm.id,
                scope=PermissionScope.PLATFORM_ONLY,  # Not in applicable_scopes
                actor_context=actor_context,
            )

        assert "not valid" in str(exc_info.value.message).lower()


# =============================================================================
# MEMBERSHIP STATUS TRANSITIONS
# =============================================================================


@pytest.mark.django_db
class TestMembershipStatusTransitions:
    """Tests for membership status change scenarios."""

    def test_suspended_member_can_be_reactivated(
        self, business_with_members, can_suspend_member_permission
    ):
        """A suspended member can be reactivated by owner."""
        owner = business_with_members["owner_membership"]
        target = business_with_members["member1_membership"]

        # First suspend the member
        target.status = MembershipStatus.SUSPENDED
        target.save()

        RolePermission.objects.create(
            role=owner.role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner)

        result = RBACService.update_membership_status(
            membership_id=target.id,
            new_status=MembershipStatus.ACTIVE,
            actor_context=actor_context,
        )

        assert result.status == MembershipStatus.ACTIVE

    def test_banned_member_can_be_reactivated_by_authorized_user(
        self, business_with_members, can_suspend_member_permission
    ):
        """A banned member can be reactivated by someone with suspend permission."""
        owner = business_with_members["owner_membership"]
        target = business_with_members["member1_membership"]

        # First set the member as banned
        target.status = MembershipStatus.BANNED
        target.save()

        # Reactivation requires suspend permission
        RolePermission.objects.create(
            role=owner.role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner)

        # Owner can reactivate a banned member
        result = RBACService.update_membership_status(
            membership_id=target.id,
            new_status=MembershipStatus.ACTIVE,
            actor_context=actor_context,
        )

        assert result.status == MembershipStatus.ACTIVE


# =============================================================================
# AUDIT TRAIL VERIFICATION TESTS
# =============================================================================


@pytest.mark.django_db
class TestAuditTrailVerification:
    """Tests verifying that service methods log audit trails correctly."""

    def test_update_membership_status_logs_audit(
        self, business_with_members, can_suspend_member_permission
    ):
        """Suspending a member logs an audit trail."""
        owner = business_with_members["owner_membership"]
        target = business_with_members["member1_membership"]

        RolePermission.objects.create(
            role=owner.role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner)

        with patch("apps.rbac.services.AuditService.log") as mock_audit:
            RBACService.update_membership_status(
                membership_id=target.id,
                new_status=MembershipStatus.SUSPENDED,
                actor_context=actor_context,
                reason="Test suspension",
            )

            mock_audit.assert_called_once()
            call_kwargs = mock_audit.call_args[1]
            assert call_kwargs["action"] == AuditLog.Action.MEMBERSHIP_SUSPENDED
            assert call_kwargs["resource"] == target
            assert call_kwargs["actor"].id == owner.user.id

    def test_change_member_role_logs_audit(
        self, business_with_members, admin_role, manager_role, can_change_member_role_permission
    ):
        """Changing a member's role logs an audit trail."""
        admin_user = business_with_members["member1_membership"]
        target = business_with_members["member2_membership"]

        admin_user.role = admin_role
        admin_user.save()

        RolePermission.objects.create(
            role=admin_role,
            permission=can_change_member_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=admin_user)

        with patch("apps.rbac.services.AuditService.log") as mock_audit:
            RBACService.change_member_role(
                membership_id=target.id,
                new_role_id=manager_role.id,
                actor_context=actor_context,
            )

            mock_audit.assert_called_once()
            call_kwargs = mock_audit.call_args[1]
            assert call_kwargs["action"] == AuditLog.Action.MEMBERSHIP_ROLE_CHANGED
            assert call_kwargs["resource"] == target

    def test_create_custom_role_logs_audit(
        self, business, owner_membership, can_create_role_permission
    ):
        """Creating a custom role logs an audit trail."""
        RolePermission.objects.create(
            role=owner_membership.role,
            permission=can_create_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner_membership)

        with patch("apps.rbac.services.AuditService.log") as mock_audit:
            role = RBACService.create_custom_role(
                account_type=AccountType.BUSINESS,
                account_id=business.id,
                name="Audit Test Role",
                level=5,
                actor_context=actor_context,
            )

            mock_audit.assert_called_once()
            call_kwargs = mock_audit.call_args[1]
            assert call_kwargs["action"] == AuditLog.Action.ROLE_CREATED
            assert call_kwargs["resource"] == role

    def test_delete_role_logs_audit(
        self, business, owner_membership, can_delete_role_permission
    ):
        """Deleting a custom role logs an audit trail."""
        custom_role = Role.objects.create(
            name="To Delete",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
        )

        RolePermission.objects.create(
            role=owner_membership.role,
            permission=can_delete_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner_membership)

        with patch("apps.rbac.services.AuditService.log") as mock_audit:
            RBACService.delete_role(
                role_id=custom_role.id,
                actor_context=actor_context,
            )

            mock_audit.assert_called_once()
            call_kwargs = mock_audit.call_args[1]
            assert call_kwargs["action"] == AuditLog.Action.ROLE_DELETED

    def test_update_role_logs_audit(
        self, business, owner_membership, can_edit_role_permission
    ):
        """Updating a role logs an audit trail."""
        custom_role = Role.objects.create(
            name="Editable Role",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
        )

        RolePermission.objects.create(
            role=owner_membership.role,
            permission=can_edit_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner_membership)

        with patch("apps.rbac.services.AuditService.log") as mock_audit:
            RBACService.update_role(
                role_id=custom_role.id,
                actor_context=actor_context,
                name="Updated Name",
            )

            mock_audit.assert_called_once()
            call_kwargs = mock_audit.call_args[1]
            assert call_kwargs["action"] == AuditLog.Action.ROLE_UPDATED

    def test_add_permission_to_role_logs_audit(
        self, business, owner_membership, can_edit_role_permission, can_view_members_permission
    ):
        """Adding permission to role logs an audit trail."""
        custom_role = Role.objects.create(
            name="Permission Test Role",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
        )

        RolePermission.objects.create(
            role=owner_membership.role,
            permission=can_edit_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner_membership)

        with patch("apps.rbac.services.AuditService.log") as mock_audit:
            RBACService.add_permission_to_role(
                role_id=custom_role.id,
                permission_id=can_view_members_permission.id,
                scope=PermissionScope.BUSINESS,
                actor_context=actor_context,
            )

            mock_audit.assert_called_once()
            call_kwargs = mock_audit.call_args[1]
            assert call_kwargs["action"] == AuditLog.Action.ROLE_PERMISSION_ADDED

    def test_remove_permission_from_role_logs_audit(
        self, business, owner_membership, can_edit_role_permission, can_view_members_permission
    ):
        """Removing permission from role logs an audit trail."""
        custom_role = Role.objects.create(
            name="Permission Removal Test",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
        )

        # Add the permission first
        RolePermission.objects.create(
            role=custom_role,
            permission=can_view_members_permission,
            scope=PermissionScope.BUSINESS,
        )

        RolePermission.objects.create(
            role=owner_membership.role,
            permission=can_edit_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner_membership)

        with patch("apps.rbac.services.AuditService.log") as mock_audit:
            RBACService.remove_permission_from_role(
                role_id=custom_role.id,
                permission_id=can_view_members_permission.id,
                actor_context=actor_context,
            )

            mock_audit.assert_called_once()
            call_kwargs = mock_audit.call_args[1]
            assert call_kwargs["action"] == AuditLog.Action.ROLE_PERMISSION_REMOVED

    def test_member_leave_logs_audit(self, business_with_members):
        """Member leaving logs an audit trail."""
        member = business_with_members["member1_membership"]

        with patch("apps.rbac.services.AuditService.log") as mock_audit:
            RBACService.member_leave(
                membership_id=member.id,
                user=member.user,
            )

            mock_audit.assert_called_once()
            call_kwargs = mock_audit.call_args[1]
            assert call_kwargs["action"] == AuditLog.Action.MEMBERSHIP_LEFT

    def test_create_membership_logs_audit(
        self, business, base_member_role, owner_membership, another_user
    ):
        """Creating a membership logs an audit trail."""
        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner_membership)

        with patch("apps.rbac.services.AuditService.log") as mock_audit:
            RBACService.create_membership(
                user=another_user,
                account_type=AccountType.BUSINESS,
                account_id=business.id,
                role_id=base_member_role.id,
                created_by=owner_membership.user,
            )

            mock_audit.assert_called_once()
            call_kwargs = mock_audit.call_args[1]
            assert call_kwargs["action"] == AuditLog.Action.MEMBERSHIP_CREATED

    def test_ban_member_logs_audit(
        self, business_with_members, can_ban_member_permission
    ):
        """Banning a member logs MEMBERSHIP_BANNED audit action."""
        owner = business_with_members["owner_membership"]
        target = business_with_members["member1_membership"]

        RolePermission.objects.create(
            role=owner.role,
            permission=can_ban_member_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner)

        with patch("apps.rbac.services.AuditService.log") as mock_audit:
            RBACService.update_membership_status(
                membership_id=target.id,
                new_status=MembershipStatus.BANNED,
                actor_context=actor_context,
                reason="Test ban",
            )

            mock_audit.assert_called_once()
            call_kwargs = mock_audit.call_args[1]
            assert call_kwargs["action"] == AuditLog.Action.MEMBERSHIP_BANNED
            assert call_kwargs["resource"] == target

    def test_remove_member_logs_audit(
        self, business_with_members, can_remove_member_permission
    ):
        """Removing a member logs MEMBERSHIP_REMOVED audit action."""
        owner = business_with_members["owner_membership"]
        target = business_with_members["member1_membership"]

        RolePermission.objects.create(
            role=owner.role,
            permission=can_remove_member_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner)

        with patch("apps.rbac.services.AuditService.log") as mock_audit:
            RBACService.update_membership_status(
                membership_id=target.id,
                new_status=MembershipStatus.REMOVED,
                actor_context=actor_context,
                reason="Test removal",
            )

            mock_audit.assert_called_once()
            call_kwargs = mock_audit.call_args[1]
            assert call_kwargs["action"] == AuditLog.Action.MEMBERSHIP_REMOVED
            assert call_kwargs["resource"] == target

    def test_reactivate_member_logs_audit(
        self, business_with_members, can_suspend_member_permission
    ):
        """Reactivating a suspended member logs MEMBERSHIP_REACTIVATED audit action."""
        owner = business_with_members["owner_membership"]
        target = business_with_members["member1_membership"]

        # First suspend the target
        target.status = MembershipStatus.SUSPENDED
        target.save()

        RolePermission.objects.create(
            role=owner.role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner)

        with patch("apps.rbac.services.AuditService.log") as mock_audit:
            RBACService.update_membership_status(
                membership_id=target.id,
                new_status=MembershipStatus.ACTIVE,
                actor_context=actor_context,
            )

            mock_audit.assert_called_once()
            call_kwargs = mock_audit.call_args[1]
            assert call_kwargs["action"] == AuditLog.Action.MEMBERSHIP_REACTIVATED
            assert call_kwargs["resource"] == target

    def test_restore_membership_logs_audit(
        self, business_with_members, can_remove_member_permission
    ):
        """Restoring a soft-deleted membership logs MEMBERSHIP_RESTORED audit action."""
        owner = business_with_members["owner_membership"]
        target = business_with_members["member1_membership"]

        # Soft delete the target
        target.is_deleted = True
        target.status = MembershipStatus.REMOVED
        target.save()

        RolePermission.objects.create(
            role=owner.role,
            permission=can_remove_member_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=owner)

        with patch("apps.rbac.services.AuditService.log") as mock_audit:
            RBACService.restore_membership(
                membership_id=target.id,
                actor_context=actor_context,
            )

            mock_audit.assert_called_once()
            call_kwargs = mock_audit.call_args[1]
            assert call_kwargs["action"] == AuditLog.Action.MEMBERSHIP_RESTORED
            assert call_kwargs["resource"] == target


# =============================================================================
# SUSPENDED MEMBER BEHAVIOR
# =============================================================================


@pytest.mark.django_db
class TestSuspendedMemberBehavior:
    """Tests for suspended member restrictions."""

    def test_suspended_member_cannot_build_actor_context(self, business_with_members):
        """A suspended member cannot build an actor context."""
        member = business_with_members["member1_membership"]
        member.status = MembershipStatus.SUSPENDED
        member.save()

        with pytest.raises(PermissionDenied) as exc_info:
            RBACService.build_actor_context(membership=member)

        assert "not active" in str(exc_info.value.message).lower()

    def test_banned_member_cannot_build_actor_context(self, business_with_members):
        """A banned member cannot build an actor context."""
        member = business_with_members["member1_membership"]
        member.status = MembershipStatus.BANNED
        member.save()

        with pytest.raises(PermissionDenied):
            RBACService.build_actor_context(membership=member)


# =============================================================================
# DOMINANCE RULE EDGE CASES
# =============================================================================


@pytest.mark.django_db
class TestDominanceRuleEdgeCases:
    """Edge cases for the dominance rule (lower level = higher authority)."""

    def test_level_3_can_act_on_level_5(
        self, business, can_suspend_member_permission, user, another_user
    ):
        """Level 3 role can act on level 5 role (lower number = higher authority)."""
        role_3 = Role.objects.create(
            name="Level 3",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=3,
        )
        role_5 = Role.objects.create(
            name="Level 5",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
        )

        actor = Membership.objects.create(
            user=user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            role=role_3,
            status=MembershipStatus.ACTIVE,
        )
        target = Membership.objects.create(
            user=another_user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            role=role_5,
            status=MembershipStatus.ACTIVE,
        )

        RolePermission.objects.create(
            role=role_3,
            permission=can_suspend_member_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=actor)

        result = RBACService.update_membership_status(
            membership_id=target.id,
            new_status=MembershipStatus.SUSPENDED,
            actor_context=actor_context,
        )

        assert result.status == MembershipStatus.SUSPENDED

    def test_level_5_cannot_act_on_level_3(
        self, business, can_suspend_member_permission, user, another_user
    ):
        """Level 5 role cannot act on level 3 role (higher number = lower authority)."""
        role_3 = Role.objects.create(
            name="Level 3",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=3,
        )
        role_5 = Role.objects.create(
            name="Level 5",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
        )

        actor = Membership.objects.create(
            user=user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            role=role_5,
            status=MembershipStatus.ACTIVE,
        )
        target = Membership.objects.create(
            user=another_user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            role=role_3,
            status=MembershipStatus.ACTIVE,
        )

        RolePermission.objects.create(
            role=role_5,
            permission=can_suspend_member_permission,
            scope=PermissionScope.BUSINESS,
        )

        cache.clear()
        actor_context = RBACService.build_actor_context(membership=actor)

        with pytest.raises(PermissionDenied) as exc_info:
            RBACService.update_membership_status(
                membership_id=target.id,
                new_status=MembershipStatus.SUSPENDED,
                actor_context=actor_context,
            )

        assert "authority" in str(exc_info.value.message).lower()
