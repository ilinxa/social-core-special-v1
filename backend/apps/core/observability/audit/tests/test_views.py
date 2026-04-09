# apps/core/observability/audit/tests/test_views.py
"""
Tests for Audit REST API endpoints (D13).

Three scoped endpoints:
    - Business: /api/v1/business/{slug}/audit/
    - Platform: /api/v1/platform/audit/
    - Governance: /api/v1/governance/audit/
"""

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.constants import AccountType
from apps.core.observability.audit.models import AuditLog
from apps.organization.tests.factories import (
    BusinessAccountFactory,
    BusinessProfileFactory,
    UserFactory,
)
from apps.rbac.services import RBACService

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def platform_account(db):
    from apps.organization.platform.models import PlatformAccount

    platform = PlatformAccount.objects.first()
    if platform:
        return platform
    from apps.organization.tests.factories import PlatformAccountFactory

    return PlatformAccountFactory()


@pytest.fixture
def platform_with_rbac(platform_account):
    from apps.rbac.models import Role

    exists = Role.objects.filter(
        account_type=AccountType.PLATFORM,
        account_id=platform_account.id,
    ).exists()
    if not exists:
        RBACService.initialize_platform_account(platform_id=platform_account.id)
    return platform_account


@pytest.fixture
def owner(db):
    return UserFactory(username="biz_owner", email="owner@example.com")


@pytest.fixture
def business_with_profile(db, owner):
    business = BusinessAccountFactory(created_by=owner, updated_by=owner)
    BusinessProfileFactory(business=business)
    RBACService.initialize_business_account(business_id=business.id, owner=owner)
    return business


@pytest.fixture
def member_with_audit_perm(db, business_with_profile, platform_with_rbac):
    """Business member with can_view_audit_logs permission via owner role."""
    # Owner already has all permissions via Owner role
    return business_with_profile.created_by


@pytest.fixture
def member_without_perm(db, business_with_profile):
    """Business base member with no permissions."""
    from apps.rbac.selectors import RoleSelector

    member = UserFactory(username="basemember", email="basemember@example.com")
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
def platform_owner_user(db, platform_with_rbac):
    from apps.rbac.selectors import RoleSelector

    plat_owner = UserFactory(username="platowner", email="platowner@example.com")
    owner_role = RoleSelector.get_owner_role(
        account_type=AccountType.PLATFORM,
        account_id=platform_with_rbac.id,
    )
    RBACService.create_membership(
        user=plat_owner,
        account_type=AccountType.PLATFORM,
        account_id=platform_with_rbac.id,
        role_id=owner_role.id,
        created_by=plat_owner,
    )
    return plat_owner


@pytest.fixture
def global_moderator_user(db, platform_with_rbac):
    from apps.rbac.models import Role

    moderator = UserFactory(username="globmod", email="globmod@example.com")
    mod_role = Role.objects.get(
        account_type=AccountType.PLATFORM,
        account_id=platform_with_rbac.id,
        name="Global Moderator",
    )
    RBACService.create_membership(
        user=moderator,
        account_type=AccountType.PLATFORM,
        account_id=platform_with_rbac.id,
        role_id=mod_role.id,
        created_by=moderator,
    )
    return moderator


@pytest.fixture
def non_member(db):
    return UserFactory(username="nonmember", email="nonmember@example.com")


def _create_business_logs(business):
    """Create sample business audit logs."""
    logs = []
    for action in [
        AuditLog.Action.BUSINESS_CREATED,
        AuditLog.Action.BUSINESS_UPDATED,
    ]:
        logs.append(
            AuditLog.objects.create(
                actor_id=str(business.created_by.id),
                actor_email=business.created_by.email,
                action=action,
                resource_type="BusinessAccount",
                resource_id=str(business.id),
                resource_repr=str(business),
                outcome=AuditLog.Outcome.SUCCESS,
            )
        )
    return logs


def _create_platform_logs():
    """Create sample platform audit logs."""
    return [
        AuditLog.objects.create(
            actor_type=AuditLog.ActorType.ADMIN,
            action=AuditLog.Action.PLATFORM_SETTINGS_UPDATED,
            resource_type="PlatformAccount",
            resource_id="platform",
            outcome=AuditLog.Outcome.SUCCESS,
        )
    ]


# =============================================================================
# BUSINESS AUDIT TESTS
# =============================================================================


@pytest.mark.django_db
class TestBusinessAuditListView:
    """Tests for GET /api/v1/business/{slug}/audit/"""

    def test_owner_can_view_audit(self, business_with_profile, member_with_audit_perm):
        client = APIClient()
        client.force_authenticate(user=member_with_audit_perm)
        _create_business_logs(business_with_profile)

        response = client.get(f"/api/v1/business/{business_with_profile.slug}/audit/")

        assert response.status_code == 200
        assert response.data["count"] == 2
        assert len(response.data["results"]) == 2

    def test_base_member_cannot_view_audit(
        self, business_with_profile, member_without_perm
    ):
        client = APIClient()
        client.force_authenticate(user=member_without_perm)

        response = client.get(f"/api/v1/business/{business_with_profile.slug}/audit/")

        assert response.status_code == 403

    def test_non_member_cannot_view_audit(self, business_with_profile, non_member):
        client = APIClient()
        client.force_authenticate(user=non_member)

        response = client.get(f"/api/v1/business/{business_with_profile.slug}/audit/")

        assert response.status_code == 403

    def test_unauthenticated_returns_401(self, business_with_profile):
        client = APIClient()

        response = client.get(f"/api/v1/business/{business_with_profile.slug}/audit/")

        assert response.status_code == 401

    def test_only_returns_business_scoped_logs(
        self, business_with_profile, member_with_audit_perm
    ):
        """Business audit should NOT include platform or other business logs."""
        client = APIClient()
        client.force_authenticate(user=member_with_audit_perm)
        _create_business_logs(business_with_profile)
        _create_platform_logs()

        response = client.get(f"/api/v1/business/{business_with_profile.slug}/audit/")

        assert response.status_code == 200
        assert response.data["count"] == 2
        for entry in response.data["results"]:
            assert entry["resource_type"] == "BusinessAccount"
            assert entry["resource_id"] == str(business_with_profile.id)

    def test_action_filter(self, business_with_profile, member_with_audit_perm):
        client = APIClient()
        client.force_authenticate(user=member_with_audit_perm)
        _create_business_logs(business_with_profile)

        response = client.get(
            f"/api/v1/business/{business_with_profile.slug}/audit/",
            {"action": "org.business.created"},
        )

        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["action"] == "org.business.created"

    def test_empty_results(self, business_with_profile, member_with_audit_perm):
        client = APIClient()
        client.force_authenticate(user=member_with_audit_perm)

        response = client.get(f"/api/v1/business/{business_with_profile.slug}/audit/")

        assert response.status_code == 200
        assert response.data["count"] == 0
        assert response.data["results"] == []

    def test_global_moderator_can_view_business_audit(
        self, business_with_profile, global_moderator_user
    ):
        """Governance actors with can_view_audit_logs can view business audit."""
        client = APIClient()
        client.force_authenticate(user=global_moderator_user)
        _create_business_logs(business_with_profile)

        response = client.get(f"/api/v1/business/{business_with_profile.slug}/audit/")

        assert response.status_code == 200
        assert response.data["count"] == 2


# =============================================================================
# PLATFORM AUDIT TESTS
# =============================================================================


@pytest.mark.django_db
class TestPlatformAuditListView:
    """Tests for GET /api/v1/platform/audit/"""

    def test_platform_owner_can_view_audit(self, platform_owner_user):
        client = APIClient()
        client.force_authenticate(user=platform_owner_user)
        _create_platform_logs()

        response = client.get("/api/v1/platform/audit/")

        assert response.status_code == 200
        assert response.data["count"] >= 1

    def test_non_member_cannot_view_audit(self, non_member, platform_with_rbac):
        client = APIClient()
        client.force_authenticate(user=non_member)

        response = client.get("/api/v1/platform/audit/")

        assert response.status_code == 403

    def test_unauthenticated_returns_401(self):
        client = APIClient()

        response = client.get("/api/v1/platform/audit/")

        assert response.status_code == 401

    def test_only_returns_platform_scoped_logs(self, platform_owner_user):
        """Platform audit should NOT include general auth or business logs."""
        client = APIClient()
        client.force_authenticate(user=platform_owner_user)
        _create_platform_logs()

        # Also create a login log (should NOT appear in platform audit)
        AuditLog.objects.create(
            action=AuditLog.Action.LOGIN_SUCCESS,
            resource_type="DeviceSession",
            resource_id="session-1",
            outcome=AuditLog.Outcome.SUCCESS,
        )

        response = client.get("/api/v1/platform/audit/")

        assert response.status_code == 200
        for entry in response.data["results"]:
            assert entry["action"].startswith(
                ("org.platform.", "admin.", "auth.governance.")
            )


# =============================================================================
# GOVERNANCE AUDIT TESTS
# =============================================================================


@pytest.mark.django_db
class TestGovernanceAuditListView:
    """Tests for GET /api/v1/governance/audit/"""

    def test_unauthenticated_returns_401(self):
        client = APIClient()

        response = client.get("/api/v1/governance/audit/")

        assert response.status_code == 401

    def test_regular_user_without_governance_token_returns_403(self, non_member):
        """Standard auth without governance token → 403."""
        client = APIClient()
        client.force_authenticate(user=non_member)

        response = client.get("/api/v1/governance/audit/")

        assert response.status_code == 403
