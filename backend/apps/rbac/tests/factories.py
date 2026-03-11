# apps/rbac/tests/factories.py
"""
Factory-boy factories for RBAC app tests.

Usage:
    from apps.rbac.tests.factories import RoleFactory, MembershipFactory

    # Create a role
    role = RoleFactory()

    # Create with specific attributes
    membership = MembershipFactory(is_owner=True)

    # Build without saving to DB
    role = RoleFactory.build()
"""

import factory
from factory.django import DjangoModelFactory

from apps.core.constants import AccountType, PermissionScope, MembershipStatus
from apps.rbac.models import Permission, Role, RolePermission, Membership
from apps.organization.platform.models import PlatformAccount
from apps.users.tests.factories import UserFactory, VerifiedUserFactory  # noqa: F401

# Canonical BusinessAccountFactory lives in organization — re-export for compatibility
from apps.organization.tests.factories import BusinessAccountFactory  # noqa: F401


# =============================================================================
# ACCOUNT FACTORIES
# =============================================================================


class PlatformAccountFactory(DjangoModelFactory):
    """Factory for PlatformAccount (singleton)."""

    class Meta:
        model = PlatformAccount
        django_get_or_create = ("singleton_key",)

    singleton_key = 1
    is_configured = True
    max_members = 5  # Matches production default
    settings = factory.LazyFunction(dict)


# =============================================================================
# PERMISSION FACTORIES
# =============================================================================


class PermissionFactory(DjangoModelFactory):
    """Factory for Permission."""

    class Meta:
        model = Permission

    code = factory.Sequence(lambda n: f"can_test_permission_{n}")
    name = factory.LazyAttribute(lambda obj: obj.code.replace("_", " ").title())
    description = "Test permission"
    category = "test"
    applicable_scopes = factory.LazyFunction(
        lambda: ["business", "platform_only", "global_only"]
    )


class BusinessPermissionFactory(PermissionFactory):
    """Factory for business-scope permission."""

    applicable_scopes = factory.LazyFunction(lambda: ["business"])


class PlatformPermissionFactory(PermissionFactory):
    """Factory for platform-scope permission."""

    applicable_scopes = factory.LazyFunction(
        lambda: ["platform_only", "global_only"]
    )


# =============================================================================
# ROLE FACTORIES
# =============================================================================


class RoleFactory(DjangoModelFactory):
    """Factory for Role."""

    class Meta:
        model = Role

    name = factory.Sequence(lambda n: f"Test Role {n}")
    account_type = AccountType.BUSINESS
    account_id = factory.LazyAttribute(
        lambda obj: BusinessAccountFactory().id
    )
    level = 5
    is_system_role = False
    description = "Test role for unit testing"


class BusinessRoleFactory(RoleFactory):
    """Factory for business role."""

    account_type = AccountType.BUSINESS


class PlatformRoleFactory(RoleFactory):
    """Factory for platform role."""

    account_type = AccountType.PLATFORM
    account_id = factory.LazyAttribute(
        lambda obj: PlatformAccountFactory().id
    )


class OwnerRoleFactory(RoleFactory):
    """Factory for owner role (level 0)."""

    name = "Owner"
    level = 0
    is_system_role = True


class BaseMemberRoleFactory(RoleFactory):
    """Factory for base member role (level 10)."""

    name = "Base Member"
    level = 10
    is_system_role = True


# =============================================================================
# ROLE PERMISSION FACTORIES
# =============================================================================


class RolePermissionFactory(DjangoModelFactory):
    """Factory for RolePermission."""

    class Meta:
        model = RolePermission

    role = factory.SubFactory(RoleFactory)
    permission = factory.SubFactory(PermissionFactory)
    scope = PermissionScope.BUSINESS


class BusinessRolePermissionFactory(RolePermissionFactory):
    """Factory for business-scoped role permission."""

    scope = PermissionScope.BUSINESS


class GlobalRolePermissionFactory(RolePermissionFactory):
    """Factory for global-scoped role permission."""

    scope = PermissionScope.GLOBAL_ONLY


# =============================================================================
# MEMBERSHIP FACTORIES
# =============================================================================


class MembershipFactory(DjangoModelFactory):
    """Factory for Membership."""

    class Meta:
        model = Membership

    user = factory.SubFactory(UserFactory)
    account_type = AccountType.BUSINESS
    account_id = factory.LazyAttribute(
        lambda obj: BusinessAccountFactory().id
    )
    role = factory.SubFactory(RoleFactory)
    is_owner = False
    status = MembershipStatus.ACTIVE


class BusinessMembershipFactory(MembershipFactory):
    """Factory for business membership."""

    account_type = AccountType.BUSINESS


class PlatformMembershipFactory(MembershipFactory):
    """Factory for platform membership."""

    account_type = AccountType.PLATFORM
    account_id = factory.LazyAttribute(
        lambda obj: PlatformAccountFactory().id
    )
    role = factory.SubFactory(PlatformRoleFactory)


class OwnerMembershipFactory(MembershipFactory):
    """Factory for owner membership."""

    is_owner = True
    role = factory.SubFactory(OwnerRoleFactory)


class SuspendedMembershipFactory(MembershipFactory):
    """Factory for suspended membership."""

    status = MembershipStatus.SUSPENDED


class BannedMembershipFactory(MembershipFactory):
    """Factory for banned membership."""

    status = MembershipStatus.BANNED


# =============================================================================
# COMPOSITE FACTORIES
# =============================================================================


class BusinessWithOwnerFactory(DjangoModelFactory):
    """
    Factory that creates a business with initialized RBAC.

    This creates:
    - BusinessAccount
    - Owner role + Base Member role
    - Owner membership

    Usage:
        result = BusinessWithOwnerFactory()
        business = result.business
        owner_membership = result.membership
        owner_user = result.user
    """

    class Meta:
        model = Membership

    user = factory.SubFactory(UserFactory)
    account_type = AccountType.BUSINESS
    is_owner = True
    status = MembershipStatus.ACTIVE

    @factory.lazy_attribute
    def account_id(self):
        """Create business and return its ID."""
        business = BusinessAccountFactory(created_by=self.user)
        return business.id

    @factory.lazy_attribute
    def role(self):
        """Create owner role for the business."""
        return Role.objects.create(
            name="Owner",
            account_type=AccountType.BUSINESS,
            account_id=self.account_id,
            level=0,
            is_system_role=True,
        )

    @classmethod
    def _after_postgeneration(cls, instance, create, results=None):
        """Create Base Member role after membership is created."""
        if create:
            Role.objects.get_or_create(
                name="Base Member",
                account_type=AccountType.BUSINESS,
                account_id=instance.account_id,
                defaults={
                    "level": 10,
                    "is_system_role": True,
                }
            )

    @property
    def business(self):
        """Get the associated business."""
        return BusinessAccount.objects.get(id=self.account_id)
