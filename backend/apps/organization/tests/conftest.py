# apps/organization/tests/conftest.py
"""
Pytest configuration and fixtures for Organization app tests.

These fixtures are available to all tests in the organization app.
All business fixtures initialize RBAC (roles + owner membership).
"""

import pytest
from rest_framework.test import APIClient

from apps.organization.tests.factories import (  # User factories; Platform factories; Business factories
    BusinessAccountFactory,
    BusinessAccountWithProfileFactory,
    BusinessProfileFactory,
    BusinessSlugHistoryFactory,
    PlatformAccountFactory,
    PlatformProfileFactory,
    StaffUserFactory,
    SuperuserFactory,
    SuspendedBusinessFactory,
    UserFactory,
    VerifiedBusinessFactory,
)


def _init_business_rbac(business, owner):
    """Initialize RBAC for a business created via factory (not via service)."""
    from apps.rbac.services import RBACService

    return RBACService.initialize_business_account(
        business_id=business.id,
        owner=owner,
    )


# =============================================================================
# API CLIENT FIXTURES
# =============================================================================


@pytest.fixture
def api_client():
    """Return an unauthenticated DRF APIClient instance."""
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user):
    """Return an APIClient authenticated as a regular user."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def staff_client(api_client, staff_user):
    """Return an APIClient authenticated as a staff user."""
    api_client.force_authenticate(user=staff_user)
    return api_client


@pytest.fixture
def admin_client(api_client, superuser):
    """Return an APIClient authenticated as a superuser."""
    api_client.force_authenticate(user=superuser)
    return api_client


# =============================================================================
# USER FIXTURES
# =============================================================================


@pytest.fixture
def user(db):
    """Create and return a regular test user."""
    return UserFactory()


@pytest.fixture
def user_factory(db):
    """Return the UserFactory for creating users in tests."""
    return UserFactory


@pytest.fixture
def staff_user(db):
    """Create and return a staff user."""
    return StaffUserFactory()


@pytest.fixture
def superuser(db):
    """Create and return a superuser."""
    return SuperuserFactory()


# =============================================================================
# PLATFORM FIXTURES
# =============================================================================


@pytest.fixture
def platform_account(db):
    """
    Get or create the platform account singleton.

    Note: Uses the existing platform account if it exists (from migrations).
    """
    from apps.organization.platform.models import PlatformAccount

    # Try to get existing platform account (created by migration)
    platform = PlatformAccount.objects.first()
    if platform:
        return platform
    # Otherwise create one
    return PlatformAccountFactory()


@pytest.fixture
def platform_profile(platform_account):
    """
    Get or create the platform profile.

    Note: Uses the existing platform profile if it exists.
    """
    from apps.organization.platform.models import PlatformProfile

    try:
        return platform_account.profile
    except PlatformProfile.DoesNotExist:
        return PlatformProfileFactory(platform=platform_account)


@pytest.fixture
def configured_platform(platform_account):
    """Return a configured platform account."""
    platform_account.is_configured = True
    platform_account.save(update_fields=["is_configured"])
    return platform_account


@pytest.fixture
def platform_account_factory(db):
    """Return the PlatformAccountFactory."""
    return PlatformAccountFactory


@pytest.fixture
def platform_profile_factory(db):
    """Return the PlatformProfileFactory."""
    return PlatformProfileFactory


# =============================================================================
# BUSINESS FIXTURES
# =============================================================================


@pytest.fixture
def business_account(db, user):
    """Create a business account with RBAC setup. User is the owner."""
    business = BusinessAccountFactory(created_by=user, updated_by=user)
    _init_business_rbac(business, owner=user)
    return business


@pytest.fixture
def business_with_profile(db, user):
    """Create a business account with profile and RBAC setup."""
    business = BusinessAccountFactory(created_by=user, updated_by=user)
    BusinessProfileFactory(business=business)
    _init_business_rbac(business, owner=user)
    return business


@pytest.fixture
def verified_business(db, user):
    """Create a verified business account with RBAC setup."""
    business = VerifiedBusinessFactory(created_by=user, updated_by=user)
    BusinessProfileFactory(business=business)
    _init_business_rbac(business, owner=user)
    return business


@pytest.fixture
def suspended_business(db, user):
    """Create a suspended business account with RBAC setup."""
    business = SuspendedBusinessFactory(created_by=user, updated_by=user)
    BusinessProfileFactory(business=business)
    _init_business_rbac(business, owner=user)
    return business


@pytest.fixture
def business_account_factory(db):
    """Return the BusinessAccountFactory."""
    return BusinessAccountFactory


@pytest.fixture
def business_profile_factory(db):
    """Return the BusinessProfileFactory."""
    return BusinessProfileFactory


@pytest.fixture
def business_slug_history_factory(db):
    """Return the BusinessSlugHistoryFactory."""
    return BusinessSlugHistoryFactory


# =============================================================================
# UTILITY FIXTURES
# =============================================================================


@pytest.fixture
def another_user(db):
    """Create and return another user (for permission tests)."""
    return UserFactory(username="anotheruser", email="another@example.com")


@pytest.fixture
def another_business(db, another_user):
    """Create a business owned by another user with RBAC setup."""
    business = BusinessAccountFactory(
        legal_name="Another Business",
        slug="another-business",
        created_by=another_user,
        updated_by=another_user,
    )
    BusinessProfileFactory(business=business)
    _init_business_rbac(business, owner=another_user)
    return business


@pytest.fixture
def member_user(db, business_with_profile):
    """Create a user with Base Member role in business_with_profile (no special permissions)."""
    from apps.core.constants import AccountType
    from apps.rbac.selectors import RoleSelector
    from apps.rbac.services import RBACService

    member = UserFactory(username="memberuser", email="member@example.com")

    base_role = RoleSelector.get_base_member_role(
        account_type=AccountType.BUSINESS,
        account_id=business_with_profile.id,
    )

    RBACService.create_membership(
        user=member,
        account_type=AccountType.BUSINESS,
        account_id=business_with_profile.id,
        role_id=base_role.id,
        created_by=business_with_profile.created_by,
    )

    return member


@pytest.fixture
def non_member_user(db):
    """Create a user with no membership in any business."""
    return UserFactory(username="nonmember", email="nonmember@example.com")
