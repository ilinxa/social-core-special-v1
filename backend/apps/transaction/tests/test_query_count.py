# apps/transaction/tests/test_query_count.py
"""
Query count regression tests for transaction list views.

Ensures batch-loading prevents N+1 queries after performance fixes.
"""

import pytest
from django.conf import settings

from apps.transaction.constants import PartyType
from apps.transaction.tests.factories import TransactionFactory
from apps.users.tests.factories import UserFactory

requires_postgres = pytest.mark.skipif(
    "sqlite" in settings.DATABASES["default"]["ENGINE"],
    reason="Query count tests require PostgreSQL",
)

pytestmark = [pytest.mark.django_db, requires_postgres]


class TestTransactionListQueryCount:
    """Transaction list endpoint should use constant queries regardless of page size."""

    def test_list_query_count_is_constant(
        self,
        authenticated_client,
        user,
        transaction_list_url,
        django_assert_max_num_queries,
    ):
        """20 transactions should NOT produce 20*N extra queries."""
        other_users = UserFactory.create_batch(5)
        for i, other in enumerate(other_users):
            # User as initiator
            TransactionFactory(
                initiator_type=PartyType.USER,
                initiator_id=user.id,
                target_type=PartyType.USER,
                target_id=other.id,
            )
            # User as target
            TransactionFactory(
                initiator_type=PartyType.USER,
                initiator_id=other.id,
                target_type=PartyType.USER,
                target_id=user.id,
            )

        # With batch loading: auth (~2) + queryset (~2) + batch users (~1) + pagination (~1)
        # Without batch loading this would be 10+ queries per item
        with django_assert_max_num_queries(15):
            response = authenticated_client.get(transaction_list_url)
            assert response.status_code == 200
            assert response.data["count"] == 10
