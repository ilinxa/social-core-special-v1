# apps/rbac/tests/test_policies.py
"""
Tests for RBAC policies.

Tests cover the two-plane authority model:
- Business Plane: Authority within a single business account
- Platform Plane: Authority over the entire platform

Key scenarios:
- Same-account actions with business-scope permissions
- Cross-account actions with global-scope permissions
- Owner invincibility (business owner and platform owner)
- Dominance rule (actor.role.level < target.role.level)
- Role assignment validation
"""

from datetime import datetime
from uuid import uuid4

import pytest

from apps.core.constants import AccountType, MembershipStatus, PermissionScope
from apps.core.exceptions import PermissionDenied
from apps.core.types import ActorContext
from apps.rbac.models import Membership, Role, RolePermission
from apps.rbac.policies import MembershipPolicy, RolePolicy

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def make_actor_context(
    user_id=None,
    account_type=AccountType.BUSINESS,
    account_id=None,
    membership_id=None,
    role_id=None,
    role_name="Test Role",
    role_level=5,
    is_owner=False,
    permissions=None,
):
    """Helper to create ActorContext for testing."""
    return ActorContext(
        user_id=user_id or uuid4(),
        account_type=account_type,
        account_id=account_id or uuid4(),
        membership_id=membership_id or uuid4(),
        role_id=role_id or uuid4(),
        role_name=role_name,
        role_level=role_level,
        is_owner=is_owner,
        permissions_snapshot=permissions or [],
    )


# =============================================================================
# MEMBERSHIP POLICY TESTS
# =============================================================================


@pytest.mark.django_db
class TestMembershipPolicyAuthorize:
    """Tests for MembershipPolicy.authorize_action."""

    def test_no_membership_context_denied(self):
        """Test that missing membership context is denied."""
        actor_context = ActorContext(
            user_id=uuid4(),
            account_type=None,
            account_id=None,
            membership_id=None,
            role_id=None,
            role_name=None,
            role_level=None,
            is_owner=False,
            permissions_snapshot=[],
        )
        with pytest.raises(PermissionDenied) as exc_info:
            MembershipPolicy.authorize_action(
                actor_context=actor_context,
                target_membership=None,
                required_permission="can_view_members",
            )
        assert "No active membership context" in str(exc_info.value.message)

    def test_same_account_with_permission(self, business, role):
        """Test same-account action with required permission."""
        account_id = business.id
        actor_context = make_actor_context(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            role_level=2,
            permissions=[("can_view_members", PermissionScope.BUSINESS)],
        )
        target_membership = Membership(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            is_owner=False,
            is_deleted=False,
        )
        target_membership.role = role

        # Should not raise
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            target_membership=target_membership,
            required_permission="can_view_members",
        )

    def test_same_account_without_permission(self, business, role):
        """Test same-account action without required permission."""
        account_id = business.id
        actor_context = make_actor_context(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            permissions=[],  # No permissions
        )
        target_membership = Membership(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            is_owner=False,
            is_deleted=False,
        )
        target_membership.role = role

        with pytest.raises(PermissionDenied) as exc_info:
            MembershipPolicy.authorize_action(
                actor_context=actor_context,
                target_membership=target_membership,
                required_permission="can_view_members",
            )
        assert "Missing required permission" in str(exc_info.value.message)

    def test_cross_account_requires_global_scope(
        self, business, another_business, role
    ):
        """Test cross-account action requires global-scoped permission."""
        # Actor in business A
        actor_context = make_actor_context(
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            permissions=[("can_remove_member", PermissionScope.BUSINESS)],
        )
        # Target in business B
        target_role = Role.objects.create(
            name="Member",
            account_type=AccountType.BUSINESS,
            account_id=another_business.id,
            level=10,
        )
        target_membership = Membership(
            account_type=AccountType.BUSINESS,
            account_id=another_business.id,
            is_owner=False,
            is_deleted=False,
        )
        target_membership.role = target_role

        # Business-scoped permission should fail for cross-account
        with pytest.raises(PermissionDenied):
            MembershipPolicy.authorize_action(
                actor_context=actor_context,
                target_membership=target_membership,
                required_permission="can_remove_member",
            )

    def test_cross_account_with_global_permission(
        self, business, another_business, platform
    ):
        """Test cross-account action with global-scoped permission."""
        # Platform actor with global permission
        actor_context = make_actor_context(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role_level=5,
            permissions=[("can_remove_member", PermissionScope.GLOBAL_ONLY)],
        )
        # Target in business
        target_role = Role.objects.create(
            name="Member",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=10,
        )
        target_membership = Membership(
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            is_owner=False,
            is_deleted=False,
        )
        target_membership.role = target_role

        # Global-scoped permission should work cross-account
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            target_membership=target_membership,
            required_permission="can_remove_member",
        )


@pytest.mark.django_db
class TestMembershipPolicyOwnerInvincibility:
    """Tests for owner invincibility rules."""

    def test_business_owner_invincible_same_account(self, business, owner_role, role):
        """Test that business owner cannot be acted upon within same account."""
        account_id = business.id
        # Actor is admin (level 2)
        actor_context = make_actor_context(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            role_level=2,
            is_owner=False,
            permissions=[("can_suspend_member", PermissionScope.BUSINESS)],
        )
        # Target is owner
        target_membership = Membership(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            is_owner=True,
            is_deleted=False,
        )
        target_membership.role = owner_role

        with pytest.raises(PermissionDenied) as exc_info:
            MembershipPolicy.authorize_action(
                actor_context=actor_context,
                target_membership=target_membership,
                required_permission="can_suspend_member",
            )
        assert "account owner" in str(exc_info.value.message)

    def test_business_owner_vulnerable_to_platform_global(
        self, business, owner_role, platform
    ):
        """Test that business owner CAN be acted upon by platform with global permission."""
        # Platform actor with global permission
        actor_context = make_actor_context(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role_level=2,
            permissions=[("can_suspend_member", PermissionScope.GLOBAL_ONLY)],
        )
        # Target is business owner
        target_membership = Membership(
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            is_owner=True,
            is_deleted=False,
        )
        target_membership.role = owner_role

        # Should not raise - platform can act on business owners
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            target_membership=target_membership,
            required_permission="can_suspend_member",
        )

    def test_platform_owner_always_invincible(self, platform, platform_owner_role):
        """Test that platform owner is ALWAYS invincible."""
        # Even another platform member with global permission
        actor_context = make_actor_context(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role_level=2,
            is_owner=False,
            permissions=[("can_suspend_member", PermissionScope.GLOBAL_ONLY)],
        )
        # Target is platform owner
        target_membership = Membership(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            is_owner=True,
            is_deleted=False,
        )
        target_membership.role = platform_owner_role

        with pytest.raises(PermissionDenied) as exc_info:
            MembershipPolicy.authorize_action(
                actor_context=actor_context,
                target_membership=target_membership,
                required_permission="can_suspend_member",
            )
        assert "account owner" in str(exc_info.value.message)


@pytest.mark.django_db
class TestMembershipPolicyDominanceRule:
    """Tests for dominance rule (actor.role.level < target.role.level)."""

    def test_higher_level_can_act_on_lower(self, business):
        """Test that higher authority (lower level) can act on lower authority."""
        account_id = business.id
        target_role = Role.objects.create(
            name="Member",
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            level=10,
        )
        # Actor level 2 (admin)
        actor_context = make_actor_context(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            role_level=2,
            permissions=[("can_change_member_role", PermissionScope.BUSINESS)],
        )
        # Target level 10 (base member)
        target_membership = Membership(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            is_owner=False,
            is_deleted=False,
        )
        target_membership.role = target_role

        # Should not raise (2 < 10)
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            target_membership=target_membership,
            required_permission="can_change_member_role",
        )

    def test_equal_level_cannot_act(self, business):
        """Test that equal level cannot act on each other."""
        account_id = business.id
        target_role = Role.objects.create(
            name="Peer Role",
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            level=5,
        )
        # Actor level 5
        actor_context = make_actor_context(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            role_level=5,
            permissions=[("can_change_member_role", PermissionScope.BUSINESS)],
        )
        # Target also level 5
        target_membership = Membership(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            is_owner=False,
            is_deleted=False,
        )
        target_membership.role = target_role

        with pytest.raises(PermissionDenied) as exc_info:
            MembershipPolicy.authorize_action(
                actor_context=actor_context,
                target_membership=target_membership,
                required_permission="can_change_member_role",
            )
        assert "role level does not outrank" in str(exc_info.value.message)

    def test_lower_level_cannot_act_on_higher(self, business):
        """Test that lower authority cannot act on higher authority."""
        account_id = business.id
        target_role = Role.objects.create(
            name="Admin",
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            level=2,
        )
        # Actor level 5 (manager)
        actor_context = make_actor_context(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            role_level=5,
            permissions=[("can_change_member_role", PermissionScope.BUSINESS)],
        )
        # Target level 2 (admin)
        target_membership = Membership(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            is_owner=False,
            is_deleted=False,
        )
        target_membership.role = target_role

        with pytest.raises(PermissionDenied) as exc_info:
            MembershipPolicy.authorize_action(
                actor_context=actor_context,
                target_membership=target_membership,
                required_permission="can_change_member_role",
            )
        assert "role level does not outrank" in str(exc_info.value.message)

    def test_dominance_skipped_cross_account(self, business, platform):
        """Test that dominance rule is skipped for cross-account actions."""
        # Platform actor level 5 (moderator)
        actor_context = make_actor_context(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role_level=5,
            permissions=[("can_suspend_member", PermissionScope.GLOBAL_ONLY)],
        )
        # Target business admin level 2 (higher authority than platform moderator level 5)
        target_role = Role.objects.create(
            name="Business Admin",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=2,
        )
        target_membership = Membership(
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            is_owner=False,
            is_deleted=False,
        )
        target_membership.role = target_role

        # Should NOT raise - cross-account dominance is skipped
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            target_membership=target_membership,
            required_permission="can_suspend_member",
        )


@pytest.mark.django_db
class TestMembershipPolicyTargetChecks:
    """Tests for target membership validation."""

    def test_deleted_membership_denied(self, business, role):
        """Test that deleted membership cannot be acted upon."""
        account_id = business.id
        actor_context = make_actor_context(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            role_level=2,
            permissions=[("can_view_members", PermissionScope.BUSINESS)],
        )
        target_membership = Membership(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            is_owner=False,
            is_deleted=True,  # Deleted
        )
        target_membership.role = role

        with pytest.raises(PermissionDenied) as exc_info:
            MembershipPolicy.authorize_action(
                actor_context=actor_context,
                target_membership=target_membership,
                required_permission="can_view_members",
            )
        assert "no longer exists" in str(exc_info.value.message)


@pytest.mark.django_db
class TestMembershipPolicyRoleAssignment:
    """Tests for role assignment validation."""

    def test_cannot_assign_owner_role(self, business):
        """Test that owner role (level 0) cannot be assigned directly."""
        account_id = business.id
        owner_role = Role.objects.create(
            name="Owner",
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            level=0,
            is_system_role=True,
        )
        member_role = Role.objects.create(
            name="Member",
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            level=10,
        )
        actor_context = make_actor_context(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            role_level=0,
            is_owner=True,
        )
        target_membership = Membership(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            is_owner=False,
            is_deleted=False,
        )
        target_membership.role = member_role

        with pytest.raises(PermissionDenied) as exc_info:
            MembershipPolicy.validate_role_assignment(
                actor_context=actor_context,
                new_role=owner_role,
                target_membership=target_membership,
            )
        assert "ownership transfer" in str(exc_info.value.message)

    def test_cannot_assign_equal_or_higher_role(self, business):
        """Test that actor cannot assign role equal to or higher than their own."""
        account_id = business.id
        admin_role = Role.objects.create(
            name="Admin",
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            level=2,
        )
        member_role = Role.objects.create(
            name="Member",
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            level=10,
        )
        # Actor is level 5
        actor_context = make_actor_context(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            role_level=5,
        )
        target_membership = Membership(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            is_owner=False,
            is_deleted=False,
        )
        target_membership.role = member_role

        # Cannot assign level 2 (higher authority)
        with pytest.raises(PermissionDenied) as exc_info:
            MembershipPolicy.validate_role_assignment(
                actor_context=actor_context,
                new_role=admin_role,
                target_membership=target_membership,
            )
        assert "equal or higher authority" in str(exc_info.value.message)

    def test_role_must_belong_to_target_account(self, business, another_business):
        """Test that role must belong to target's account."""
        account_id = business.id
        other_role = Role.objects.create(
            name="Other Role",
            account_type=AccountType.BUSINESS,
            account_id=another_business.id,
            level=5,
        )
        member_role = Role.objects.create(
            name="Member",
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            level=10,
        )
        actor_context = make_actor_context(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            role_level=2,
        )
        target_membership = Membership(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            is_owner=False,
            is_deleted=False,
        )
        target_membership.role = member_role

        with pytest.raises(PermissionDenied) as exc_info:
            MembershipPolicy.validate_role_assignment(
                actor_context=actor_context,
                new_role=other_role,
                target_membership=target_membership,
            )
        assert "does not belong to this account" in str(exc_info.value.message)


# =============================================================================
# ROLE POLICY TESTS
# =============================================================================


@pytest.mark.django_db
class TestRolePolicyCanCreateRole:
    """Tests for RolePolicy.can_create_role."""

    def test_cannot_create_level_0_role(self):
        """Test that level 0 cannot be created (reserved for owner)."""
        actor_context = make_actor_context(role_level=0, is_owner=True)

        with pytest.raises(PermissionDenied) as exc_info:
            RolePolicy.can_create_role(actor_context=actor_context, level=0)
        assert "reserved for the Owner role" in str(exc_info.value.message)

    def test_must_outrank_role_being_created(self):
        """Test that actor must outrank the role they're creating."""
        # Actor level 5
        actor_context = make_actor_context(role_level=5)

        # Cannot create level 3 (higher authority)
        with pytest.raises(PermissionDenied) as exc_info:
            RolePolicy.can_create_role(actor_context=actor_context, level=3)
        assert "equal or higher authority" in str(exc_info.value.message)

        # Cannot create level 5 (equal authority)
        with pytest.raises(PermissionDenied) as exc_info:
            RolePolicy.can_create_role(actor_context=actor_context, level=5)
        assert "equal or higher authority" in str(exc_info.value.message)

    def test_can_create_lower_authority_role(self):
        """Test that actor can create role with lower authority."""
        # Actor level 2
        actor_context = make_actor_context(role_level=2)

        # Should not raise for level 5
        RolePolicy.can_create_role(actor_context=actor_context, level=5)


@pytest.mark.django_db
class TestRolePolicyCanModifyRole:
    """Tests for RolePolicy.can_modify_role."""

    def test_cannot_modify_system_role(self, business):
        """Test that system roles cannot be modified."""
        system_role = Role.objects.create(
            name="Owner",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=0,
            is_system_role=True,
        )
        actor_context = make_actor_context(
            role_level=0,
            is_owner=True,
            account_id=business.id,
        )

        with pytest.raises(PermissionDenied) as exc_info:
            RolePolicy.can_modify_role(actor_context=actor_context, role=system_role)
        assert "System roles cannot be modified" in str(exc_info.value.message)

    def test_must_outrank_role_being_modified(self, business):
        """Test that actor must outrank the role they're modifying."""
        custom_role = Role.objects.create(
            name="Admin",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=2,
            is_system_role=False,
        )
        # Actor level 5 (lower authority)
        actor_context = make_actor_context(
            role_level=5,
            account_id=business.id,
        )

        with pytest.raises(PermissionDenied) as exc_info:
            RolePolicy.can_modify_role(actor_context=actor_context, role=custom_role)
        assert "equal or higher authority" in str(exc_info.value.message)

    def test_can_modify_lower_authority_role(self, business):
        """Test that actor can modify role with lower authority."""
        custom_role = Role.objects.create(
            name="Manager",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
            is_system_role=False,
        )
        # Actor level 2 (higher authority)
        actor_context = make_actor_context(
            role_level=2,
            account_id=business.id,
        )

        # Should not raise
        RolePolicy.can_modify_role(actor_context=actor_context, role=custom_role)


@pytest.mark.django_db
class TestRolePolicyCanDeleteRole:
    """Tests for RolePolicy.can_delete_role."""

    def test_cannot_delete_system_role(self, business):
        """Test that system roles cannot be deleted."""
        system_role = Role.objects.create(
            name="Base Member",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=10,
            is_system_role=True,
        )
        actor_context = make_actor_context(
            role_level=0,
            is_owner=True,
            account_id=business.id,
        )

        with pytest.raises(PermissionDenied) as exc_info:
            RolePolicy.can_delete_role(actor_context=actor_context, role=system_role)
        assert "System roles cannot be modified" in str(exc_info.value.message)

    def test_must_outrank_role_being_deleted(self, business):
        """Test that actor must outrank the role they're deleting."""
        custom_role = Role.objects.create(
            name="Admin",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=2,
            is_system_role=False,
        )
        # Actor level 5
        actor_context = make_actor_context(
            role_level=5,
            account_id=business.id,
        )

        with pytest.raises(PermissionDenied):
            RolePolicy.can_delete_role(actor_context=actor_context, role=custom_role)


# =============================================================================
# GET VIEWER PERMISSIONS TESTS
# =============================================================================


@pytest.mark.django_db
class TestMembershipPolicyGetViewerPermissions:
    """Tests for MembershipPolicy.get_viewer_permissions."""

    def test_owner_viewing_active_member(self, business, owner_role, base_member_role):
        """Owner should have all action permissions on an active member."""
        account_id = business.id
        actor_context = make_actor_context(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            role_level=0,
            is_owner=True,
            permissions=[
                ("can_change_member_role", PermissionScope.BUSINESS),
                ("can_suspend_member", PermissionScope.BUSINESS),
                ("can_remove_member", PermissionScope.BUSINESS),
                ("can_ban_member", PermissionScope.BUSINESS),
            ],
        )
        target_membership = Membership(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            is_owner=False,
            is_deleted=False,
            status=MembershipStatus.ACTIVE,
        )
        target_membership.role = base_member_role

        perms = MembershipPolicy.get_viewer_permissions(
            actor_context=actor_context,
            target_membership=target_membership,
        )

        assert perms["can_change_role"] is True
        assert perms["can_suspend"] is True
        assert perms["can_remove"] is True
        assert perms["can_ban"] is True
        assert perms["can_reactivate"] is False  # Already active

    def test_member_viewing_peer(self, business, base_member_role):
        """Base member should have no action permissions on peer."""
        account_id = business.id
        actor_context = make_actor_context(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            role_level=10,
            is_owner=False,
            permissions=[],  # No management permissions
        )
        target_membership = Membership(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            is_owner=False,
            is_deleted=False,
            status=MembershipStatus.ACTIVE,
        )
        target_membership.role = base_member_role

        perms = MembershipPolicy.get_viewer_permissions(
            actor_context=actor_context,
            target_membership=target_membership,
        )

        assert perms["can_change_role"] is False
        assert perms["can_suspend"] is False
        assert perms["can_remove"] is False
        assert perms["can_ban"] is False
        assert perms["can_reactivate"] is False

    def test_owner_viewing_suspended_member(
        self, business, owner_role, base_member_role
    ):
        """Owner should see can_reactivate=True for suspended member."""
        account_id = business.id
        actor_context = make_actor_context(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            role_level=0,
            is_owner=True,
            permissions=[
                ("can_suspend_member", PermissionScope.BUSINESS),
            ],
        )
        target_membership = Membership(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            is_owner=False,
            is_deleted=False,
            status=MembershipStatus.SUSPENDED,
        )
        target_membership.role = base_member_role

        perms = MembershipPolicy.get_viewer_permissions(
            actor_context=actor_context,
            target_membership=target_membership,
        )

        assert perms["can_reactivate"] is True

    def test_viewing_owner_member(self, business, owner_role):
        """No one should be able to act on the owner within same account."""
        account_id = business.id
        actor_context = make_actor_context(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            role_level=2,
            is_owner=False,
            permissions=[
                ("can_change_member_role", PermissionScope.BUSINESS),
                ("can_suspend_member", PermissionScope.BUSINESS),
                ("can_remove_member", PermissionScope.BUSINESS),
                ("can_ban_member", PermissionScope.BUSINESS),
            ],
        )
        target_membership = Membership(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            is_owner=True,
            is_deleted=False,
            status=MembershipStatus.ACTIVE,
        )
        target_membership.role = owner_role

        perms = MembershipPolicy.get_viewer_permissions(
            actor_context=actor_context,
            target_membership=target_membership,
        )

        assert perms["can_change_role"] is False
        assert perms["can_suspend"] is False
        assert perms["can_remove"] is False
        assert perms["can_ban"] is False
        assert perms["can_reactivate"] is False


@pytest.mark.django_db
class TestRolePolicyGetViewerPermissions:
    """Tests for RolePolicy.get_viewer_permissions."""

    def test_owner_viewing_custom_role(self, business):
        """Owner with can_create_role should have all permissions on custom role."""
        account_id = business.id
        custom_role = Role.objects.create(
            name="Manager",
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            level=5,
            is_system_role=False,
        )
        actor_context = make_actor_context(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            role_level=0,
            is_owner=True,
            permissions=[
                ("can_create_role", PermissionScope.BUSINESS),
            ],
        )

        perms = RolePolicy.get_viewer_permissions(
            actor_context=actor_context,
            role=custom_role,
        )

        assert perms["can_edit"] is True
        assert perms["can_delete"] is True
        assert perms["can_modify_permissions"] is True

    def test_member_viewing_system_role(self, business):
        """System roles should have can_edit=False and can_delete=False."""
        account_id = business.id
        system_role = Role.objects.create(
            name="Owner",
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            level=0,
            is_system_role=True,
        )
        actor_context = make_actor_context(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            role_level=0,
            is_owner=True,
            permissions=[
                ("can_create_role", PermissionScope.BUSINESS),
            ],
        )

        perms = RolePolicy.get_viewer_permissions(
            actor_context=actor_context,
            role=system_role,
        )

        assert perms["can_edit"] is False
        assert perms["can_delete"] is False
        assert perms["can_modify_permissions"] is False

    def test_member_without_permission(self, business):
        """Member without can_create_role should have no permissions."""
        account_id = business.id
        custom_role = Role.objects.create(
            name="Manager",
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            level=5,
            is_system_role=False,
        )
        actor_context = make_actor_context(
            account_type=AccountType.BUSINESS,
            account_id=account_id,
            role_level=10,
            is_owner=False,
            permissions=[],
        )

        perms = RolePolicy.get_viewer_permissions(
            actor_context=actor_context,
            role=custom_role,
        )

        assert perms["can_edit"] is False
        assert perms["can_delete"] is False
        assert perms["can_modify_permissions"] is False


# =============================================================================
# PLATFORM POLICY TESTS
# =============================================================================


@pytest.mark.django_db
class TestPlatformMembershipPolicyAuthorize:
    """Platform-scoped authorize_action tests — mirrors TestMembershipPolicyAuthorize."""

    def test_same_platform_with_permission(self, platform, global_moderator_role):
        """Platform actor with permission can act on platform member within same account."""
        account_id = platform.id
        actor_context = make_actor_context(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            role_level=2,
            permissions=[("can_view_members", PermissionScope.PLATFORM_ONLY)],
        )
        target_membership = Membership(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            is_owner=False,
            is_deleted=False,
        )
        target_membership.role = global_moderator_role

        # Should not raise
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            target_membership=target_membership,
            required_permission="can_view_members",
        )

    def test_same_platform_without_permission(self, platform, global_moderator_role):
        """Platform actor without required permission is denied."""
        account_id = platform.id
        actor_context = make_actor_context(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            permissions=[],
        )
        target_membership = Membership(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            is_owner=False,
            is_deleted=False,
        )
        target_membership.role = global_moderator_role

        with pytest.raises(PermissionDenied) as exc_info:
            MembershipPolicy.authorize_action(
                actor_context=actor_context,
                target_membership=target_membership,
                required_permission="can_view_members",
            )
        assert "Missing required permission" in str(exc_info.value.message)

    def test_platform_only_scope_grants_access(self, platform, global_moderator_role):
        """platform_only scoped permission grants access within platform."""
        account_id = platform.id
        actor_context = make_actor_context(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            role_level=2,
            permissions=[("can_suspend_member", PermissionScope.PLATFORM_ONLY)],
        )
        target_membership = Membership(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            is_owner=False,
            is_deleted=False,
        )
        target_membership.role = global_moderator_role

        # Should not raise — platform_only grants same-account access
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            target_membership=target_membership,
            required_permission="can_suspend_member",
        )


@pytest.mark.django_db
class TestPlatformDominanceRule:
    """Dominance rule tests within platform context."""

    def test_platform_admin_can_act_on_moderator(self, platform, global_moderator_role):
        """Level 2 (admin) can act on level 5 (moderator) within platform."""
        account_id = platform.id
        actor_context = make_actor_context(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            role_level=2,
            permissions=[("can_change_member_role", PermissionScope.PLATFORM_ONLY)],
        )
        target_membership = Membership(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            is_owner=False,
            is_deleted=False,
        )
        target_membership.role = global_moderator_role

        # Should not raise (2 < 5)
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            target_membership=target_membership,
            required_permission="can_change_member_role",
        )

    def test_platform_moderator_cannot_act_on_admin(
        self, platform, platform_admin_role
    ):
        """Level 5 (moderator) cannot act on level 2 (admin) within platform."""
        account_id = platform.id
        actor_context = make_actor_context(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            role_level=5,
            permissions=[("can_change_member_role", PermissionScope.PLATFORM_ONLY)],
        )
        target_membership = Membership(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            is_owner=False,
            is_deleted=False,
        )
        target_membership.role = platform_admin_role

        with pytest.raises(PermissionDenied) as exc_info:
            MembershipPolicy.authorize_action(
                actor_context=actor_context,
                target_membership=target_membership,
                required_permission="can_change_member_role",
            )
        assert "role level does not outrank" in str(exc_info.value.message)

    def test_platform_equal_level_denied(self, platform):
        """Equal level denied within platform."""
        account_id = platform.id
        peer_role = Role.objects.create(
            name="Platform Peer",
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            level=5,
        )
        actor_context = make_actor_context(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            role_level=5,
            permissions=[("can_change_member_role", PermissionScope.PLATFORM_ONLY)],
        )
        target_membership = Membership(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            is_owner=False,
            is_deleted=False,
        )
        target_membership.role = peer_role

        with pytest.raises(PermissionDenied) as exc_info:
            MembershipPolicy.authorize_action(
                actor_context=actor_context,
                target_membership=target_membership,
                required_permission="can_change_member_role",
            )
        assert "role level does not outrank" in str(exc_info.value.message)


@pytest.mark.django_db
class TestPlatformTargetChecks:
    """Target membership validation for platform context."""

    def test_deleted_platform_membership_denied(self, platform, global_moderator_role):
        """Deleted platform membership cannot be acted upon."""
        account_id = platform.id
        actor_context = make_actor_context(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            role_level=2,
            permissions=[("can_view_members", PermissionScope.PLATFORM_ONLY)],
        )
        target_membership = Membership(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            is_owner=False,
            is_deleted=True,
        )
        target_membership.role = global_moderator_role

        with pytest.raises(PermissionDenied) as exc_info:
            MembershipPolicy.authorize_action(
                actor_context=actor_context,
                target_membership=target_membership,
                required_permission="can_view_members",
            )
        assert "no longer exists" in str(exc_info.value.message)


@pytest.mark.django_db
class TestPlatformRoleAssignment:
    """Role assignment validation for platform context."""

    def test_cannot_assign_platform_owner_role(
        self, platform, platform_base_member_role
    ):
        """Platform owner role (level 0) cannot be assigned directly."""
        account_id = platform.id
        owner_role = Role.objects.create(
            name="Platform Owner Test",
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            level=0,
            is_system_role=True,
        )
        actor_context = make_actor_context(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            role_level=0,
            is_owner=True,
        )
        target_membership = Membership(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            is_owner=False,
            is_deleted=False,
        )
        target_membership.role = platform_base_member_role

        with pytest.raises(PermissionDenied) as exc_info:
            MembershipPolicy.validate_role_assignment(
                actor_context=actor_context,
                new_role=owner_role,
                target_membership=target_membership,
            )
        assert "ownership transfer" in str(exc_info.value.message)

    def test_cannot_assign_equal_or_higher_platform_role(
        self, platform, platform_base_member_role
    ):
        """Platform actor cannot assign role equal to or higher than their own."""
        account_id = platform.id
        admin_role = Role.objects.create(
            name="Platform Admin Test",
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            level=2,
        )
        # Actor is level 5 (moderator)
        actor_context = make_actor_context(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            role_level=5,
        )
        target_membership = Membership(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            is_owner=False,
            is_deleted=False,
        )
        target_membership.role = platform_base_member_role

        # Cannot assign level 2 (higher authority)
        with pytest.raises(PermissionDenied) as exc_info:
            MembershipPolicy.validate_role_assignment(
                actor_context=actor_context,
                new_role=admin_role,
                target_membership=target_membership,
            )
        assert "equal or higher authority" in str(exc_info.value.message)

    def test_platform_role_must_belong_to_same_platform(
        self, platform, business, platform_base_member_role
    ):
        """Role from a different account is rejected."""
        # Create role on the business, not the platform
        business_role = Role.objects.create(
            name="Wrong Account Role",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
        )
        actor_context = make_actor_context(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            role_level=2,
        )
        target_membership = Membership(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            is_owner=False,
            is_deleted=False,
        )
        target_membership.role = platform_base_member_role

        with pytest.raises(PermissionDenied) as exc_info:
            MembershipPolicy.validate_role_assignment(
                actor_context=actor_context,
                new_role=business_role,
                target_membership=target_membership,
            )
        assert "does not belong to this account" in str(exc_info.value.message)


@pytest.mark.django_db
class TestPlatformRolePolicies:
    """Role create/modify/delete policies for platform context."""

    def test_cannot_create_level_0_platform_role(self):
        """Level 0 reserved for platform owner role."""
        actor_context = make_actor_context(
            account_type=AccountType.PLATFORM,
            role_level=0,
            is_owner=True,
        )

        with pytest.raises(PermissionDenied) as exc_info:
            RolePolicy.can_create_role(actor_context=actor_context, level=0)
        assert "reserved for the Owner role" in str(exc_info.value.message)

    def test_platform_must_outrank_role_being_created(self):
        """Platform actor must outrank the role they're creating."""
        actor_context = make_actor_context(
            account_type=AccountType.PLATFORM,
            role_level=5,
        )

        with pytest.raises(PermissionDenied) as exc_info:
            RolePolicy.can_create_role(actor_context=actor_context, level=3)
        assert "equal or higher authority" in str(exc_info.value.message)

    def test_platform_can_create_lower_authority_role(self):
        """Platform admin can create role with lower authority."""
        actor_context = make_actor_context(
            account_type=AccountType.PLATFORM,
            role_level=2,
        )

        # Should not raise for level 5
        RolePolicy.can_create_role(actor_context=actor_context, level=5)

    def test_cannot_modify_system_platform_role(self, platform):
        """System platform roles cannot be modified."""
        system_role = Role.objects.create(
            name="Platform Owner",
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            level=0,
            is_system_role=True,
        )
        actor_context = make_actor_context(
            account_type=AccountType.PLATFORM,
            role_level=0,
            is_owner=True,
            account_id=platform.id,
        )

        with pytest.raises(PermissionDenied) as exc_info:
            RolePolicy.can_modify_role(actor_context=actor_context, role=system_role)
        assert "System roles cannot be modified" in str(exc_info.value.message)

    def test_can_modify_custom_platform_role(self, platform):
        """Custom platform roles can be modified by higher authority."""
        custom_role = Role.objects.create(
            name="Platform Custom",
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            level=5,
            is_system_role=False,
        )
        actor_context = make_actor_context(
            account_type=AccountType.PLATFORM,
            role_level=2,
            account_id=platform.id,
        )

        # Should not raise
        RolePolicy.can_modify_role(actor_context=actor_context, role=custom_role)

    def test_cannot_delete_system_platform_role(self, platform):
        """System platform roles cannot be deleted."""
        system_role = Role.objects.create(
            name="Base Member",
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            level=10,
            is_system_role=True,
        )
        actor_context = make_actor_context(
            account_type=AccountType.PLATFORM,
            role_level=0,
            is_owner=True,
            account_id=platform.id,
        )

        with pytest.raises(PermissionDenied) as exc_info:
            RolePolicy.can_delete_role(actor_context=actor_context, role=system_role)
        assert "System roles cannot be modified" in str(exc_info.value.message)

    def test_platform_must_outrank_role_to_delete(self, platform):
        """Platform actor must outrank the role to delete it."""
        custom_role = Role.objects.create(
            name="Platform Admin Custom",
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            level=2,
            is_system_role=False,
        )
        # Actor level 5 (lower authority)
        actor_context = make_actor_context(
            account_type=AccountType.PLATFORM,
            role_level=5,
            account_id=platform.id,
        )

        with pytest.raises(PermissionDenied):
            RolePolicy.can_delete_role(actor_context=actor_context, role=custom_role)


@pytest.mark.django_db
class TestPlatformMembershipViewerPermissions:
    """get_viewer_permissions for platform membership context."""

    def test_platform_owner_viewing_active_member(
        self, platform, platform_owner_role, platform_base_member_role
    ):
        """Platform owner should have all action permissions on an active member."""
        account_id = platform.id
        actor_context = make_actor_context(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            role_level=0,
            is_owner=True,
            permissions=[
                ("can_change_member_role", PermissionScope.PLATFORM_ONLY),
                ("can_suspend_member", PermissionScope.PLATFORM_ONLY),
                ("can_remove_member", PermissionScope.PLATFORM_ONLY),
                ("can_ban_member", PermissionScope.PLATFORM_ONLY),
            ],
        )
        target_membership = Membership(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            is_owner=False,
            is_deleted=False,
            status=MembershipStatus.ACTIVE,
        )
        target_membership.role = platform_base_member_role

        perms = MembershipPolicy.get_viewer_permissions(
            actor_context=actor_context,
            target_membership=target_membership,
        )

        assert perms["can_change_role"] is True
        assert perms["can_suspend"] is True
        assert perms["can_remove"] is True
        assert perms["can_ban"] is True
        assert perms["can_reactivate"] is False

    def test_platform_member_viewing_peer(self, platform, platform_base_member_role):
        """Platform base member should have no action permissions on peer."""
        account_id = platform.id
        actor_context = make_actor_context(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            role_level=10,
            is_owner=False,
            permissions=[],
        )
        target_membership = Membership(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            is_owner=False,
            is_deleted=False,
            status=MembershipStatus.ACTIVE,
        )
        target_membership.role = platform_base_member_role

        perms = MembershipPolicy.get_viewer_permissions(
            actor_context=actor_context,
            target_membership=target_membership,
        )

        assert perms["can_change_role"] is False
        assert perms["can_suspend"] is False
        assert perms["can_remove"] is False
        assert perms["can_ban"] is False
        assert perms["can_reactivate"] is False

    def test_platform_owner_viewing_suspended_member(
        self, platform, platform_owner_role, platform_base_member_role
    ):
        """Platform owner sees can_reactivate=True for suspended member."""
        account_id = platform.id
        actor_context = make_actor_context(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            role_level=0,
            is_owner=True,
            permissions=[
                ("can_suspend_member", PermissionScope.PLATFORM_ONLY),
            ],
        )
        target_membership = Membership(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            is_owner=False,
            is_deleted=False,
            status=MembershipStatus.SUSPENDED,
        )
        target_membership.role = platform_base_member_role

        perms = MembershipPolicy.get_viewer_permissions(
            actor_context=actor_context,
            target_membership=target_membership,
        )

        assert perms["can_reactivate"] is True

    def test_viewing_platform_owner_member(self, platform, platform_owner_role):
        """No one should be able to act on the platform owner."""
        account_id = platform.id
        actor_context = make_actor_context(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            role_level=2,
            is_owner=False,
            permissions=[
                ("can_change_member_role", PermissionScope.PLATFORM_ONLY),
                ("can_suspend_member", PermissionScope.PLATFORM_ONLY),
                ("can_remove_member", PermissionScope.PLATFORM_ONLY),
                ("can_ban_member", PermissionScope.PLATFORM_ONLY),
            ],
        )
        target_membership = Membership(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            is_owner=True,
            is_deleted=False,
            status=MembershipStatus.ACTIVE,
        )
        target_membership.role = platform_owner_role

        perms = MembershipPolicy.get_viewer_permissions(
            actor_context=actor_context,
            target_membership=target_membership,
        )

        assert perms["can_change_role"] is False
        assert perms["can_suspend"] is False
        assert perms["can_remove"] is False
        assert perms["can_ban"] is False
        assert perms["can_reactivate"] is False


@pytest.mark.django_db
class TestPlatformRoleViewerPermissions:
    """get_viewer_permissions for platform role context."""

    def test_platform_owner_viewing_custom_role(self, platform):
        """Platform owner with can_create_role should have all permissions on custom role."""
        account_id = platform.id
        custom_role = Role.objects.create(
            name="Platform Moderator",
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            level=5,
            is_system_role=False,
        )
        actor_context = make_actor_context(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            role_level=0,
            is_owner=True,
            permissions=[
                ("can_create_role", PermissionScope.PLATFORM_ONLY),
            ],
        )

        perms = RolePolicy.get_viewer_permissions(
            actor_context=actor_context,
            role=custom_role,
        )

        assert perms["can_edit"] is True
        assert perms["can_delete"] is True
        assert perms["can_modify_permissions"] is True

    def test_platform_system_role_permissions(self, platform):
        """System platform roles should have can_edit=False and can_delete=False."""
        account_id = platform.id
        system_role = Role.objects.create(
            name="Platform Owner Role",
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            level=0,
            is_system_role=True,
        )
        actor_context = make_actor_context(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            role_level=0,
            is_owner=True,
            permissions=[
                ("can_create_role", PermissionScope.PLATFORM_ONLY),
            ],
        )

        perms = RolePolicy.get_viewer_permissions(
            actor_context=actor_context,
            role=system_role,
        )

        assert perms["can_edit"] is False
        assert perms["can_delete"] is False
        assert perms["can_modify_permissions"] is False

    def test_platform_member_without_permission(self, platform):
        """Platform member without can_create_role should have no permissions."""
        account_id = platform.id
        custom_role = Role.objects.create(
            name="Platform Custom Role",
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            level=5,
            is_system_role=False,
        )
        actor_context = make_actor_context(
            account_type=AccountType.PLATFORM,
            account_id=account_id,
            role_level=10,
            is_owner=False,
            permissions=[],
        )

        perms = RolePolicy.get_viewer_permissions(
            actor_context=actor_context,
            role=custom_role,
        )

        assert perms["can_edit"] is False
        assert perms["can_delete"] is False
        assert perms["can_modify_permissions"] is False
