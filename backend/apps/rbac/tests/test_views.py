# apps/rbac/tests/test_views.py
"""
Tests for RBAC API views.

Tests cover:
- Permission list view
- Business role and member views
- Platform role and member views
- User memberships views
- Authentication and authorization
"""

from uuid import uuid4

import pytest
from django.urls import reverse
from rest_framework import status

from apps.core.constants import AccountType, MembershipStatus, PermissionScope
from apps.rbac.models import Membership, Permission, Role, RolePermission
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestPermissionListView:
    """Tests for permission list endpoint."""

    def test_list_permissions_authenticated(self, authenticated_client, permission):
        """Test listing permissions as authenticated user."""
        url = "/api/v1/rbac/permissions/"
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_list_permissions_unauthenticated(self, api_client, permission):
        """Test that unauthenticated users cannot list permissions."""
        url = "/api/v1/rbac/permissions/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestBusinessRoleListView:
    """Tests for business role list endpoint."""

    def test_list_roles_as_member(self, api_client, business_with_members):
        """Test listing roles as a business member."""
        owner = business_with_members["owner_membership"]
        api_client.force_authenticate(user=owner.user)

        url = f"/api/v1/business/{business_with_members['business'].slug}/roles/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Should have Owner and Base Member roles
        assert len(response.data) >= 2

    def test_list_roles_non_member_denied(self, api_client, business, another_user):
        """Test that non-members cannot list roles."""
        api_client.force_authenticate(user=another_user)

        url = f"/api/v1/business/{business.slug}/roles/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_role_as_owner(
        self, api_client, business_with_members, can_create_role_permission
    ):
        """Test creating a role as business owner."""
        owner = business_with_members["owner_membership"]

        # Grant the owner the permission to create roles
        RolePermission.objects.create(
            role=owner.role,
            permission=can_create_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        api_client.force_authenticate(user=owner.user)

        url = f"/api/v1/business/{business_with_members['business'].slug}/roles/"
        data = {
            "name": "Manager",
            "level": 5,
            "description": "Manager role",
        }
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Manager"
        assert response.data["level"] == 5


@pytest.mark.django_db
class TestBusinessRoleDetailView:
    """Tests for business role detail endpoint."""

    def test_get_role_detail(self, api_client, business_with_members):
        """Test getting role details."""
        owner = business_with_members["owner_membership"]
        owner_role = business_with_members["owner_role"]
        api_client.force_authenticate(user=owner.user)

        url = f"/api/v1/business/{business_with_members['business'].slug}/roles/{owner_role.id}/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Owner"

    def test_update_custom_role(
        self, api_client, business_with_members, can_edit_role_permission
    ):
        """Test updating a custom role."""
        owner = business_with_members["owner_membership"]
        business = business_with_members["business"]

        # Grant the owner the permission to edit roles
        RolePermission.objects.create(
            role=owner.role,
            permission=can_edit_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        api_client.force_authenticate(user=owner.user)

        # Create a custom role first
        custom_role = Role.objects.create(
            name="Manager",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
            is_system_role=False,
        )

        url = f"/api/v1/business/{business.slug}/roles/{custom_role.id}/"
        data = {"name": "Senior Manager", "description": "Updated description"}
        response = api_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Senior Manager"

    def test_cannot_update_system_role(
        self, api_client, business_with_members, can_edit_role_permission
    ):
        """Test that system roles cannot be updated."""
        owner = business_with_members["owner_membership"]
        owner_role = business_with_members["owner_role"]

        # Grant the owner the permission to edit roles
        RolePermission.objects.create(
            role=owner.role,
            permission=can_edit_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        api_client.force_authenticate(user=owner.user)

        url = f"/api/v1/business/{business_with_members['business'].slug}/roles/{owner_role.id}/"
        data = {"name": "New Owner Name"}
        response = api_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestBusinessMemberListView:
    """Tests for business member list endpoint."""

    def test_list_members(
        self, api_client, business_with_members, can_view_members_permission
    ):
        """Test listing business members."""
        owner = business_with_members["owner_membership"]
        business = business_with_members["business"]

        # Give owner the permission
        RolePermission.objects.create(
            role=owner.role,
            permission=can_view_members_permission,
            scope=PermissionScope.BUSINESS,
        )

        api_client.force_authenticate(user=owner.user)

        url = f"/api/v1/business/{business.slug}/members/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Owner + 2 members = 3 (paginated response)
        assert response.data["count"] == 3
        assert len(response.data["results"]) == 3

    def test_list_members_as_member(self, api_client, business_with_members):
        """Test that any member can list members."""
        member = business_with_members["member1_membership"]
        business = business_with_members["business"]

        api_client.force_authenticate(user=member.user)

        url = f"/api/v1/business/{business.slug}/members/"
        response = api_client.get(url)

        # Any member can view the member list
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 3  # Owner + 2 members

    def test_search_members_by_email(self, api_client, business_with_members):
        """Test searching members by email."""
        owner = business_with_members["owner_membership"]
        member1 = business_with_members["member1_membership"]
        business = business_with_members["business"]

        api_client.force_authenticate(user=owner.user)

        url = f"/api/v1/business/{business.slug}/members/?search={member1.user.email}"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["user"]["email"] == member1.user.email

    def test_filter_members_by_role(self, api_client, business_with_members):
        """Test filtering members by role_id."""
        owner = business_with_members["owner_membership"]
        base_role = business_with_members["base_member_role"]
        business = business_with_members["business"]

        api_client.force_authenticate(user=owner.user)

        url = f"/api/v1/business/{business.slug}/members/?role_id={base_role.id}"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2  # member1 + member2 (not owner)

    def test_filter_members_by_status(
        self, api_client, business_with_members, can_suspend_member_permission
    ):
        """Test filtering members by status."""
        owner = business_with_members["owner_membership"]
        member1 = business_with_members["member1_membership"]
        business = business_with_members["business"]

        # Suspend member1
        member1.status = MembershipStatus.SUSPENDED
        member1.save(update_fields=["status"])

        api_client.force_authenticate(user=owner.user)

        url = f"/api/v1/business/{business.slug}/members/?include_all=true&status=suspended"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1


@pytest.mark.django_db
class TestBusinessMemberDetailView:
    """Tests for business member detail endpoint."""

    def test_get_member_detail(
        self, api_client, business_with_members, can_view_members_permission
    ):
        """Test getting member details."""
        owner = business_with_members["owner_membership"]
        member1 = business_with_members["member1_membership"]
        business = business_with_members["business"]

        RolePermission.objects.create(
            role=owner.role,
            permission=can_view_members_permission,
            scope=PermissionScope.BUSINESS,
        )

        api_client.force_authenticate(user=owner.user)

        url = f"/api/v1/business/{business.slug}/members/{member1.id}/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert str(response.data["id"]) == str(member1.id)
        # Verify display_name and avatar_url are in user data
        user_data = response.data["user"]
        assert "display_name" in user_data
        assert "avatar_url" in user_data
        assert user_data["display_name"]  # Should have a value


@pytest.mark.django_db
class TestBusinessMemberRoleView:
    """Tests for changing member role endpoint."""

    def test_change_member_role(
        self, api_client, business_with_members, can_change_member_role_permission
    ):
        """Test changing a member's role."""
        owner = business_with_members["owner_membership"]
        member1 = business_with_members["member1_membership"]
        business = business_with_members["business"]

        RolePermission.objects.create(
            role=owner.role,
            permission=can_change_member_role_permission,
            scope=PermissionScope.BUSINESS,
        )

        # Create a new role to assign
        new_role = Role.objects.create(
            name="Manager",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
        )

        api_client.force_authenticate(user=owner.user)

        url = f"/api/v1/business/{business.slug}/members/{member1.id}/role/"
        data = {"role_id": str(new_role.id)}
        response = api_client.patch(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK

        member1.refresh_from_db()
        assert member1.role == new_role


@pytest.mark.django_db
class TestBusinessMemberSuspendView:
    """Tests for suspending member endpoint."""

    def test_suspend_member(
        self, api_client, business_with_members, can_suspend_member_permission
    ):
        """Test suspending a member."""
        owner = business_with_members["owner_membership"]
        member1 = business_with_members["member1_membership"]
        business = business_with_members["business"]

        RolePermission.objects.create(
            role=owner.role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.BUSINESS,
        )

        api_client.force_authenticate(user=owner.user)

        url = f"/api/v1/business/{business.slug}/members/{member1.id}/suspend/"
        data = {"reason": "Terms violation"}
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK

        member1.refresh_from_db()
        assert member1.status == MembershipStatus.SUSPENDED


@pytest.mark.django_db
class TestBusinessMemberBanView:
    """Tests for banning member endpoint."""

    def test_ban_member(
        self, api_client, business_with_members, can_ban_member_permission
    ):
        """Test banning a member."""
        owner = business_with_members["owner_membership"]
        member1 = business_with_members["member1_membership"]
        business = business_with_members["business"]

        RolePermission.objects.create(
            role=owner.role,
            permission=can_ban_member_permission,
            scope=PermissionScope.BUSINESS,
        )

        api_client.force_authenticate(user=owner.user)

        url = f"/api/v1/business/{business.slug}/members/{member1.id}/ban/"
        data = {"reason": "Permanent ban"}
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK

        member1.refresh_from_db()
        assert member1.status == MembershipStatus.BANNED


@pytest.mark.django_db
class TestBusinessMemberRemoveView:
    """Tests for removing member endpoint."""

    def test_remove_member(
        self, api_client, business_with_members, can_remove_member_permission
    ):
        """Test removing a member."""
        owner = business_with_members["owner_membership"]
        member1 = business_with_members["member1_membership"]
        business = business_with_members["business"]

        RolePermission.objects.create(
            role=owner.role,
            permission=can_remove_member_permission,
            scope=PermissionScope.BUSINESS,
        )

        api_client.force_authenticate(user=owner.user)

        url = f"/api/v1/business/{business.slug}/members/{member1.id}/remove/"
        response = api_client.post(url, format="json")

        assert response.status_code == status.HTTP_200_OK

        member1.refresh_from_db()
        assert member1.status == MembershipStatus.REMOVED


@pytest.mark.django_db
class TestBusinessMemberReactivateView:
    """Tests for reactivating member endpoint."""

    def test_reactivate_suspended_member(
        self, api_client, business_with_members, can_suspend_member_permission
    ):
        """Test reactivating a suspended member."""
        owner = business_with_members["owner_membership"]
        member1 = business_with_members["member1_membership"]
        business = business_with_members["business"]

        # Suspend the member first
        member1.status = MembershipStatus.SUSPENDED
        member1.save(update_fields=["status"])

        RolePermission.objects.create(
            role=owner.role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.BUSINESS,
        )

        api_client.force_authenticate(user=owner.user)

        url = f"/api/v1/business/{business.slug}/members/{member1.id}/reactivate/"
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK

        member1.refresh_from_db()
        assert member1.status == MembershipStatus.ACTIVE

    def test_reactivate_removed_member(
        self, api_client, business_with_members, can_suspend_member_permission
    ):
        """Test reactivating a removed member."""
        owner = business_with_members["owner_membership"]
        member1 = business_with_members["member1_membership"]
        business = business_with_members["business"]

        member1.status = MembershipStatus.REMOVED
        member1.save(update_fields=["status"])

        RolePermission.objects.create(
            role=owner.role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.BUSINESS,
        )

        api_client.force_authenticate(user=owner.user)

        url = f"/api/v1/business/{business.slug}/members/{member1.id}/reactivate/"
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK

        member1.refresh_from_db()
        assert member1.status == MembershipStatus.ACTIVE


@pytest.mark.django_db
class TestBusinessMemberLeaveView:
    """Tests for member leave endpoint."""

    def test_member_leave(self, api_client, business_with_members):
        """Test member leaving a business."""
        member1 = business_with_members["member1_membership"]
        business = business_with_members["business"]

        api_client.force_authenticate(user=member1.user)

        url = f"/api/v1/business/{business.slug}/members/leave/"
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK

        member1.refresh_from_db()
        assert member1.status == MembershipStatus.LEFT

    def test_owner_cannot_leave(self, api_client, business_with_members):
        """Test that owner cannot leave."""
        owner = business_with_members["owner_membership"]
        business = business_with_members["business"]

        api_client.force_authenticate(user=owner.user)

        url = f"/api/v1/business/{business.slug}/members/leave/"
        response = api_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "owner" in response.data["error"]["message"].lower()


@pytest.mark.django_db
class TestMyMembershipsListView:
    """Tests for user's own memberships endpoint."""

    def test_list_my_memberships(self, api_client, business_with_members):
        """Test listing own memberships."""
        member1 = business_with_members["member1_membership"]

        api_client.force_authenticate(user=member1.user)

        url = "/api/v1/users/me/memberships/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_membership_includes_account_name_and_slug(
        self, api_client, business_with_members
    ):
        """Test that membership response includes account_name and account_slug."""
        member1 = business_with_members["member1_membership"]
        business = business_with_members["business"]

        api_client.force_authenticate(user=member1.user)

        url = "/api/v1/users/me/memberships/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Find the business membership
        biz_membership = next(
            m for m in response.data if m["account_type"] == AccountType.BUSINESS
        )
        assert biz_membership["account_name"] == business.legal_name
        assert biz_membership["account_slug"] == business.slug

    def test_list_memberships_unauthenticated(self, api_client):
        """Test that unauthenticated user cannot access memberships."""
        url = "/api/v1/users/me/memberships/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestMyMembershipDetailView:
    """Tests for user's own membership detail endpoint."""

    def test_get_my_membership(self, api_client, business_with_members):
        """Test getting own membership details."""
        member1 = business_with_members["member1_membership"]

        api_client.force_authenticate(user=member1.user)

        url = f"/api/v1/users/me/memberships/{member1.id}/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert str(response.data["id"]) == str(member1.id)

    def test_cannot_view_other_membership(self, api_client, business_with_members):
        """Test that user cannot view another user's membership."""
        member1 = business_with_members["member1_membership"]
        member2 = business_with_members["member2_membership"]

        api_client.force_authenticate(user=member1.user)

        url = f"/api/v1/users/me/memberships/{member2.id}/"
        response = api_client.get(url)

        # Returns 403 because user is denied access to another user's membership
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestRolePermissionView:
    """Tests for role permission management endpoint."""

    def test_add_permission_to_role(
        self, api_client, business_with_members, permission
    ):
        """Test adding permission to a role."""
        owner = business_with_members["owner_membership"]
        business = business_with_members["business"]

        # Create a custom role
        custom_role = Role.objects.create(
            name="Custom",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
            is_system_role=False,
        )

        api_client.force_authenticate(user=owner.user)

        url = f"/api/v1/business/{business.slug}/roles/{custom_role.id}/permissions/"
        data = {
            "permission_id": str(permission.id),
            "scope": PermissionScope.BUSINESS,
        }
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert RolePermission.objects.filter(
            role=custom_role, permission=permission
        ).exists()

    def test_remove_permission_from_role(
        self, api_client, business_with_members, permission
    ):
        """Test removing permission from a role."""
        owner = business_with_members["owner_membership"]
        business = business_with_members["business"]

        # Create a custom role with permission
        custom_role = Role.objects.create(
            name="Custom",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
            is_system_role=False,
        )
        RolePermission.objects.create(
            role=custom_role,
            permission=permission,
            scope=PermissionScope.BUSINESS,
        )

        api_client.force_authenticate(user=owner.user)

        url = f"/api/v1/business/{business.slug}/roles/{custom_role.id}/permissions/"
        data = {"permission_id": str(permission.id)}
        response = api_client.delete(url, data, format="json")

        # Returns 200 with updated role data (permission removed)
        assert response.status_code == status.HTTP_200_OK
        assert not RolePermission.objects.filter(
            role=custom_role, permission=permission
        ).exists()


@pytest.mark.django_db
class TestPlatformRoleViews:
    """Tests for platform role endpoints."""

    def test_list_platform_roles(self, api_client, platform_owner_membership):
        """Test listing platform roles as platform owner."""
        api_client.force_authenticate(user=platform_owner_membership.user)

        url = "/api/v1/platform/roles/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_non_platform_member_denied(self, api_client, user):
        """Test that non-platform members cannot access platform roles."""
        api_client.force_authenticate(user=user)

        url = "/api/v1/platform/roles/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestPlatformMemberViews:
    """Tests for platform member endpoints."""

    def test_list_platform_members(
        self, api_client, platform_owner_membership, can_view_members_permission
    ):
        """Test listing platform members."""
        # Give platform owner the permission
        RolePermission.objects.create(
            role=platform_owner_membership.role,
            permission=can_view_members_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        api_client.force_authenticate(user=platform_owner_membership.user)

        url = "/api/v1/platform/members/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestPlatformRolePermissionView:
    """Tests for platform role permission management endpoint (Issue #11)."""

    def test_add_permission_to_platform_role(
        self, api_client, platform_owner_membership, permission
    ):
        """Test adding permission to a platform role."""
        platform_id = platform_owner_membership.account_id

        # Create a custom platform role
        custom_role = Role.objects.create(
            name="Custom Platform Role",
            account_type=AccountType.PLATFORM,
            account_id=platform_id,
            level=5,
            is_system_role=False,
        )

        api_client.force_authenticate(user=platform_owner_membership.user)

        url = f"/api/v1/platform/roles/{custom_role.id}/permissions/"
        data = {
            "permission_id": str(permission.id),
            "scope": PermissionScope.PLATFORM_ONLY,
        }
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert RolePermission.objects.filter(
            role=custom_role, permission=permission
        ).exists()

    def test_remove_permission_from_platform_role(
        self, api_client, platform_owner_membership, permission
    ):
        """Test removing permission from a platform role."""
        platform_id = platform_owner_membership.account_id

        # Create a custom platform role with a permission
        custom_role = Role.objects.create(
            name="Custom Platform Role",
            account_type=AccountType.PLATFORM,
            account_id=platform_id,
            level=5,
            is_system_role=False,
        )
        RolePermission.objects.create(
            role=custom_role,
            permission=permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        api_client.force_authenticate(user=platform_owner_membership.user)

        url = f"/api/v1/platform/roles/{custom_role.id}/permissions/"
        data = {"permission_id": str(permission.id)}
        response = api_client.delete(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert not RolePermission.objects.filter(
            role=custom_role, permission=permission
        ).exists()

    def test_platform_role_permission_non_member_denied(
        self, api_client, platform_owner_membership, permission, another_user
    ):
        """Test that non-platform members cannot manage role permissions."""
        platform_id = platform_owner_membership.account_id

        # Create a custom platform role
        custom_role = Role.objects.create(
            name="Custom Platform Role",
            account_type=AccountType.PLATFORM,
            account_id=platform_id,
            level=5,
            is_system_role=False,
        )

        # Authenticate as a non-platform member (another_user has no platform membership)
        api_client.force_authenticate(user=another_user)

        url = f"/api/v1/platform/roles/{custom_role.id}/permissions/"
        data = {
            "permission_id": str(permission.id),
            "scope": PermissionScope.PLATFORM_ONLY,
        }
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestBusinessMemberDetailPermissions:
    """Tests for _permissions injection on business member detail."""

    def test_permissions_injected_in_get(
        self,
        api_client,
        business_with_members,
        can_change_member_role_permission,
        can_suspend_member_permission,
        can_remove_member_permission,
        can_ban_member_permission,
    ):
        """Test that _permissions dict is injected in GET response."""
        owner = business_with_members["owner_membership"]
        member1 = business_with_members["member1_membership"]
        business = business_with_members["business"]

        # Give owner management permissions
        for perm in [
            can_change_member_role_permission,
            can_suspend_member_permission,
            can_remove_member_permission,
            can_ban_member_permission,
        ]:
            RolePermission.objects.get_or_create(
                role=owner.role,
                permission=perm,
                defaults={"scope": PermissionScope.BUSINESS},
            )

        api_client.force_authenticate(user=owner.user)
        url = f"/api/v1/business/{business.slug}/members/{member1.id}/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "_permissions" in response.data
        perms = response.data["_permissions"]
        assert perms["can_change_role"] is True
        assert perms["can_suspend"] is True
        assert perms["can_remove"] is True
        assert perms["can_ban"] is True
        assert perms["can_reactivate"] is False  # member is active

    def test_base_member_sees_no_permissions(
        self,
        api_client,
        business_with_members,
    ):
        """Test that base member sees all permissions as False."""
        member1 = business_with_members["member1_membership"]
        member2 = business_with_members["member2_membership"]
        business = business_with_members["business"]

        api_client.force_authenticate(user=member1.user)
        url = f"/api/v1/business/{business.slug}/members/{member2.id}/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        perms = response.data["_permissions"]
        assert perms["can_change_role"] is False
        assert perms["can_suspend"] is False
        assert perms["can_remove"] is False
        assert perms["can_ban"] is False
        assert perms["can_reactivate"] is False


@pytest.mark.django_db
class TestBusinessRoleDetailPermissions:
    """Tests for _permissions injection on business role detail."""

    def test_permissions_injected_for_custom_role(
        self,
        api_client,
        business_with_members,
        can_create_role_permission,
    ):
        """Test that _permissions shows can_edit/can_delete=True for custom role."""
        owner = business_with_members["owner_membership"]
        business = business_with_members["business"]

        RolePermission.objects.get_or_create(
            role=owner.role,
            permission=can_create_role_permission,
            defaults={"scope": PermissionScope.BUSINESS},
        )

        custom_role = Role.objects.create(
            name="Manager",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
            is_system_role=False,
        )

        api_client.force_authenticate(user=owner.user)
        url = f"/api/v1/business/{business.slug}/roles/{custom_role.id}/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "_permissions" in response.data
        perms = response.data["_permissions"]
        assert perms["can_edit"] is True
        assert perms["can_delete"] is True
        assert perms["can_modify_permissions"] is True

    def test_permissions_false_for_system_role(
        self,
        api_client,
        business_with_members,
        can_create_role_permission,
    ):
        """Test that system roles have can_edit=False."""
        owner = business_with_members["owner_membership"]
        owner_role = business_with_members["owner_role"]
        business = business_with_members["business"]

        RolePermission.objects.get_or_create(
            role=owner_role,
            permission=can_create_role_permission,
            defaults={"scope": PermissionScope.BUSINESS},
        )

        api_client.force_authenticate(user=owner.user)
        url = f"/api/v1/business/{business.slug}/roles/{owner_role.id}/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        perms = response.data["_permissions"]
        assert perms["can_edit"] is False
        assert perms["can_delete"] is False

    def test_no_permissions_on_patch(
        self,
        api_client,
        business_with_members,
        can_edit_role_permission,
    ):
        """Test that _permissions is NOT injected in PATCH response."""
        owner = business_with_members["owner_membership"]
        business = business_with_members["business"]

        RolePermission.objects.get_or_create(
            role=owner.role,
            permission=can_edit_role_permission,
            defaults={"scope": PermissionScope.BUSINESS},
        )

        custom_role = Role.objects.create(
            name="Manager",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
            is_system_role=False,
        )

        api_client.force_authenticate(user=owner.user)
        url = f"/api/v1/business/{business.slug}/roles/{custom_role.id}/"
        response = api_client.patch(url, {"name": "Updated"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "_permissions" not in response.data


@pytest.mark.django_db
class TestPlatformMemberDetailPermissions:
    """Tests for _permissions injection on platform member detail."""

    def test_permissions_injected_in_get(
        self,
        api_client,
        platform,
        platform_owner_membership,
        platform_admin_membership,
        can_change_member_role_permission,
        can_suspend_member_permission,
    ):
        """Test _permissions on platform member detail."""
        # Give owner permissions
        for perm in [can_change_member_role_permission, can_suspend_member_permission]:
            RolePermission.objects.get_or_create(
                role=platform_owner_membership.role,
                permission=perm,
                defaults={"scope": PermissionScope.PLATFORM_ONLY},
            )

        api_client.force_authenticate(user=platform_owner_membership.user)
        url = f"/api/v1/platform/members/{platform_admin_membership.id}/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "_permissions" in response.data
        perms = response.data["_permissions"]
        assert perms["can_change_role"] is True
        assert perms["can_suspend"] is True


@pytest.mark.django_db
class TestPlatformRoleDetailPermissions:
    """Tests for _permissions injection on platform role detail."""

    def test_permissions_injected_for_custom_role(
        self,
        api_client,
        platform,
        platform_owner_membership,
        can_create_role_permission,
    ):
        """Test _permissions on platform role detail."""
        RolePermission.objects.get_or_create(
            role=platform_owner_membership.role,
            permission=can_create_role_permission,
            defaults={"scope": PermissionScope.PLATFORM_ONLY},
        )

        custom_role = Role.objects.create(
            name="Custom Platform",
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            level=7,
            is_system_role=False,
        )

        api_client.force_authenticate(user=platform_owner_membership.user)
        url = f"/api/v1/platform/roles/{custom_role.id}/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "_permissions" in response.data
        perms = response.data["_permissions"]
        assert perms["can_edit"] is True
        assert perms["can_delete"] is True
        assert perms["can_modify_permissions"] is True


@pytest.mark.django_db
class TestErrorHandling:
    """Tests for API error handling."""

    def test_nonexistent_business_404(self, authenticated_client):
        """Test accessing non-existent business returns 404."""
        url = "/api/v1/business/nonexistent-slug/roles/"
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_nonexistent_role_404(self, api_client, business_with_members):
        """Test accessing non-existent role returns 404."""
        owner = business_with_members["owner_membership"]
        business = business_with_members["business"]
        api_client.force_authenticate(user=owner.user)

        fake_id = uuid4()
        url = f"/api/v1/business/{business.slug}/roles/{fake_id}/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_nonexistent_membership_404(self, api_client, business_with_members):
        """Test accessing non-existent membership returns 404."""
        owner = business_with_members["owner_membership"]
        business = business_with_members["business"]
        api_client.force_authenticate(user=owner.user)

        fake_id = uuid4()
        url = f"/api/v1/business/{business.slug}/members/{fake_id}/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestRoleListMemberCount:
    """Tests for member_count annotation on role list responses."""

    def test_role_list_includes_member_count(
        self,
        api_client,
        business_with_members,
    ):
        """Role list includes member_count for each role."""
        owner = business_with_members["owner_membership"]
        api_client.force_authenticate(user=owner.user)

        url = f"/api/v1/business/{business_with_members['business'].slug}/roles/"
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        for role_data in response.data:
            assert "member_count" in role_data
            assert isinstance(role_data["member_count"], int)

    def test_member_count_reflects_active_members(
        self,
        api_client,
        business_with_members,
    ):
        """member_count counts only active, non-deleted members."""
        owner = business_with_members["owner_membership"]
        api_client.force_authenticate(user=owner.user)

        url = f"/api/v1/business/{business_with_members['business'].slug}/roles/"
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        # Owner role should have at least 1 active member (the owner)
        owner_role_data = next(
            (r for r in response.data if r["id"] == str(owner.role_id)),
            None,
        )
        assert owner_role_data is not None
        assert owner_role_data["member_count"] >= 1


# ==========================================================================
# Platform Member Action Tests
# ==========================================================================


@pytest.mark.django_db
class TestPlatformMemberActions:
    """Tests for platform member action endpoints (suspend/ban/remove/reactivate/leave)."""

    def test_change_platform_member_role(
        self,
        api_client,
        platform_with_members,
        can_change_member_role_permission,
    ):
        """Test changing a platform member's role."""
        owner = platform_with_members["owner_membership"]
        member = platform_with_members["member_membership"]
        platform = platform_with_members["platform"]

        RolePermission.objects.create(
            role=owner.role,
            permission=can_change_member_role_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        new_role = Role.objects.create(
            name="Custom Role",
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            level=7,
        )

        api_client.force_authenticate(user=owner.user)
        url = f"/api/v1/platform/members/{member.id}/role/"
        response = api_client.patch(url, {"role_id": str(new_role.id)}, format="json")

        assert response.status_code == status.HTTP_200_OK
        member.refresh_from_db()
        assert member.role == new_role

    def test_suspend_platform_member(
        self,
        api_client,
        platform_with_members,
        can_suspend_member_permission,
    ):
        """Test suspending a platform member."""
        owner = platform_with_members["owner_membership"]
        member = platform_with_members["member_membership"]

        RolePermission.objects.create(
            role=owner.role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        api_client.force_authenticate(user=owner.user)
        url = f"/api/v1/platform/members/{member.id}/suspend/"
        response = api_client.post(url, {"reason": "Policy violation"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        member.refresh_from_db()
        assert member.status == MembershipStatus.SUSPENDED

    def test_ban_platform_member(
        self,
        api_client,
        platform_with_members,
        can_ban_member_permission,
    ):
        """Test banning a platform member."""
        owner = platform_with_members["owner_membership"]
        member = platform_with_members["member_membership"]

        RolePermission.objects.create(
            role=owner.role,
            permission=can_ban_member_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        api_client.force_authenticate(user=owner.user)
        url = f"/api/v1/platform/members/{member.id}/ban/"
        response = api_client.post(url, {"reason": "Permanent ban"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        member.refresh_from_db()
        assert member.status == MembershipStatus.BANNED

    def test_remove_platform_member(
        self,
        api_client,
        platform_with_members,
        can_remove_member_permission,
    ):
        """Test removing a platform member."""
        owner = platform_with_members["owner_membership"]
        member = platform_with_members["member_membership"]

        RolePermission.objects.create(
            role=owner.role,
            permission=can_remove_member_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        api_client.force_authenticate(user=owner.user)
        url = f"/api/v1/platform/members/{member.id}/remove/"
        response = api_client.post(url, format="json")

        assert response.status_code == status.HTTP_200_OK
        member.refresh_from_db()
        assert member.status == MembershipStatus.REMOVED

    def test_reactivate_suspended_platform_member(
        self,
        api_client,
        platform_with_members,
        can_suspend_member_permission,
    ):
        """Test reactivating a suspended platform member."""
        owner = platform_with_members["owner_membership"]
        member = platform_with_members["member_membership"]

        member.status = MembershipStatus.SUSPENDED
        member.save(update_fields=["status"])

        RolePermission.objects.create(
            role=owner.role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        api_client.force_authenticate(user=owner.user)
        url = f"/api/v1/platform/members/{member.id}/reactivate/"
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        member.refresh_from_db()
        assert member.status == MembershipStatus.ACTIVE

    def test_reactivate_removed_platform_member(
        self,
        api_client,
        platform_with_members,
        can_suspend_member_permission,
    ):
        """Test reactivating a removed platform member."""
        owner = platform_with_members["owner_membership"]
        member = platform_with_members["member_membership"]

        member.status = MembershipStatus.REMOVED
        member.save(update_fields=["status"])

        RolePermission.objects.create(
            role=owner.role,
            permission=can_suspend_member_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        api_client.force_authenticate(user=owner.user)
        url = f"/api/v1/platform/members/{member.id}/reactivate/"
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        member.refresh_from_db()
        assert member.status == MembershipStatus.ACTIVE

    def test_platform_member_leave(self, api_client, platform_with_members):
        """Test member leaving a platform."""
        member = platform_with_members["member_membership"]

        api_client.force_authenticate(user=member.user)
        url = "/api/v1/platform/members/leave/"
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        member.refresh_from_db()
        assert member.status == MembershipStatus.LEFT

    def test_platform_owner_cannot_leave(self, api_client, platform_with_members):
        """Test that platform owner cannot leave."""
        owner = platform_with_members["owner_membership"]

        api_client.force_authenticate(user=owner.user)
        url = "/api/v1/platform/members/leave/"
        response = api_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_non_member_cannot_suspend(
        self,
        api_client,
        platform_with_members,
    ):
        """Test that non-platform-member cannot suspend."""
        member = platform_with_members["member_membership"]
        outsider = UserFactory(is_verified=True)

        api_client.force_authenticate(user=outsider)
        url = f"/api/v1/platform/members/{member.id}/suspend/"
        response = api_client.post(url, {"reason": "test"}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_member_without_permission_cannot_suspend(
        self,
        api_client,
        platform_with_members,
    ):
        """Test that base member without permission cannot suspend."""
        member = platform_with_members["member_membership"]
        admin = platform_with_members["admin_membership"]

        # member (base member) tries to suspend admin — no suspend permission
        api_client.force_authenticate(user=member.user)
        url = f"/api/v1/platform/members/{admin.id}/suspend/"
        response = api_client.post(url, {"reason": "test"}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN


# ==========================================================================
# Platform Role CRUD Tests
# ==========================================================================


@pytest.mark.django_db
class TestPlatformRoleCRUD:
    """Tests for platform role CRUD endpoints."""

    def test_create_platform_role(
        self,
        api_client,
        platform_with_members,
        can_create_role_permission,
    ):
        """Test creating a custom platform role."""
        owner = platform_with_members["owner_membership"]

        RolePermission.objects.create(
            role=owner.role,
            permission=can_create_role_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        api_client.force_authenticate(user=owner.user)
        url = "/api/v1/platform/roles/"
        response = api_client.post(
            url,
            {
                "name": "Content Moderator",
                "description": "Moderates content",
                "level": 7,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Content Moderator"

    def test_get_platform_role_detail(self, api_client, platform_with_members):
        """Test retrieving platform role detail."""
        owner = platform_with_members["owner_membership"]
        platform = platform_with_members["platform"]

        custom_role = Role.objects.create(
            name="Custom",
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            level=7,
        )

        api_client.force_authenticate(user=owner.user)
        url = f"/api/v1/platform/roles/{custom_role.id}/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Custom"

    def test_update_platform_role(
        self,
        api_client,
        platform_with_members,
        can_edit_role_permission,
    ):
        """Test updating a custom platform role."""
        owner = platform_with_members["owner_membership"]
        platform = platform_with_members["platform"]

        RolePermission.objects.create(
            role=owner.role,
            permission=can_edit_role_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        custom_role = Role.objects.create(
            name="Old Name",
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            level=7,
            is_system_role=False,
        )

        api_client.force_authenticate(user=owner.user)
        url = f"/api/v1/platform/roles/{custom_role.id}/"
        response = api_client.patch(url, {"name": "New Name"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        custom_role.refresh_from_db()
        assert custom_role.name == "New Name"

    def test_delete_platform_role(
        self,
        api_client,
        platform_with_members,
        can_delete_role_permission,
    ):
        """Test deleting a custom platform role."""
        owner = platform_with_members["owner_membership"]
        platform = platform_with_members["platform"]

        RolePermission.objects.create(
            role=owner.role,
            permission=can_delete_role_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        custom_role = Role.objects.create(
            name="To Delete",
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            level=7,
            is_system_role=False,
        )

        api_client.force_authenticate(user=owner.user)
        url = f"/api/v1/platform/roles/{custom_role.id}/"
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Role.objects.filter(id=custom_role.id).exists()

    def test_cannot_delete_system_platform_role(
        self,
        api_client,
        platform_with_members,
        can_delete_role_permission,
    ):
        """Test that system platform roles cannot be deleted."""
        owner = platform_with_members["owner_membership"]
        owner_role = platform_with_members["owner_role"]

        RolePermission.objects.create(
            role=owner_role,
            permission=can_delete_role_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        api_client.force_authenticate(user=owner.user)
        url = f"/api/v1/platform/roles/{owner_role.id}/"
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_delete_role_with_members(
        self,
        api_client,
        platform_with_members,
        can_delete_role_permission,
    ):
        """Test that roles with active members cannot be deleted."""
        owner = platform_with_members["owner_membership"]
        admin_role = platform_with_members["admin_role"]

        RolePermission.objects.create(
            role=owner.role,
            permission=can_delete_role_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        # admin_role has admin_membership assigned to it
        api_client.force_authenticate(user=owner.user)
        url = f"/api/v1/platform/roles/{admin_role.id}/"
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_role_without_permission_denied(
        self,
        api_client,
        platform_with_members,
    ):
        """Test that base member cannot create roles."""
        member = platform_with_members["member_membership"]

        api_client.force_authenticate(user=member.user)
        url = "/api/v1/platform/roles/"
        response = api_client.post(
            url,
            {"name": "Attempt", "description": "Should fail", "level": 7},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


# ==========================================================================
# Platform Member List Tests
# ==========================================================================


@pytest.mark.django_db
class TestPlatformMemberList:
    """Tests for platform member list endpoints."""

    def test_list_platform_members_paginated(
        self,
        api_client,
        platform_with_members,
        can_view_members_permission,
    ):
        """Test listing platform members returns paginated response."""
        owner = platform_with_members["owner_membership"]

        RolePermission.objects.create(
            role=owner.role,
            permission=can_view_members_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        api_client.force_authenticate(user=owner.user)
        url = "/api/v1/platform/members/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) == 3  # owner + admin + member

    def test_search_platform_members_by_email(
        self,
        api_client,
        platform_with_members,
        can_view_members_permission,
    ):
        """Test searching platform members by email."""
        owner = platform_with_members["owner_membership"]
        admin = platform_with_members["admin_membership"]

        RolePermission.objects.create(
            role=owner.role,
            permission=can_view_members_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        api_client.force_authenticate(user=owner.user)
        url = f"/api/v1/platform/members/?search={admin.user.email}"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

    def test_filter_platform_members_by_role(
        self,
        api_client,
        platform_with_members,
        can_view_members_permission,
    ):
        """Test filtering platform members by role."""
        owner = platform_with_members["owner_membership"]
        admin_role = platform_with_members["admin_role"]

        RolePermission.objects.create(
            role=owner.role,
            permission=can_view_members_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        api_client.force_authenticate(user=owner.user)
        url = f"/api/v1/platform/members/?role_id={admin_role.id}"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_filter_platform_members_by_status(
        self,
        api_client,
        platform_with_members,
        can_view_members_permission,
    ):
        """Test filtering platform members by status."""
        owner = platform_with_members["owner_membership"]
        member = platform_with_members["member_membership"]

        member.status = MembershipStatus.SUSPENDED
        member.save(update_fields=["status"])

        RolePermission.objects.create(
            role=owner.role,
            permission=can_view_members_permission,
            scope=PermissionScope.PLATFORM_ONLY,
        )

        api_client.force_authenticate(user=owner.user)
        url = "/api/v1/platform/members/?include_all=true&status=suspended"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

    def test_get_platform_member_detail(self, api_client, platform_with_members):
        """Test getting platform member detail."""
        owner = platform_with_members["owner_membership"]
        admin = platform_with_members["admin_membership"]

        api_client.force_authenticate(user=owner.user)
        url = f"/api/v1/platform/members/{admin.id}/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(admin.id)


# ==========================================================================
# Platform Role List Member Count
# ==========================================================================


@pytest.mark.django_db
class TestPlatformRoleListMemberCount:
    """Tests for member_count annotation on platform role list."""

    def test_platform_role_list_includes_member_count(
        self,
        api_client,
        platform_with_members,
    ):
        """Platform role list includes member_count for each role."""
        owner = platform_with_members["owner_membership"]

        api_client.force_authenticate(user=owner.user)
        url = "/api/v1/platform/roles/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        for role_data in response.data:
            assert "member_count" in role_data
            assert isinstance(role_data["member_count"], int)


# =============================================================================
# PLATFORM _PERMISSIONS INJECTION TESTS
# =============================================================================


@pytest.mark.django_db
class TestPlatformMemberDetailPermissionsExtended:
    """Test _permissions on platform member detail endpoint."""

    def test_platform_owner_sees_action_permissions_on_member(
        self,
        authenticated_client,
        platform_with_members,
        can_change_member_role_permission,
        can_suspend_member_permission,
        can_remove_member_permission,
        can_ban_member_permission,
        platform_members_url,
    ):
        """Platform owner sees all action permissions on active member."""
        owner = platform_with_members["owner_membership"]
        target = platform_with_members["member_membership"]

        # Assign permissions to owner role
        for perm in [
            can_change_member_role_permission,
            can_suspend_member_permission,
            can_remove_member_permission,
            can_ban_member_permission,
        ]:
            RolePermission.objects.get_or_create(
                role=owner.role,
                permission=perm,
                defaults={"scope": PermissionScope.PLATFORM_ONLY},
            )

        response = authenticated_client.get(f"{platform_members_url}{target.id}/")
        assert response.status_code == 200
        assert "_permissions" in response.data
        perms = response.data["_permissions"]
        assert perms["can_change_role"] is True
        assert perms["can_suspend"] is True
        assert perms["can_remove"] is True
        assert perms["can_ban"] is True
        assert perms["can_reactivate"] is False  # Already active

    def test_platform_base_member_sees_no_permissions_on_peer(
        self,
        api_client,
        platform_with_members,
        platform_members_url,
    ):
        """Platform base member without permissions sees all False."""
        member = platform_with_members["member_membership"]
        admin = platform_with_members["admin_membership"]

        # Authenticate as the base member (third_user)
        api_client.force_authenticate(user=member.user)

        response = api_client.get(f"{platform_members_url}{admin.id}/")
        assert response.status_code == 200
        assert "_permissions" in response.data
        perms = response.data["_permissions"]
        assert perms["can_change_role"] is False
        assert perms["can_suspend"] is False

    def test_platform_owner_sees_reactivate_for_suspended(
        self,
        authenticated_client,
        platform_with_members,
        can_suspend_member_permission,
        platform_members_url,
    ):
        """Platform owner sees can_reactivate=True for suspended member."""
        owner = platform_with_members["owner_membership"]
        target = platform_with_members["member_membership"]

        # Suspend the target
        target.status = MembershipStatus.SUSPENDED
        target.save()

        RolePermission.objects.get_or_create(
            role=owner.role,
            permission=can_suspend_member_permission,
            defaults={"scope": PermissionScope.PLATFORM_ONLY},
        )

        response = authenticated_client.get(f"{platform_members_url}{target.id}/")
        assert response.status_code == 200
        perms = response.data["_permissions"]
        assert perms["can_reactivate"] is True


@pytest.mark.django_db
class TestPlatformRoleDetailPermissionsExtended:
    """Test _permissions on platform role detail endpoint."""

    def test_platform_owner_sees_role_permissions_on_custom(
        self,
        authenticated_client,
        platform,
        platform_owner_membership,
        can_create_role_permission,
        platform_roles_url,
    ):
        """Platform owner sees all permissions on custom role."""
        RolePermission.objects.get_or_create(
            role=platform_owner_membership.role,
            permission=can_create_role_permission,
            defaults={"scope": PermissionScope.PLATFORM_ONLY},
        )

        custom_role = Role.objects.create(
            name="Custom Platform Reviewer",
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            level=6,
            is_system_role=False,
        )

        response = authenticated_client.get(f"{platform_roles_url}{custom_role.id}/")
        assert response.status_code == 200
        assert "_permissions" in response.data
        perms = response.data["_permissions"]
        assert perms["can_edit"] is True
        assert perms["can_delete"] is True
        assert perms["can_modify_permissions"] is True

    def test_platform_system_role_no_edit_delete(
        self,
        authenticated_client,
        platform_owner_membership,
        platform_owner_role,
        can_create_role_permission,
        platform_roles_url,
    ):
        """System platform roles have can_edit=False, can_delete=False."""
        RolePermission.objects.get_or_create(
            role=platform_owner_membership.role,
            permission=can_create_role_permission,
            defaults={"scope": PermissionScope.PLATFORM_ONLY},
        )

        response = authenticated_client.get(
            f"{platform_roles_url}{platform_owner_role.id}/"
        )
        assert response.status_code == 200
        assert "_permissions" in response.data
        perms = response.data["_permissions"]
        assert perms["can_edit"] is False
        assert perms["can_delete"] is False

    def test_platform_member_without_role_permission(
        self,
        api_client,
        platform_with_members,
        platform_roles_url,
    ):
        """Platform member without can_create_role sees no permissions."""
        member = platform_with_members["member_membership"]
        api_client.force_authenticate(user=member.user)

        # Create a custom role to view
        platform = platform_with_members["platform"]
        custom_role = Role.objects.create(
            name="Reviewer Role",
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            level=7,
            is_system_role=False,
        )

        response = api_client.get(f"{platform_roles_url}{custom_role.id}/")
        assert response.status_code == 200
        assert "_permissions" in response.data
        perms = response.data["_permissions"]
        assert perms["can_edit"] is False
        assert perms["can_delete"] is False
        assert perms["can_modify_permissions"] is False
