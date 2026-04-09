# apps/organization/tests/business/test_governance_views.py
"""
Tests for governance console business endpoints.

Test matrix per endpoint:
- Global Moderator with governance token → 200 (has permission)
- Platform Admin with governance token → 403 (no global scope)
- Regular user → 403 (no governance token / no permission)
- Unauthenticated → 401
- State machine transitions
"""

import pytest
from rest_framework.test import APIClient

from apps.organization.business.selectors import BusinessAccountSelector
from apps.organization.tests.factories import (
    BusinessAccountFactory,
    BusinessProfileFactory,
    SuspendedBusinessFactory,
    UserFactory,
)

GOV_TOKEN_PAYLOAD = {"token_scope": "governance"}


def _init_business_rbac(business, owner):
    """Initialize RBAC for a business."""
    from apps.rbac.services import RBACService

    return RBACService.initialize_business_account(
        business_id=business.id,
        owner=owner,
    )


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
    from apps.organization.tests.factories import PlatformAccountFactory

    return PlatformAccountFactory()


@pytest.fixture
def global_moderator(db, platform_account):
    """Create a Global Moderator with governance token auth."""
    from apps.rbac.models import Role
    from apps.rbac.services import RBACService

    _ensure_platform_rbac(platform_account)

    user = UserFactory(username="gov_mod", email="gov_mod@example.com")
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

    user = UserFactory(username="plat_admin", email="plat_admin@example.com")
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
    return UserFactory(username="regular", email="regular@example.com")


@pytest.fixture
def regular_client(regular_user):
    """APIClient authenticated as regular user (no governance token)."""
    client = APIClient()
    client.force_authenticate(user=regular_user)
    return client


@pytest.fixture
def active_business(db):
    """Create an active business with profile and RBAC."""
    owner = UserFactory(username="biz_owner", email="biz_owner@example.com")
    business = BusinessAccountFactory(
        status="active",
        created_by=owner,
        updated_by=owner,
    )
    BusinessProfileFactory(business=business)
    _init_business_rbac(business, owner=owner)
    return business


@pytest.fixture
def suspended_business(db):
    """Create a suspended business with profile and RBAC."""
    owner = UserFactory(username="susp_owner", email="susp_owner@example.com")
    business = SuspendedBusinessFactory(created_by=owner, updated_by=owner)
    BusinessProfileFactory(business=business)
    _init_business_rbac(business, owner=owner)
    return business


# =============================================================================
# LIST VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestGovernanceBusinessListView:
    """Tests for GET /api/v1/governance/businesses/"""

    URL = "/api/v1/governance/businesses/"

    def test_global_moderator_can_list(self, gov_client, active_business):
        response = gov_client.get(self.URL)
        assert response.status_code == 200
        assert "results" in response.data
        assert len(response.data["results"]) >= 1

    def test_filter_by_status(self, gov_client, active_business, suspended_business):
        response = gov_client.get(self.URL, {"status": "active"})
        assert response.status_code == 200
        slugs = [b["slug"] for b in response.data["results"]]
        assert active_business.slug in slugs
        assert suspended_business.slug not in slugs

    def test_filter_by_search(self, gov_client, active_business):
        response = gov_client.get(self.URL, {"search": active_business.legal_name[:5]})
        assert response.status_code == 200
        assert len(response.data["results"]) >= 1

    def test_includes_member_count(self, gov_client, active_business):
        response = gov_client.get(self.URL)
        assert response.status_code == 200
        biz = next(
            b for b in response.data["results"] if b["id"] == str(active_business.id)
        )
        assert "member_count" in biz
        assert biz["member_count"] >= 1  # owner is a member

    def test_platform_admin_forbidden(self, plat_admin_gov_client):
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
# DETAIL VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestGovernanceBusinessDetailView:
    """Tests for GET /api/v1/governance/businesses/{uuid}/"""

    def _url(self, business):
        return f"/api/v1/governance/businesses/{business.id}/"

    def test_global_moderator_can_view(self, gov_client, active_business):
        response = gov_client.get(self._url(active_business))
        assert response.status_code == 200
        assert response.data["id"] == str(active_business.id)
        assert "_permissions" in response.data

    def test_includes_governance_permissions(self, gov_client, active_business):
        response = gov_client.get(self._url(active_business))
        perms = response.data["_permissions"]
        assert "can_suspend" in perms
        assert "can_view_businesses" in perms
        assert "can_transfer_ownership" in perms

    def test_includes_member_count(self, gov_client, active_business):
        response = gov_client.get(self._url(active_business))
        assert "member_count" in response.data
        assert response.data["member_count"] >= 1

    def test_includes_legal_info(self, gov_client, active_business):
        response = gov_client.get(self._url(active_business))
        assert "registration_number" in response.data
        assert "tax_id" in response.data
        assert "legal_address" in response.data

    def test_can_view_deleted_business(self, gov_client, active_business):
        active_business.is_deleted = True
        active_business.status = "deleted"
        active_business.save(update_fields=["is_deleted", "status"])
        response = gov_client.get(self._url(active_business))
        assert response.status_code == 200

    def test_platform_admin_forbidden(self, plat_admin_gov_client, active_business):
        response = plat_admin_gov_client.get(self._url(active_business))
        assert response.status_code == 403

    def test_not_found(self, gov_client):
        import uuid

        response = gov_client.get(f"/api/v1/governance/businesses/{uuid.uuid4()}/")
        assert response.status_code == 404


# =============================================================================
# SUSPEND VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestGovernanceBusinessSuspendView:
    """Tests for POST /api/v1/governance/businesses/{uuid}/suspend/"""

    def _url(self, business):
        return f"/api/v1/governance/businesses/{business.id}/suspend/"

    def test_can_suspend_active_business(self, gov_client, active_business):
        response = gov_client.post(
            self._url(active_business),
            {"reason": "Policy violation"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["status"] == "suspended"

    def test_cannot_suspend_already_suspended(self, gov_client, suspended_business):
        response = gov_client.post(
            self._url(suspended_business),
            {"reason": "Already suspended"},
            format="json",
        )
        assert response.status_code == 400

    def test_reason_required(self, gov_client, active_business):
        response = gov_client.post(self._url(active_business), {}, format="json")
        assert response.status_code == 400

    def test_platform_admin_forbidden(self, plat_admin_gov_client, active_business):
        response = plat_admin_gov_client.post(
            self._url(active_business),
            {"reason": "test"},
            format="json",
        )
        assert response.status_code == 403


# =============================================================================
# REACTIVATE VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestGovernanceBusinessReactivateView:
    """Tests for POST /api/v1/governance/businesses/{uuid}/reactivate/"""

    def _url(self, business):
        return f"/api/v1/governance/businesses/{business.id}/reactivate/"

    def test_can_reactivate_suspended_business(self, gov_client, suspended_business):
        response = gov_client.post(self._url(suspended_business))
        assert response.status_code == 200
        assert response.data["status"] == "active"

    def test_cannot_reactivate_active_business(self, gov_client, active_business):
        response = gov_client.post(self._url(active_business))
        assert response.status_code == 400

    def test_platform_admin_forbidden(self, plat_admin_gov_client, suspended_business):
        response = plat_admin_gov_client.post(self._url(suspended_business))
        assert response.status_code == 403


# =============================================================================
# ARCHIVE VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestGovernanceBusinessArchiveView:
    """Tests for POST /api/v1/governance/businesses/{uuid}/archive/"""

    def _url(self, business):
        return f"/api/v1/governance/businesses/{business.id}/archive/"

    def test_can_archive_active_business(self, gov_client, active_business):
        response = gov_client.post(self._url(active_business))
        assert response.status_code == 200
        assert response.data["status"] == "archived"

    def test_cannot_archive_already_archived(self, gov_client, active_business):
        # First archive
        gov_client.post(self._url(active_business))
        # Try again
        response = gov_client.post(self._url(active_business))
        assert response.status_code == 400

    def test_can_archive_suspended_business(self, gov_client, suspended_business):
        response = gov_client.post(self._url(suspended_business))
        assert response.status_code == 200
        assert response.data["status"] == "archived"


# =============================================================================
# TRANSFER OWNERSHIP VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestGovernanceBusinessTransferView:
    """Tests for POST /api/v1/governance/businesses/{uuid}/transfer-ownership/"""

    def _url(self, business):
        return f"/api/v1/governance/businesses/{business.id}/transfer-ownership/"

    def test_can_transfer_to_member(self, gov_client, active_business):
        """Transfer ownership to an existing member of the business."""
        from apps.core.constants import AccountType
        from apps.rbac.selectors import RoleSelector
        from apps.rbac.services import RBACService

        new_member = UserFactory(username="new_member", email="new_member@example.com")
        base_role = RoleSelector.get_base_member_role(
            account_type=AccountType.BUSINESS,
            account_id=active_business.id,
        )
        RBACService.create_membership(
            user=new_member,
            account_type=AccountType.BUSINESS,
            account_id=active_business.id,
            role_id=base_role.id,
            created_by=active_business.created_by,
        )

        response = gov_client.post(
            self._url(active_business),
            {"new_owner_id": str(new_member.id), "reason": "Governance decision"},
            format="json",
        )
        assert response.status_code == 200

    def test_cannot_transfer_to_non_member(self, gov_client, active_business):
        """Cannot transfer to a user who is not a member."""
        outsider = UserFactory(username="outsider", email="outsider@example.com")
        response = gov_client.post(
            self._url(active_business),
            {"new_owner_id": str(outsider.id)},
            format="json",
        )
        assert response.status_code == 400

    def test_cannot_transfer_to_current_owner(self, gov_client, active_business):
        """Cannot transfer to the user who is already the owner."""
        response = gov_client.post(
            self._url(active_business),
            {"new_owner_id": str(active_business.created_by.id)},
            format="json",
        )
        assert response.status_code == 400

    def test_platform_admin_forbidden(self, plat_admin_gov_client, active_business):
        response = plat_admin_gov_client.post(
            self._url(active_business),
            {"new_owner_id": str(active_business.created_by.id)},
            format="json",
        )
        assert response.status_code == 403


# =============================================================================
# VERIFICATION LIST VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestGovernanceVerificationListView:
    """Tests for GET /api/v1/governance/verification/"""

    URL = "/api/v1/governance/verification/"

    def test_global_moderator_can_list(self, gov_client):
        response = gov_client.get(self.URL)
        assert response.status_code == 200
        assert "results" in response.data

    def test_platform_admin_forbidden(self, plat_admin_gov_client):
        response = plat_admin_gov_client.get(self.URL)
        assert response.status_code == 403


# =============================================================================
# APPROVED CREATORS VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestGovernanceApprovedCreatorsView:
    """Tests for GET /api/v1/governance/approved-creators/"""

    URL = "/api/v1/governance/approved-creators/"

    def test_global_moderator_can_list(self, gov_client):
        response = gov_client.get(self.URL)
        assert response.status_code == 200
        assert "results" in response.data

    def test_returns_approved_creators(self, gov_client):
        creator = UserFactory(
            username="creator", email="creator@example.com", can_create_business=True
        )
        response = gov_client.get(self.URL)
        assert response.status_code == 200
        ids = [u["id"] for u in response.data["results"]]
        assert str(creator.id) in ids

    def test_platform_admin_forbidden(self, plat_admin_gov_client):
        response = plat_admin_gov_client.get(self.URL)
        assert response.status_code == 403


# =============================================================================
# BUSINESS STATE TRANSITION EDGE CASES (C4)
# =============================================================================


@pytest.mark.django_db
class TestGovernanceBusinessStateTransitions:
    """
    Edge-case state machine tests for governance business actions.

    ARCHIVED and DELETED are terminal states (empty valid transitions list).
    """

    def _suspend_url(self, business):
        return f"/api/v1/governance/businesses/{business.id}/suspend/"

    def _reactivate_url(self, business):
        return f"/api/v1/governance/businesses/{business.id}/reactivate/"

    def _archive_url(self, business):
        return f"/api/v1/governance/businesses/{business.id}/archive/"

    def _transfer_url(self, business):
        return f"/api/v1/governance/businesses/{business.id}/transfer-ownership/"

    def test_cannot_reactivate_archived_business(self, gov_client, active_business):
        """Archived is a terminal state -- reactivation must fail."""
        # First archive
        gov_client.post(self._archive_url(active_business))
        # Try to reactivate
        response = gov_client.post(self._reactivate_url(active_business))
        assert response.status_code == 400

    def test_cannot_reactivate_deleted_business(self, gov_client, active_business):
        """Deleted is a terminal state -- reactivation must fail."""
        from apps.core.constants import BusinessStatus
        from apps.organization.business.models import BusinessAccount

        # Force-set to DELETED via all_objects (bypasses soft-delete filter)
        BusinessAccount.all_objects.filter(id=active_business.id).update(
            status=BusinessStatus.DELETED
        )
        active_business.refresh_from_db()

        response = gov_client.post(self._reactivate_url(active_business))
        assert response.status_code == 400

    def test_transfer_to_suspended_member(self, gov_client, active_business):
        """Cannot transfer ownership to a suspended member."""
        from apps.core.constants import AccountType, MembershipStatus
        from apps.rbac.models import Membership
        from apps.rbac.selectors import RoleSelector
        from apps.rbac.services import RBACService

        # Create a member
        new_member = UserFactory(
            username="susp_transfer", email="susp_transfer@example.com"
        )
        base_role = RoleSelector.get_base_member_role(
            account_type=AccountType.BUSINESS,
            account_id=active_business.id,
        )
        membership = RBACService.create_membership(
            user=new_member,
            account_type=AccountType.BUSINESS,
            account_id=active_business.id,
            role_id=base_role.id,
            created_by=active_business.created_by,
        )

        # Suspend the member directly
        Membership.objects.filter(id=membership.id).update(
            status=MembershipStatus.SUSPENDED
        )

        # Try to transfer ownership
        response = gov_client.post(
            self._transfer_url(active_business),
            {"new_owner_id": str(new_member.id), "reason": "Governance decision"},
            format="json",
        )
        assert response.status_code == 400

    def test_transfer_to_banned_member(self, gov_client, active_business):
        """Cannot transfer ownership to a banned member."""
        from apps.core.constants import AccountType, MembershipStatus
        from apps.rbac.models import Membership
        from apps.rbac.selectors import RoleSelector
        from apps.rbac.services import RBACService

        # Create a member
        new_member = UserFactory(
            username="ban_transfer", email="ban_transfer@example.com"
        )
        base_role = RoleSelector.get_base_member_role(
            account_type=AccountType.BUSINESS,
            account_id=active_business.id,
        )
        membership = RBACService.create_membership(
            user=new_member,
            account_type=AccountType.BUSINESS,
            account_id=active_business.id,
            role_id=base_role.id,
            created_by=active_business.created_by,
        )

        # Ban the member directly
        Membership.objects.filter(id=membership.id).update(
            status=MembershipStatus.BANNED
        )

        # Try to transfer ownership
        response = gov_client.post(
            self._transfer_url(active_business),
            {"new_owner_id": str(new_member.id), "reason": "Governance decision"},
            format="json",
        )
        assert response.status_code == 400


# =============================================================================
# BUSINESS AUDIT LOG TESTS (C5)
# =============================================================================


@pytest.mark.django_db
class TestGovernanceBusinessAudit:
    """
    Verify audit log entries for governance business actions.

    After each action, query AuditLog and check:
    - Correct action enum
    - Correct actor (actor_id == governance user's ID)
    - Details contain reason where applicable
    """

    def _suspend_url(self, business):
        return f"/api/v1/governance/businesses/{business.id}/suspend/"

    def _reactivate_url(self, business):
        return f"/api/v1/governance/businesses/{business.id}/reactivate/"

    def _archive_url(self, business):
        return f"/api/v1/governance/businesses/{business.id}/archive/"

    def test_suspend_creates_audit_entry(
        self, gov_client, global_moderator, active_business
    ):
        """Suspending a business creates BUSINESS_SUSPENDED audit entry."""
        from apps.core.observability.audit.models import AuditLog

        gov_client.post(
            self._suspend_url(active_business),
            {"reason": "Fraudulent activity"},
            format="json",
        )

        entry = AuditLog.objects.filter(
            action=AuditLog.Action.BUSINESS_SUSPENDED,
            resource_id=str(active_business.id),
        ).first()
        assert entry is not None
        assert entry.actor_id == str(global_moderator.id)
        assert "reason" in entry.details
        assert entry.details["reason"] == "Fraudulent activity"

    def test_reactivate_creates_audit_entry(
        self, gov_client, global_moderator, suspended_business
    ):
        """Reactivating a business creates BUSINESS_REACTIVATED audit entry."""
        from apps.core.observability.audit.models import AuditLog

        gov_client.post(self._reactivate_url(suspended_business))

        entry = AuditLog.objects.filter(
            action=AuditLog.Action.BUSINESS_REACTIVATED,
            resource_id=str(suspended_business.id),
        ).first()
        assert entry is not None
        assert entry.actor_id == str(global_moderator.id)

    def test_archive_creates_audit_entry(
        self, gov_client, global_moderator, active_business
    ):
        """Archiving a business creates BUSINESS_ARCHIVED audit entry."""
        from apps.core.observability.audit.models import AuditLog

        gov_client.post(self._archive_url(active_business))

        entry = AuditLog.objects.filter(
            action=AuditLog.Action.BUSINESS_ARCHIVED,
            resource_id=str(active_business.id),
        ).first()
        assert entry is not None
        assert entry.actor_id == str(global_moderator.id)
