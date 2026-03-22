# apps/rbac/tests/test_models.py
"""
Tests for RBAC models.

Tests cover:
- Permission model
- Role model with unique constraints
- RolePermission model
- Membership model with unique constraints (one owner, one membership per user)
- Soft-delete behavior
- Manager query methods
"""

import pytest
from django.db import IntegrityError
from django.db.utils import IntegrityError as DBIntegrityError

from apps.core.constants import AccountType, MembershipStatus, PermissionScope
from apps.rbac.models import Membership, Permission, Role, RolePermission


@pytest.mark.django_db
class TestPermissionModel:
    """Tests for Permission model."""

    def test_create_permission(self, db):
        """Test creating a permission."""
        permission = Permission.objects.create(
            code="can_test_action",
            name="Test Action",
            description="Test permission description",
            category="test",
            applicable_scopes=["business", "platform_only"],
        )
        assert permission.id is not None
        assert permission.code == "can_test_action"
        assert permission.category == "test"
        assert "business" in permission.applicable_scopes

    def test_permission_code_unique(self, permission):
        """Test that permission code must be unique."""
        with pytest.raises(IntegrityError):
            Permission.objects.create(
                code=permission.code,
                name="Duplicate",
                category="test",
                applicable_scopes=["business"],
            )

    def test_permission_str(self, permission):
        """Test permission string representation."""
        expected = f"{permission.code} ({permission.category})"
        assert str(permission) == expected


@pytest.mark.django_db
class TestRoleModel:
    """Tests for Role model."""

    def test_create_role(self, business):
        """Test creating a role."""
        role = Role.objects.create(
            name="Manager",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
            is_system_role=False,
            description="Manager role",
        )
        assert role.id is not None
        assert role.name == "Manager"
        assert role.level == 5
        assert role.account_id == business.id

    def test_role_unique_name_per_account(self, business):
        """Test that role name must be unique within an account."""
        Role.objects.create(
            name="Manager",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
        )
        with pytest.raises(IntegrityError):
            Role.objects.create(
                name="Manager",
                account_type=AccountType.BUSINESS,
                account_id=business.id,
                level=6,
            )

    def test_role_same_name_different_accounts(self, business, another_business):
        """Test that same role name can exist in different accounts."""
        Role.objects.create(
            name="Manager",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
        )
        role2 = Role.objects.create(
            name="Manager",
            account_type=AccountType.BUSINESS,
            account_id=another_business.id,
            level=5,
        )
        assert role2.name == "Manager"

    def test_role_str(self, role):
        """Test role string representation."""
        expected = f"{role.name} (Level {role.level})"
        assert str(role) == expected


@pytest.mark.django_db
class TestRolePermissionModel:
    """Tests for RolePermission model."""

    def test_create_role_permission(self, role, permission):
        """Test creating a role permission assignment."""
        role_perm = RolePermission.objects.create(
            role=role,
            permission=permission,
            scope=PermissionScope.BUSINESS,
        )
        assert role_perm.id is not None
        assert role_perm.role == role
        assert role_perm.permission == permission
        assert role_perm.scope == PermissionScope.BUSINESS

    def test_role_permission_unique(self, role, permission):
        """Test that each permission can only be assigned once per role."""
        RolePermission.objects.create(
            role=role,
            permission=permission,
            scope=PermissionScope.BUSINESS,
        )
        with pytest.raises(IntegrityError):
            RolePermission.objects.create(
                role=role,
                permission=permission,
                scope=PermissionScope.GLOBAL_ONLY,  # Different scope, same role+permission
            )

    def test_role_permission_str(self, role, permission):
        """Test role permission string representation."""
        role_perm = RolePermission.objects.create(
            role=role,
            permission=permission,
            scope=PermissionScope.BUSINESS,
        )
        expected = f"{role.name} -> {permission.code} ({PermissionScope.BUSINESS})"
        assert str(role_perm) == expected


@pytest.mark.django_db
class TestMembershipModel:
    """Tests for Membership model."""

    def test_create_membership(self, user, role):
        """Test creating a membership."""
        membership = Membership.objects.create(
            user=user,
            account_type=role.account_type,
            account_id=role.account_id,
            role=role,
            is_owner=False,
            status=MembershipStatus.ACTIVE,
        )
        assert membership.id is not None
        assert membership.user == user
        assert membership.role == role
        assert membership.is_owner is False
        assert membership.status == MembershipStatus.ACTIVE

    def test_membership_str(self, membership):
        """Test membership string representation."""
        expected = f"{membership.user} -> {membership.role.name}"
        assert str(membership) == expected


@pytest.mark.django_db
class TestMembershipUniqueConstraints:
    """Tests for Membership unique constraints."""

    def test_one_owner_per_account(self, business, owner_role, user, another_user):
        """Test that only one owner can exist per account."""
        Membership.objects.create(
            user=user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            role=owner_role,
            is_owner=True,
            status=MembershipStatus.ACTIVE,
        )
        with pytest.raises(IntegrityError):
            Membership.objects.create(
                user=another_user,
                account_type=AccountType.BUSINESS,
                account_id=business.id,
                role=owner_role,
                is_owner=True,
                status=MembershipStatus.ACTIVE,
            )

    def test_one_membership_per_user_per_account(
        self, business, role, base_member_role, user
    ):
        """Test that a user can only have one membership per account."""
        Membership.objects.create(
            user=user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            role=role,
            is_owner=False,
            status=MembershipStatus.ACTIVE,
        )
        with pytest.raises(IntegrityError):
            Membership.objects.create(
                user=user,
                account_type=AccountType.BUSINESS,
                account_id=business.id,
                role=base_member_role,  # Different role, same user
                is_owner=False,
                status=MembershipStatus.ACTIVE,
            )

    def test_same_user_different_accounts(self, business, another_business, user):
        """Test that a user can have memberships in different accounts."""
        role1 = Role.objects.create(
            name="Member",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=10,
        )
        role2 = Role.objects.create(
            name="Member",
            account_type=AccountType.BUSINESS,
            account_id=another_business.id,
            level=10,
        )
        m1 = Membership.objects.create(
            user=user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            role=role1,
            status=MembershipStatus.ACTIVE,
        )
        m2 = Membership.objects.create(
            user=user,
            account_type=AccountType.BUSINESS,
            account_id=another_business.id,
            role=role2,
            status=MembershipStatus.ACTIVE,
        )
        assert m1.id != m2.id

    def test_deleted_owner_allows_new_owner(
        self, business, owner_role, user, another_user
    ):
        """Test that soft-deleting owner allows assigning a new owner."""
        old_owner = Membership.objects.create(
            user=user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            role=owner_role,
            is_owner=True,
            status=MembershipStatus.ACTIVE,
        )
        # Soft-delete the old owner
        old_owner.is_deleted = True
        old_owner.save()

        # Now we can create a new owner
        new_owner = Membership.objects.create(
            user=another_user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            role=owner_role,
            is_owner=True,
            status=MembershipStatus.ACTIVE,
        )
        assert new_owner.is_owner is True

    def test_deleted_membership_allows_rejoin(self, business, role, user):
        """Test that soft-deleting membership allows user to rejoin."""
        old_membership = Membership.objects.create(
            user=user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            role=role,
            status=MembershipStatus.ACTIVE,
        )
        # Soft-delete
        old_membership.is_deleted = True
        old_membership.save()

        # User can rejoin
        new_membership = Membership.objects.create(
            user=user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            role=role,
            status=MembershipStatus.ACTIVE,
        )
        assert new_membership.id != old_membership.id


@pytest.mark.django_db
class TestMembershipManager:
    """Tests for MembershipManager."""

    def test_active_filter(self, business_with_members):
        """Test that active() returns only active memberships."""
        # Suspend one member
        member1 = business_with_members["member1_membership"]
        member1.status = MembershipStatus.SUSPENDED
        member1.save()

        active_count = (
            Membership.objects.active()
            .filter(account_id=business_with_members["business"].id)
            .count()
        )
        # Owner + member2 = 2 active
        assert active_count == 2

    def test_for_account(self, business_with_members):
        """Test for_account() method."""
        business = business_with_members["business"]
        memberships = Membership.objects.for_account(
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        )
        assert memberships.count() == 3  # Owner + 2 members

    def test_for_user(self, user, business, another_business, role):
        """Test for_user() method."""
        role1 = Role.objects.create(
            name="Role1",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
        )
        role2 = Role.objects.create(
            name="Role2",
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
        user_memberships = Membership.objects.for_user(user=user)
        assert user_memberships.count() == 2

    def test_default_manager_excludes_deleted(self, business, role, user):
        """Test that default manager excludes soft-deleted memberships."""
        membership = Membership.objects.create(
            user=user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            role=role,
            status=MembershipStatus.ACTIVE,
        )
        membership_id = membership.id
        membership.is_deleted = True
        membership.save()

        # Default manager should not find it
        assert not Membership.objects.filter(id=membership_id).exists()
        # all_objects should find it
        assert Membership.all_objects.filter(id=membership_id).exists()


@pytest.mark.django_db
class TestRoleAuditFields:
    """Tests for Role audit fields."""

    def test_role_created_by_updated_by(self, business, user):
        """Test that created_by and updated_by are set correctly."""
        role = Role.objects.create(
            name="Test Role",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
            created_by=user,
        )
        assert role.created_by == user
        assert role.updated_by is None

        role.updated_by = user
        role.save()
        assert role.updated_by == user

    def test_role_timestamps(self, business):
        """Test that timestamps are set automatically."""
        role = Role.objects.create(
            name="Test Role",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
        )
        assert role.created_at is not None
        assert role.updated_at is not None


@pytest.mark.django_db
class TestMembershipStatuses:
    """Tests for different membership statuses."""

    def test_membership_status_transitions(self, membership):
        """Test valid status transitions."""
        # Active -> Suspended
        membership.status = MembershipStatus.SUSPENDED
        membership.save()
        membership.refresh_from_db()
        assert membership.status == MembershipStatus.SUSPENDED

        # Suspended -> Active
        membership.status = MembershipStatus.ACTIVE
        membership.save()
        membership.refresh_from_db()
        assert membership.status == MembershipStatus.ACTIVE

        # Active -> Banned
        membership.status = MembershipStatus.BANNED
        membership.save()
        membership.refresh_from_db()
        assert membership.status == MembershipStatus.BANNED

    def test_membership_status_reason(self, membership):
        """Test that status reason is recorded."""
        membership.status = MembershipStatus.BANNED
        membership.status_reason = "Violation of terms of service"
        membership.save()

        membership.refresh_from_db()
        assert membership.status_reason == "Violation of terms of service"
