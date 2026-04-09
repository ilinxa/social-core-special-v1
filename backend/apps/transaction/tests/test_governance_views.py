# apps/transaction/tests/test_governance_views.py
"""
Tests for governance console transaction endpoints.

Test matrix:
- Global Moderator with governance token → 200
- Regular user → 403
- Unauthenticated → 401
- Filters: status, mode, transaction_type
"""

import pytest
from rest_framework.test import APIClient

from apps.organization.tests.factories import PlatformAccountFactory, UserFactory

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
def global_moderator(db, platform_account):
    """Create a Global Moderator with governance token auth."""
    from apps.rbac.models import Role
    from apps.rbac.services import RBACService

    _ensure_platform_rbac(platform_account)

    user = UserFactory(username="gov_mod_t", email="gov_mod_t@example.com")
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
def regular_user(db):
    """Regular user without any special permissions."""
    return UserFactory(username="regular_t", email="regular_t@example.com")


@pytest.fixture
def regular_client(regular_user):
    """APIClient authenticated as regular user (no governance token)."""
    client = APIClient()
    client.force_authenticate(user=regular_user)
    return client


# =============================================================================
# TRANSACTION LIST VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestGovernanceTransactionListView:
    """Tests for GET /api/v1/governance/transactions/"""

    URL = "/api/v1/governance/transactions/"

    def test_global_moderator_can_list(self, gov_client):
        response = gov_client.get(self.URL)
        assert response.status_code == 200
        assert "results" in response.data

    def test_empty_results(self, gov_client):
        response = gov_client.get(self.URL)
        assert response.status_code == 200
        assert response.data["results"] == []

    def test_filter_by_status(self, gov_client):
        response = gov_client.get(self.URL, {"status": "pending"})
        assert response.status_code == 200

    def test_filter_by_mode(self, gov_client):
        response = gov_client.get(self.URL, {"mode": "invitation"})
        assert response.status_code == 200

    def test_filter_by_context_type(self, gov_client):
        response = gov_client.get(self.URL, {"context_type": "business"})
        assert response.status_code == 200

    def test_regular_user_forbidden(self, regular_client):
        response = regular_client.get(self.URL)
        assert response.status_code == 403

    def test_unauthenticated(self):
        client = APIClient()
        response = client.get(self.URL)
        assert response.status_code == 401
