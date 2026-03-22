# apps/network/tests/test_query_count.py
"""
Query count regression tests for network list views.

Ensures batch-loading prevents N+1 queries after performance fixes.
"""

import pytest
from django.conf import settings

from apps.network.tests.factories import FollowFactory
from apps.users.tests.factories import UserFactory

requires_postgres = pytest.mark.skipif(
    "sqlite" in settings.DATABASES["default"]["ENGINE"],
    reason="Query count tests require PostgreSQL",
)

pytestmark = [pytest.mark.django_db, requires_postgres]


class TestFollowingListQueryCount:
    """Following list endpoint should use constant queries regardless of page size."""

    def test_following_query_count_is_constant(
        self,
        authenticated_client,
        user,
        business,
        django_assert_max_num_queries,
    ):
        """10 follows should NOT produce 10*N extra queries."""
        from apps.core.constants import BusinessStatus
        from apps.organization.tests.factories import (
            BusinessAccountFactory,
            BusinessProfileFactory,
        )
        from apps.rbac.services import RBACService

        # Create 10 follows to different businesses
        for _ in range(10):
            biz = BusinessAccountFactory(status=BusinessStatus.ACTIVE)
            BusinessProfileFactory(business=biz, is_public=True)
            RBACService.initialize_business_account(
                business_id=biz.id, owner=biz.created_by
            )
            FollowFactory(
                follower=user,
                followee_type="business",
                followee_id=biz.id,
            )

        # With batch loading: auth (~2) + queryset (~2) + batch accounts (~1) + pagination (~1)
        with django_assert_max_num_queries(15):
            response = authenticated_client.get("/api/v1/network/following/")
            assert response.status_code == 200
            assert response.data["count"] == 10
