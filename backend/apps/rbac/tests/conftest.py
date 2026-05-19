# apps/rbac/tests/conftest.py
"""
Pytest configuration and fixtures for RBAC app tests.

These fixtures are available to all tests in the rbac app.
"""

from uuid import uuid4

import pytest
from django.conf import settings

# =============================================================================
# SKIP MARKERS
# =============================================================================


def is_sqlite():
    """Check if the default database is SQLite."""
    db_engine = settings.DATABASES.get("default", {}).get("ENGINE", "")
    return "sqlite" in db_engine


# Skip marker for tests that require PostgreSQL (e.g., JSON contains lookup)
skip_if_sqlite = pytest.mark.skipif(
    is_sqlite(),
    reason="Test requires PostgreSQL (JSONField contains lookup not supported on SQLite)",
)


# Skip marker for tests that require a real cache backend
def is_dummy_or_locmem_cache():
    """Check if cache is DummyCache or LocMemCache (non-persistent caches)."""
    backend = settings.CACHES.get("default", {}).get("BACKEND", "")
    return "DummyCache" in backend or "LocMemCache" in backend


skip_if_locmem_cache = pytest.mark.skipif(
    is_dummy_or_locmem_cache(),
    reason="Test requires a real cache backend (Redis or Memcached)",
)

from apps.core.constants import AccountType, MembershipStatus, PermissionScope
from apps.rbac.models import Membership, Permission, Role, RolePermission
from apps.rbac.tests.factories import (  # User/Account factories; Permission factories; Role factories; Role Permission factories; Membership factories; Composite
    BannedMembershipFactory,
    BaseMemberRoleFactory,
    BusinessAccountFactory,
    BusinessMembershipFactory,
    BusinessPermissionFactory,
    BusinessRoleFactory,
    BusinessRolePermissionFactory,
    BusinessWithOwnerFactory,
    GlobalRolePermissionFactory,
    MembershipFactory,
    OwnerMembershipFactory,
    OwnerRoleFactory,
    PermissionFactory,
    PlatformAccountFactory,
    PlatformMembershipFactory,
    PlatformPermissionFactory,
    PlatformRoleFactory,
    RoleFactory,
    RolePermissionFactory,
    SuspendedMembershipFactory,
    UserFactory,
)

# =============================================================================
# USER FIXTURES
# =============================================================================


@pytest.fixture
def user(db):
    """Verified user override — rbac tests rely on ``is_verified=True``."""
    return UserFactory(is_verified=True)


@pytest.fixture
def another_user(db):
    """Create and return another verified user (for permission tests)."""
    return UserFactory(is_verified=True)


@pytest.fixture
def third_user(db):
    """Create and return a third verified user (for multi-member tests)."""
    return UserFactory(is_verified=True)


@pytest.fixture
def user_factory(db):
    """Return the UserFactory for creating users in tests."""
    return UserFactory


# =============================================================================
# ACCOUNT FIXTURES
# =============================================================================


@pytest.fixture
def business(db, user):
    """Create and return a business account."""
    return BusinessAccountFactory(created_by=user)


@pytest.fixture
def another_business(db, user):
    """Create and return another business account."""
    return BusinessAccountFactory(created_by=user)


@pytest.fixture
def platform(db):
    """Create and return the platform account singleton."""
    return PlatformAccountFactory()


@pytest.fixture
def business_factory(db):
    """Return the BusinessAccountFactory."""
    return BusinessAccountFactory


@pytest.fixture
def platform_factory(db):
    """Return the PlatformAccountFactory."""
    return PlatformAccountFactory


# =============================================================================
# PERMISSION FIXTURES
# =============================================================================


@pytest.fixture
def permission(db):
    """Create and return a test permission."""
    return PermissionFactory()


@pytest.fixture
def business_permission(db):
    """Create and return a business-scope permission."""
    return BusinessPermissionFactory()


@pytest.fixture
def platform_permission(db):
    """Create and return a platform-scope permission."""
    return PlatformPermissionFactory()


@pytest.fixture
def permission_factory(db):
    """Return the PermissionFactory."""
    return PermissionFactory


@pytest.fixture
def can_view_members_permission(db):
    """Get or create the can_view_members permission."""
    perm, _ = Permission.objects.get_or_create(
        code="can_view_members",
        defaults={
            "name": "View Members",
            "description": "View the list of account members",
            "category": "membership",
            "applicable_scopes": ["business", "platform_only", "global_only"],
        },
    )
    return perm


@pytest.fixture
def can_change_member_role_permission(db):
    """Get or create the can_change_member_role permission."""
    perm, _ = Permission.objects.get_or_create(
        code="can_change_member_role",
        defaults={
            "name": "Change Member Role",
            "description": "Change the role assigned to a member",
            "category": "membership",
            "applicable_scopes": ["business", "global_only"],
        },
    )
    return perm


@pytest.fixture
def can_suspend_member_permission(db):
    """Get or create the can_suspend_member permission."""
    perm, _ = Permission.objects.get_or_create(
        code="can_suspend_member",
        defaults={
            "name": "Suspend Member",
            "description": "Temporarily suspend a member's access",
            "category": "membership",
            "applicable_scopes": ["business", "global_only"],
        },
    )
    return perm


@pytest.fixture
def can_remove_member_permission(db):
    """Get or create the can_remove_member permission."""
    perm, _ = Permission.objects.get_or_create(
        code="can_remove_member",
        defaults={
            "name": "Remove Member",
            "description": "Remove members from the account",
            "category": "membership",
            "applicable_scopes": ["business", "global_only"],
        },
    )
    return perm


@pytest.fixture
def can_ban_member_permission(db):
    """Get or create the can_ban_member permission."""
    perm, _ = Permission.objects.get_or_create(
        code="can_ban_member",
        defaults={
            "name": "Ban Member",
            "description": "Permanently ban a member from the account",
            "category": "membership",
            "applicable_scopes": ["business", "global_only"],
        },
    )
    return perm


@pytest.fixture
def can_create_role_permission(db):
    """Get or create the can_create_role permission."""
    perm, _ = Permission.objects.get_or_create(
        code="can_create_role",
        defaults={
            "name": "Create Role",
            "description": "Create new custom roles for the account",
            "category": "roles",
            "applicable_scopes": [
                "business",
                "platform_only",
            ],  # NO global_only per registry
        },
    )
    return perm


@pytest.fixture
def can_edit_role_permission(db):
    """Get or create the can_edit_role permission."""
    perm, _ = Permission.objects.get_or_create(
        code="can_edit_role",
        defaults={
            "name": "Edit Role",
            "description": "Modify existing custom roles",
            "category": "roles",
            "applicable_scopes": [
                "business",
                "platform_only",
            ],  # NO global_only per registry
        },
    )
    return perm


@pytest.fixture
def can_delete_role_permission(db):
    """Get or create the can_delete_role permission."""
    perm, _ = Permission.objects.get_or_create(
        code="can_delete_role",
        defaults={
            "name": "Delete Role",
            "description": "Delete custom roles from the account",
            "category": "roles",
            "applicable_scopes": [
                "business",
                "platform_only",
            ],  # NO global_only per registry
        },
    )
    return perm


# =============================================================================
# ROLE FIXTURES
# =============================================================================


@pytest.fixture
def role(db, business):
    """Create and return a test role for the business."""
    return RoleFactory(
        account_type=AccountType.BUSINESS,
        account_id=business.id,
    )


@pytest.fixture
def owner_role(db, business):
    """Create and return an owner role for the business."""
    return Role.objects.create(
        name="Owner",
        account_type=AccountType.BUSINESS,
        account_id=business.id,
        level=0,
        is_system_role=True,
    )


@pytest.fixture
def base_member_role(db, business):
    """Create and return a base member role for the business."""
    return Role.objects.create(
        name="Base Member",
        account_type=AccountType.BUSINESS,
        account_id=business.id,
        level=10,
        is_system_role=True,
    )


@pytest.fixture
def admin_role(db, business):
    """Create and return an admin role for the business."""
    return RoleFactory(
        name="Admin",
        account_type=AccountType.BUSINESS,
        account_id=business.id,
        level=2,
    )


@pytest.fixture
def manager_role(db, business):
    """Create and return a manager role for the business."""
    return RoleFactory(
        name="Manager",
        account_type=AccountType.BUSINESS,
        account_id=business.id,
        level=5,
    )


@pytest.fixture
def platform_owner_role(db, platform):
    """Create and return a platform owner role."""
    return Role.objects.create(
        name="Platform Owner",
        account_type=AccountType.PLATFORM,
        account_id=platform.id,
        level=0,
        is_system_role=True,
    )


@pytest.fixture
def platform_admin_role(db, platform):
    """Create and return a platform admin role."""
    return Role.objects.create(
        name="Platform Admin",
        account_type=AccountType.PLATFORM,
        account_id=platform.id,
        level=2,
        is_system_role=False,
    )


@pytest.fixture
def global_moderator_role(db, platform):
    """Create and return a global moderator role."""
    return Role.objects.create(
        name="Global Moderator",
        account_type=AccountType.PLATFORM,
        account_id=platform.id,
        level=5,
        is_system_role=False,
    )


@pytest.fixture
def role_factory(db):
    """Return the RoleFactory."""
    return RoleFactory


# =============================================================================
# MEMBERSHIP FIXTURES
# =============================================================================


@pytest.fixture
def membership(db, user, role):
    """Create and return a test membership."""
    return Membership.objects.create(
        user=user,
        account_type=role.account_type,
        account_id=role.account_id,
        role=role,
        is_owner=False,
        status=MembershipStatus.ACTIVE,
    )


@pytest.fixture
def owner_membership(db, user, owner_role):
    """Create and return an owner membership."""
    return Membership.objects.create(
        user=user,
        account_type=owner_role.account_type,
        account_id=owner_role.account_id,
        role=owner_role,
        is_owner=True,
        status=MembershipStatus.ACTIVE,
    )


@pytest.fixture
def platform_owner_membership(db, user, platform_owner_role):
    """Create and return a platform owner membership."""
    return Membership.objects.create(
        user=user,
        account_type=platform_owner_role.account_type,
        account_id=platform_owner_role.account_id,
        role=platform_owner_role,
        is_owner=True,
        status=MembershipStatus.ACTIVE,
    )


@pytest.fixture
def platform_admin_membership(db, another_user, platform_admin_role):
    """Create and return a platform admin membership."""
    return Membership.objects.create(
        user=another_user,
        account_type=platform_admin_role.account_type,
        account_id=platform_admin_role.account_id,
        role=platform_admin_role,
        is_owner=False,
        status=MembershipStatus.ACTIVE,
    )


@pytest.fixture
def global_moderator_membership(db, another_user, global_moderator_role):
    """Create and return a global moderator membership."""
    return Membership.objects.create(
        user=another_user,
        account_type=global_moderator_role.account_type,
        account_id=global_moderator_role.account_id,
        role=global_moderator_role,
        is_owner=False,
        status=MembershipStatus.ACTIVE,
    )


@pytest.fixture
def membership_factory(db):
    """Return the MembershipFactory."""
    return MembershipFactory


# =============================================================================
# COMPOSITE FIXTURES
# =============================================================================


@pytest.fixture
def business_with_members(
    db, business, owner_role, base_member_role, user, another_user, third_user
):
    """
    Create a business with owner and two regular members.

    Returns a dict with:
    - business: BusinessAccount
    - owner_membership: Membership (user is owner)
    - member1_membership: Membership (another_user)
    - member2_membership: Membership (third_user)
    """
    owner_membership = Membership.objects.create(
        user=user,
        account_type=AccountType.BUSINESS,
        account_id=business.id,
        role=owner_role,
        is_owner=True,
        status=MembershipStatus.ACTIVE,
    )
    member1_membership = Membership.objects.create(
        user=another_user,
        account_type=AccountType.BUSINESS,
        account_id=business.id,
        role=base_member_role,
        is_owner=False,
        status=MembershipStatus.ACTIVE,
    )
    member2_membership = Membership.objects.create(
        user=third_user,
        account_type=AccountType.BUSINESS,
        account_id=business.id,
        role=base_member_role,
        is_owner=False,
        status=MembershipStatus.ACTIVE,
    )
    return {
        "business": business,
        "owner_membership": owner_membership,
        "member1_membership": member1_membership,
        "member2_membership": member2_membership,
        "owner_role": owner_role,
        "base_member_role": base_member_role,
    }


@pytest.fixture
def platform_base_member_role(db, platform):
    """Create and return a platform base member role."""
    return Role.objects.create(
        name="Base Member",
        account_type=AccountType.PLATFORM,
        account_id=platform.id,
        level=10,
        is_system_role=True,
    )


@pytest.fixture
def platform_base_membership(db, third_user, platform_base_member_role):
    """Create and return a platform base membership."""
    return Membership.objects.create(
        user=third_user,
        account_type=platform_base_member_role.account_type,
        account_id=platform_base_member_role.account_id,
        role=platform_base_member_role,
        is_owner=False,
        status=MembershipStatus.ACTIVE,
    )


@pytest.fixture
def platform_with_members(
    db,
    platform,
    platform_owner_role,
    platform_admin_role,
    platform_base_member_role,
    user,
    another_user,
    third_user,
):
    """Create a platform with owner and two regular members.

    Returns a dict with:
    - platform: PlatformAccount
    - owner_membership: Membership (user is owner)
    - admin_membership: Membership (another_user)
    - member_membership: Membership (third_user)
    """
    owner_membership = Membership.objects.create(
        user=user,
        account_type=AccountType.PLATFORM,
        account_id=platform.id,
        role=platform_owner_role,
        is_owner=True,
        status=MembershipStatus.ACTIVE,
    )
    admin_membership = Membership.objects.create(
        user=another_user,
        account_type=AccountType.PLATFORM,
        account_id=platform.id,
        role=platform_admin_role,
        is_owner=False,
        status=MembershipStatus.ACTIVE,
    )
    member_membership = Membership.objects.create(
        user=third_user,
        account_type=AccountType.PLATFORM,
        account_id=platform.id,
        role=platform_base_member_role,
        is_owner=False,
        status=MembershipStatus.ACTIVE,
    )
    return {
        "platform": platform,
        "owner_membership": owner_membership,
        "admin_membership": admin_membership,
        "member_membership": member_membership,
        "owner_role": platform_owner_role,
        "admin_role": platform_admin_role,
        "base_member_role": platform_base_member_role,
    }


@pytest.fixture
def role_with_permissions(
    db, role, can_view_members_permission, can_change_member_role_permission
):
    """
    Create a role with some permissions assigned.

    Returns the role with can_view_members and can_change_member_role permissions.
    """
    RolePermission.objects.create(
        role=role,
        permission=can_view_members_permission,
        scope=PermissionScope.BUSINESS,
    )
    RolePermission.objects.create(
        role=role,
        permission=can_change_member_role_permission,
        scope=PermissionScope.BUSINESS,
    )
    return role


# =============================================================================
# URL FIXTURES
# =============================================================================


@pytest.fixture
def permissions_url():
    """Return the permissions list URL."""
    return "/api/v1/rbac/permissions/"


@pytest.fixture
def business_roles_url(business):
    """Return the business roles URL."""
    return f"/api/v1/business/{business.slug}/roles/"


@pytest.fixture
def business_members_url(business):
    """Return the business members URL."""
    return f"/api/v1/business/{business.slug}/members/"


@pytest.fixture
def platform_roles_url():
    """Return the platform roles URL."""
    return "/api/v1/platform/roles/"


@pytest.fixture
def platform_members_url():
    """Return the platform members URL."""
    return "/api/v1/platform/members/"


@pytest.fixture
def my_memberships_url():
    """Return the user's memberships URL."""
    return "/api/v1/users/me/memberships/"
