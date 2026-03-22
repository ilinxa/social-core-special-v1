# apps/rbac/tests/test_query_count.py
"""
Query count regression tests for RBAC membership views.

Ensures batch-loading prevents N+1 queries after performance fixes.
"""

import pytest
from django.conf import settings

from apps.core.constants import AccountType, MembershipStatus
from apps.rbac.tests.factories import (
    BaseMemberRoleFactory,
    BusinessAccountFactory,
    MembershipFactory,
    OwnerRoleFactory,
)
from apps.users.tests.factories import UserFactory

requires_postgres = pytest.mark.skipif(
    "sqlite" in settings.DATABASES["default"]["ENGINE"],
    reason="Query count tests require PostgreSQL",
)

pytestmark = [pytest.mark.django_db, requires_postgres]


class TestMyMembershipsQueryCount:
    """My memberships endpoint should use constant queries regardless of membership count."""

    def test_memberships_query_count_is_constant(
        self,
        api_client,
        django_assert_max_num_queries,
    ):
        """5 memberships should NOT produce 5*3 extra queries."""
        user = UserFactory()
        api_client.force_authenticate(user=user)

        # Create 5 business memberships for the user
        for _ in range(5):
            biz = BusinessAccountFactory()
            role = BaseMemberRoleFactory(
                account_type=AccountType.BUSINESS,
                account_id=biz.id,
            )
            MembershipFactory(
                user=user,
                account_type=AccountType.BUSINESS,
                account_id=biz.id,
                role=role,
                status=MembershipStatus.ACTIVE,
            )

        # With batch loading: auth (~2) + memberships (~1) + batch accounts (~2) + permissions (~5 Redis)
        # Redis permission lookups are NOT counted by assertNumQueries
        with django_assert_max_num_queries(15):
            response = api_client.get("/api/v1/users/me/memberships/")
            assert response.status_code == 200
            assert len(response.data) == 5
