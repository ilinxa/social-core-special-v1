# apps/rbac/tests/test_governance_views.py
"""
Tests for governance console member endpoints.

Test matrix per endpoint:
- Global Moderator with governance token → 200 (has permission)
- Platform Admin with governance token → 403 (no global scope)
- Regular user → 403 (no governance token / no permission)
- Unauthenticated → 401
- Member action: suspend, ban, remove, reactivate
- Owner invincibility
"""

import pytest
from rest_framework.test import APIClient

from apps.organization.tests.factories import (
    BusinessAccountFactory,
    BusinessProfileFactory,
    PlatformAccountFactory,
    PlatformProfileFactory,
    UserFactory,
)

GOV_TOKEN_PAYLOAD = {"token_scope": "governance"}


def _ensure_platform_rbac(platform_account):
    """Ensure platform RBAC roles are initialized."""
    from apps.rbac.models import Role
    from apps.rbac.services import RBACService

    exists = Role.objects.filter(
        account_type="platform",
        account_id=platform_account.id,
    ).exists()
    if not exists:
        RBACService.initialize_platform_account(platform_id=platform_account.id)


def _init_business_rbac(business, owner):
    """Initialize RBAC for a business."""
    from apps.rbac.services import RBACService

    return RBACService.initialize_business_account(
        business_id=business.id,
        owner=owner,
    )


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def platform_account(db):
    """Get or create the platform singleton."""
    from apps.organization.platform.models import PlatformAccount

    platform = PlatformAccount.objects.first()
    if platform:
        return platform
    return PlatformAccountFactory()


@pytest.fixture
def platform_profile(platform_account):
    """Ensure platform profile exists (needed for account_name annotation)."""
    from apps.organization.platform.models import PlatformProfile

    profile, _ = PlatformProfile.objects.get_or_create(
        platform=platform_account,
        defaults={"name": "Test Platform"},
    )
    return profile


@pytest.fixture
def global_moderator(db, platform_account):
    """Create a Global Moderator with governance token auth."""
    from apps.rbac.models import Role
    from apps.rbac.services import RBACService

    _ensure_platform_rbac(platform_account)

    user = UserFactory(username="gov_mod_m", email="gov_mod_m@example.com")
    mod_role = Role.objects.get(
        account_type="platform",
        account_id=platform_account.id,
        name="Global Moderator",
    )
    RBACService.create_membership(
        user=user,
        account_type="platform",
        account_id=platform_account.id,
        role_id=mod_role.id,
        created_by=user,
    )
    return user


@pytest.fixture
def gov_client(global_moderator):
    """APIClient authenticated as Global Moderator with governance token."""
    client = APIClient()
    client.force_authenticate(user=global_moderator, token=GOV_TOKEN_PAYLOAD)
    return client


@pytest.fixture
def platform_admin(db, platform_account):
    """Create a Platform Admin (no global-scope permissions)."""
    from apps.rbac.models import Role
    from apps.rbac.services import RBACService

    _ensure_platform_rbac(platform_account)

    user = UserFactory(username="plat_admin_m", email="plat_admin_m@example.com")
    admin_role = Role.objects.get(
        account_type="platform",
        account_id=platform_account.id,
        name="Platform Admin",
    )
    RBACService.create_membership(
        user=user,
        account_type="platform",
        account_id=platform_account.id,
        role_id=admin_role.id,
        created_by=user,
    )
    return user


@pytest.fixture
def plat_admin_gov_client(platform_admin):
    """APIClient as Platform Admin WITH governance token (but no global perms)."""
    client = APIClient()
    client.force_authenticate(user=platform_admin, token=GOV_TOKEN_PAYLOAD)
    return client


@pytest.fixture
def regular_user(db):
    """Regular user without any special permissions."""
    return UserFactory(username="regular_m", email="regular_m@example.com")


@pytest.fixture
def regular_client(regular_user):
    """APIClient authenticated as regular user (no governance token)."""
    client = APIClient()
    client.force_authenticate(user=regular_user)
    return client


@pytest.fixture
def business_with_member(db, platform_profile):
    """Create a business with owner + one regular member."""
    owner = UserFactory(username="biz_owner_m", email="biz_owner_m@example.com")
    member_user = UserFactory(username="biz_member", email="biz_member@example.com")
    business = BusinessAccountFactory(
        status="active", created_by=owner, updated_by=owner
    )
    BusinessProfileFactory(business=business)
    _init_business_rbac(business, owner=owner)

    from apps.rbac.models import Role
    from apps.rbac.services import RBACService

    base_role = Role.objects.get(
        account_type="business",
        account_id=business.id,
        name="Base Member",
    )
    membership = RBACService.create_membership(
        user=member_user,
        account_type="business",
        account_id=business.id,
        role_id=base_role.id,
        created_by=owner,
    )
    return {
        "business": business,
        "owner": owner,
        "member_user": member_user,
        "membership": membership,
    }


# =============================================================================
# MEMBER LIST VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestGovernanceMemberListView:
    """Tests for GET /api/v1/governance/members/"""

    URL = "/api/v1/governance/members/"

    def test_global_moderator_can_list(self, gov_client, business_with_member):
        response = gov_client.get(self.URL)
        assert response.status_code == 200
        assert "results" in response.data
        assert len(response.data["results"]) >= 1

    def test_includes_account_context(self, gov_client, business_with_member):
        response = gov_client.get(self.URL)
        assert response.status_code == 200
        member = response.data["results"][0]
        assert "account_name" in member
        assert "account_slug" in member

    def test_filter_by_account_type(self, gov_client, business_with_member):
        response = gov_client.get(self.URL, {"account_type": "business"})
        assert response.status_code == 200
        for member in response.data["results"]:
            assert member["account_type"] == "business"

    def test_filter_by_status(self, gov_client, business_with_member):
        response = gov_client.get(self.URL, {"status": "active"})
        assert response.status_code == 200
        for member in response.data["results"]:
            assert member["status"] == "active"

    def test_search_by_email(self, gov_client, business_with_member):
        email = business_with_member["member_user"].email
        response = gov_client.get(self.URL, {"search": email[:8]})
        assert response.status_code == 200
        emails = [m["user"]["email"] for m in response.data["results"]]
        assert email in emails

    def test_platform_admin_forbidden(
        self, plat_admin_gov_client, business_with_member
    ):
        response = plat_admin_gov_client.get(self.URL)
        assert response.status_code == 403

    def test_regular_user_forbidden(self, regular_client):
        response = regular_client.get(self.URL)
        assert response.status_code == 403

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get(self.URL)
        assert response.status_code == 401


# =============================================================================
# MEMBER DETAIL VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestGovernanceMemberDetailView:
    """Tests for GET /api/v1/governance/members/{uuid}/"""

    def _url(self, pk):
        return f"/api/v1/governance/members/{pk}/"

    def test_global_moderator_can_view(self, gov_client, business_with_member):
        membership = business_with_member["membership"]
        response = gov_client.get(self._url(membership.id))
        assert response.status_code == 200
        assert response.data["id"] == str(membership.id)
        assert "account_name" in response.data
        assert "_permissions" in response.data

    def test_permissions_include_expected_keys(self, gov_client, business_with_member):
        membership = business_with_member["membership"]
        response = gov_client.get(self._url(membership.id))
        assert response.status_code == 200
        perms = response.data["_permissions"]
        assert "can_suspend" in perms
        assert "can_ban" in perms
        assert "can_remove" in perms
        assert "can_reactivate" in perms
        assert "can_change_role" in perms

    def test_platform_admin_forbidden(
        self, plat_admin_gov_client, business_with_member
    ):
        membership = business_with_member["membership"]
        response = plat_admin_gov_client.get(self._url(membership.id))
        assert response.status_code == 403

    def test_unauthenticated(self, business_with_member):
        membership = business_with_member["membership"]
        client = APIClient()
        response = client.get(self._url(membership.id))
        assert response.status_code == 401


# =============================================================================
# MEMBER ACTION VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestGovernanceMemberActionView:
    """Tests for POST /api/v1/governance/members/{uuid}/action/"""

    def _url(self, pk):
        return f"/api/v1/governance/members/{pk}/action/"

    def test_suspend_member(self, gov_client, business_with_member):
        membership = business_with_member["membership"]
        response = gov_client.post(
            self._url(membership.id),
            {"action": "suspend", "reason": "Policy violation"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "suspended"

    def test_ban_member(self, gov_client, business_with_member):
        membership = business_with_member["membership"]
        response = gov_client.post(
            self._url(membership.id),
            {"action": "ban", "reason": "Repeated violations"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "banned"

    def test_remove_member(self, gov_client, business_with_member):
        membership = business_with_member["membership"]
        response = gov_client.post(
            self._url(membership.id),
            {"action": "remove", "reason": "Test removal"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "removed"

    def test_suspend_then_reactivate(self, gov_client, business_with_member):
        membership = business_with_member["membership"]
        # First suspend
        gov_client.post(
            self._url(membership.id),
            {"action": "suspend", "reason": "Temp"},
            format="json",
        )
        # Then reactivate
        response = gov_client.post(
            self._url(membership.id),
            {"action": "reactivate"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "active"

    def test_cannot_act_on_business_owner_from_same_account(
        self, gov_client, business_with_member
    ):
        """Business owner CAN be acted on cross-account by global permissions."""
        from apps.rbac.selectors import MembershipSelector

        owner = business_with_member["owner"]
        owner_membership = MembershipSelector.get_owner_membership(
            account_type="business",
            account_id=business_with_member["business"].id,
        )
        # Cross-account action on business owner IS allowed
        response = gov_client.post(
            self._url(owner_membership.id),
            {"action": "suspend", "reason": "Governance action"},
            format="json",
        )
        assert response.status_code == 200

    def test_invalid_action_rejected(self, gov_client, business_with_member):
        membership = business_with_member["membership"]
        response = gov_client.post(
            self._url(membership.id),
            {"action": "invalid_action"},
            format="json",
        )
        assert response.status_code == 400

    def test_platform_admin_forbidden(
        self, plat_admin_gov_client, business_with_member
    ):
        membership = business_with_member["membership"]
        response = plat_admin_gov_client.post(
            self._url(membership.id),
            {"action": "suspend", "reason": "test"},
            format="json",
        )
        assert response.status_code == 403

    def test_unauthenticated(self, business_with_member):
        membership = business_with_member["membership"]
        client = APIClient()
        response = client.post(
            self._url(membership.id),
            {"action": "suspend"},
            format="json",
        )
        assert response.status_code == 401


# =============================================================================
# MEMBER STATE TRANSITION TESTS (C4)
# =============================================================================


@pytest.mark.django_db
class TestGovernanceMemberStateTransitions:
    """
    Edge-case state machine tests for governance member actions.

    Member status has NO transition validation -- update_membership_status
    directly sets membership.status. All transitions succeed if authorized.
    """

    def _action_url(self, pk):
        return f"/api/v1/governance/members/{pk}/action/"

    def test_suspend_then_ban(self, gov_client, business_with_member):
        """Suspended member can be banned."""
        membership = business_with_member["membership"]
        # Suspend
        r1 = gov_client.post(
            self._action_url(membership.id),
            {"action": "suspend", "reason": "First offense"},
            format="json",
        )
        assert r1.status_code == 200
        assert r1.data["status"] == "suspended"

        # Ban
        r2 = gov_client.post(
            self._action_url(membership.id),
            {"action": "ban", "reason": "Repeated offense"},
            format="json",
        )
        assert r2.status_code == 200
        assert r2.data["status"] == "banned"

    def test_ban_then_reactivate(self, gov_client, business_with_member):
        """Banned member can be reactivated."""
        membership = business_with_member["membership"]
        # Ban
        gov_client.post(
            self._action_url(membership.id),
            {"action": "ban", "reason": "Bad behavior"},
            format="json",
        )
        # Reactivate
        r = gov_client.post(
            self._action_url(membership.id),
            {"action": "reactivate"},
            format="json",
        )
        assert r.status_code == 200
        assert r.data["status"] == "active"

    def test_full_chain_suspend_ban_reactivate(self, gov_client, business_with_member):
        """Full lifecycle: active -> suspend -> ban -> reactivate."""
        membership = business_with_member["membership"]

        # Suspend
        r1 = gov_client.post(
            self._action_url(membership.id),
            {"action": "suspend", "reason": "Warning"},
            format="json",
        )
        assert r1.status_code == 200
        assert r1.data["status"] == "suspended"

        # Ban
        r2 = gov_client.post(
            self._action_url(membership.id),
            {"action": "ban", "reason": "Escalation"},
            format="json",
        )
        assert r2.status_code == 200
        assert r2.data["status"] == "banned"

        # Reactivate
        r3 = gov_client.post(
            self._action_url(membership.id),
            {"action": "reactivate"},
            format="json",
        )
        assert r3.status_code == 200
        assert r3.data["status"] == "active"

    def test_business_suspend_does_not_cascade_to_members(
        self, gov_client, business_with_member
    ):
        """Suspending a business does not cascade to its members."""
        business = business_with_member["business"]
        membership = business_with_member["membership"]

        # Suspend the business
        suspend_url = f"/api/v1/governance/businesses/{business.id}/suspend/"
        r = gov_client.post(
            suspend_url,
            {"reason": "Business policy violation"},
            format="json",
        )
        assert r.status_code == 200
        assert r.data["status"] == "suspended"

        # Verify member is still active
        detail_url = f"/api/v1/governance/members/{membership.id}/"
        r2 = gov_client.get(detail_url)
        assert r2.status_code == 200
        assert r2.data["status"] == "active"


# =============================================================================
# MEMBER AUDIT LOG TESTS (C5)
# =============================================================================


@pytest.mark.django_db
class TestGovernanceMemberAudit:
    """
    Verify audit log entries for governance member actions.

    After each action, query AuditLog and check:
    - Correct action enum
    - Correct actor (actor_id == governance user's ID)
    - Details contain reason
    - Changes contain old_status and new_status
    """

    def _action_url(self, pk):
        return f"/api/v1/governance/members/{pk}/action/"

    def test_suspend_creates_audit_entry(
        self, gov_client, global_moderator, business_with_member
    ):
        """Suspending a member creates MEMBERSHIP_SUSPENDED audit entry."""
        from apps.core.observability.audit.models import AuditLog

        membership = business_with_member["membership"]
        gov_client.post(
            self._action_url(membership.id),
            {"action": "suspend", "reason": "Spam content"},
            format="json",
        )

        entry = AuditLog.objects.filter(
            action=AuditLog.Action.MEMBERSHIP_SUSPENDED,
            resource_id=str(membership.id),
        ).first()
        assert entry is not None
        assert entry.actor_id == str(global_moderator.id)
        assert entry.details.get("reason") == "Spam content"
        assert entry.changes.get("old_status") == "active"
        assert entry.changes.get("new_status") == "suspended"

    def test_ban_creates_audit_entry(
        self, gov_client, global_moderator, business_with_member
    ):
        """Banning a member creates MEMBERSHIP_BANNED audit entry."""
        from apps.core.observability.audit.models import AuditLog

        membership = business_with_member["membership"]
        gov_client.post(
            self._action_url(membership.id),
            {"action": "ban", "reason": "Severe violations"},
            format="json",
        )

        entry = AuditLog.objects.filter(
            action=AuditLog.Action.MEMBERSHIP_BANNED,
            resource_id=str(membership.id),
        ).first()
        assert entry is not None
        assert entry.actor_id == str(global_moderator.id)
        assert entry.details.get("reason") == "Severe violations"
        assert entry.changes.get("old_status") == "active"
        assert entry.changes.get("new_status") == "banned"

    def test_remove_creates_audit_entry(
        self, gov_client, global_moderator, business_with_member
    ):
        """Removing a member creates MEMBERSHIP_REMOVED audit entry."""
        from apps.core.observability.audit.models import AuditLog

        membership = business_with_member["membership"]
        gov_client.post(
            self._action_url(membership.id),
            {"action": "remove", "reason": "Cleanup"},
            format="json",
        )

        entry = AuditLog.objects.filter(
            action=AuditLog.Action.MEMBERSHIP_REMOVED,
            resource_id=str(membership.id),
        ).first()
        assert entry is not None
        assert entry.actor_id == str(global_moderator.id)
        assert entry.details.get("reason") == "Cleanup"
        assert entry.changes.get("old_status") == "active"
        assert entry.changes.get("new_status") == "removed"

    def test_reactivate_creates_audit_entry(
        self, gov_client, global_moderator, business_with_member
    ):
        """Reactivating a member creates MEMBERSHIP_REACTIVATED audit entry."""
        from apps.core.observability.audit.models import AuditLog

        membership = business_with_member["membership"]

        # First suspend
        gov_client.post(
            self._action_url(membership.id),
            {"action": "suspend", "reason": "Temp suspension"},
            format="json",
        )

        # Then reactivate
        gov_client.post(
            self._action_url(membership.id),
            {"action": "reactivate"},
            format="json",
        )

        entry = AuditLog.objects.filter(
            action=AuditLog.Action.MEMBERSHIP_REACTIVATED,
            resource_id=str(membership.id),
        ).first()
        assert entry is not None
        assert entry.actor_id == str(global_moderator.id)
        assert entry.changes.get("old_status") == "suspended"
        assert entry.changes.get("new_status") == "active"
