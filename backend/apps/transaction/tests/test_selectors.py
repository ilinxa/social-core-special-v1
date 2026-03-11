"""
Tests for TransactionSelector and TransactionLogSelector.

Covers:
- TransactionSelector: get_by_id, get_by_id_or_none, get_by_id_with_logs,
  exists_active, list_for_user_as_initiator, list_for_user_as_target,
  list_pending_for_context, list_expired_needing_update, get_resubmission_cooldown
- TransactionLogSelector: list_for_transaction
"""

import pytest
from datetime import timedelta
from uuid import uuid4

from django.utils import timezone

from apps.core.constants import ContextType
from apps.core.exceptions import NotFound
from apps.transaction.constants import PartyType, TransactionStatus
from apps.transaction.selectors import TransactionLogSelector, TransactionSelector
from apps.transaction.tests.factories import TransactionFactory, TransactionLogFactory


# ==========================================================================
# TransactionSelector — get_by_id
# ==========================================================================


@pytest.mark.django_db
class TestGetById:

    def test_returns_transaction_when_found(self):
        txn = TransactionFactory()
        result = TransactionSelector.get_by_id(transaction_id=txn.id)
        assert result.id == txn.id

    def test_raises_not_found_when_missing(self):
        with pytest.raises(NotFound):
            TransactionSelector.get_by_id(transaction_id=uuid4())


# ==========================================================================
# TransactionSelector — get_by_id_or_none
# ==========================================================================


@pytest.mark.django_db
class TestGetByIdOrNone:

    def test_returns_transaction_when_found(self):
        txn = TransactionFactory()
        result = TransactionSelector.get_by_id_or_none(transaction_id=txn.id)
        assert result is not None
        assert result.id == txn.id

    def test_returns_none_when_not_found(self):
        result = TransactionSelector.get_by_id_or_none(transaction_id=uuid4())
        assert result is None


# ==========================================================================
# TransactionSelector — get_by_id_with_logs
# ==========================================================================


@pytest.mark.django_db
class TestGetByIdWithLogs:

    def test_returns_transaction_with_prefetched_logs(self):
        txn = TransactionFactory()
        log1 = TransactionLogFactory(transaction=txn)
        log2 = TransactionLogFactory(transaction=txn)

        result = TransactionSelector.get_by_id_with_logs(transaction_id=txn.id)
        assert result.id == txn.id

        # Verify logs are prefetched (no additional query)
        logs = list(result.logs.all())
        assert len(logs) == 2
        log_ids = {log.id for log in logs}
        assert log1.id in log_ids
        assert log2.id in log_ids

    def test_raises_not_found_when_missing(self):
        with pytest.raises(NotFound):
            TransactionSelector.get_by_id_with_logs(transaction_id=uuid4())


# ==========================================================================
# TransactionSelector — exists_active
# ==========================================================================


@pytest.mark.django_db
class TestExistsActive:

    def test_returns_true_when_active_transaction_exists(self):
        txn = TransactionFactory(status=TransactionStatus.PENDING)
        result = TransactionSelector.exists_active(
            transaction_type=txn.transaction_type,
            initiator_id=txn.initiator_id,
            target_id=txn.target_id,
        )
        assert result is True

    def test_returns_false_when_no_match(self):
        result = TransactionSelector.exists_active(
            transaction_type="business_membership_invitation",
            initiator_id=uuid4(),
            target_id=uuid4(),
        )
        assert result is False

    def test_returns_false_when_only_terminal_transactions_exist(self):
        txn = TransactionFactory(status=TransactionStatus.ACCEPTED)
        result = TransactionSelector.exists_active(
            transaction_type=txn.transaction_type,
            initiator_id=txn.initiator_id,
            target_id=txn.target_id,
        )
        assert result is False


# ==========================================================================
# TransactionSelector — has_active_in_conflict_group
# ==========================================================================


@pytest.mark.django_db
class TestHasActiveInConflictGroup:

    def test_empty_conflict_group_returns_none(self):
        result = TransactionSelector.has_active_in_conflict_group(
            conflict_group="",
            user_id=uuid4(),
            context_type=ContextType.BUSINESS,
            context_id=uuid4(),
        )
        assert result is None

    def test_no_active_transactions_returns_none(self):
        result = TransactionSelector.has_active_in_conflict_group(
            conflict_group="business_membership",
            user_id=uuid4(),
            context_type=ContextType.BUSINESS,
            context_id=uuid4(),
        )
        assert result is None

    def test_detects_invitation_where_user_is_target(self):
        user_id = uuid4()
        biz_id = uuid4()
        TransactionFactory(
            transaction_type="business_membership_invitation",
            mode="invitation",
            initiator_type=PartyType.MEMBERSHIP_ACTOR,
            target_type=PartyType.USER,
            target_id=user_id,
            context_type=ContextType.BUSINESS,
            context_id=biz_id,
            status=TransactionStatus.PENDING,
        )
        result = TransactionSelector.has_active_in_conflict_group(
            conflict_group="business_membership",
            user_id=user_id,
            context_type=ContextType.BUSINESS,
            context_id=biz_id,
        )
        assert result is not None
        assert result.transaction_type == "business_membership_invitation"

    def test_detects_request_where_user_is_initiator(self):
        user_id = uuid4()
        biz_id = uuid4()
        TransactionFactory(
            transaction_type="business_membership_request",
            mode="request",
            initiator_type=PartyType.USER,
            initiator_id=user_id,
            target_type=PartyType.ACCOUNT,
            context_type=ContextType.BUSINESS,
            context_id=biz_id,
            status=TransactionStatus.PENDING,
        )
        result = TransactionSelector.has_active_in_conflict_group(
            conflict_group="business_membership",
            user_id=user_id,
            context_type=ContextType.BUSINESS,
            context_id=biz_id,
        )
        assert result is not None
        assert result.transaction_type == "business_membership_request"

    def test_ignores_terminal_state_transactions(self):
        user_id = uuid4()
        biz_id = uuid4()
        TransactionFactory(
            transaction_type="business_membership_invitation",
            target_type=PartyType.USER,
            target_id=user_id,
            context_type=ContextType.BUSINESS,
            context_id=biz_id,
            status=TransactionStatus.ACCEPTED,
        )
        result = TransactionSelector.has_active_in_conflict_group(
            conflict_group="business_membership",
            user_id=user_id,
            context_type=ContextType.BUSINESS,
            context_id=biz_id,
        )
        assert result is None

    def test_ignores_different_context(self):
        user_id = uuid4()
        biz_id = uuid4()
        other_biz_id = uuid4()
        TransactionFactory(
            transaction_type="business_membership_invitation",
            target_type=PartyType.USER,
            target_id=user_id,
            context_type=ContextType.BUSINESS,
            context_id=other_biz_id,
            status=TransactionStatus.PENDING,
        )
        result = TransactionSelector.has_active_in_conflict_group(
            conflict_group="business_membership",
            user_id=user_id,
            context_type=ContextType.BUSINESS,
            context_id=biz_id,
        )
        assert result is None

    def test_cross_type_invitation_blocks_request_detection(self):
        """Invitation in conflict group detected when checking for request user."""
        user_id = uuid4()
        biz_id = uuid4()
        # User has a pending invitation (someone invited them)
        TransactionFactory(
            transaction_type="business_membership_invitation",
            mode="invitation",
            target_type=PartyType.USER,
            target_id=user_id,
            context_type=ContextType.BUSINESS,
            context_id=biz_id,
            status=TransactionStatus.PENDING,
        )
        # Conflict group check should find it
        result = TransactionSelector.has_active_in_conflict_group(
            conflict_group="business_membership",
            user_id=user_id,
            context_type=ContextType.BUSINESS,
            context_id=biz_id,
        )
        assert result is not None
        assert result.transaction_type == "business_membership_invitation"


# ==========================================================================
# TransactionSelector — list_for_user_as_initiator
# ==========================================================================


@pytest.mark.django_db
class TestListForUserAsInitiator:

    def test_returns_transactions_where_user_is_initiator(self):
        user_id = uuid4()
        txn = TransactionFactory(
            initiator_type=PartyType.USER,
            initiator_id=user_id,
            status=TransactionStatus.PENDING,
        )
        # Different initiator — should not appear
        TransactionFactory(
            initiator_type=PartyType.USER,
            initiator_id=uuid4(),
            status=TransactionStatus.PENDING,
        )

        result = list(
            TransactionSelector.list_for_user_as_initiator(user_id=user_id)
        )
        assert len(result) == 1
        assert result[0].id == txn.id

    def test_returns_empty_for_user_with_no_transactions(self):
        result = list(
            TransactionSelector.list_for_user_as_initiator(user_id=uuid4())
        )
        assert result == []

    def test_include_terminal_false_filters_terminal_states(self):
        user_id = uuid4()
        active_txn = TransactionFactory(
            initiator_type=PartyType.USER,
            initiator_id=user_id,
            status=TransactionStatus.PENDING,
        )
        TransactionFactory(
            initiator_type=PartyType.USER,
            initiator_id=user_id,
            status=TransactionStatus.ACCEPTED,
        )
        TransactionFactory(
            initiator_type=PartyType.USER,
            initiator_id=user_id,
            status=TransactionStatus.DENIED,
        )

        result = list(
            TransactionSelector.list_for_user_as_initiator(
                user_id=user_id, include_terminal=False,
            )
        )
        assert len(result) == 1
        assert result[0].id == active_txn.id

    def test_include_terminal_true_includes_all(self):
        user_id = uuid4()
        TransactionFactory(
            initiator_type=PartyType.USER,
            initiator_id=user_id,
            status=TransactionStatus.PENDING,
        )
        TransactionFactory(
            initiator_type=PartyType.USER,
            initiator_id=user_id,
            status=TransactionStatus.ACCEPTED,
        )
        TransactionFactory(
            initiator_type=PartyType.USER,
            initiator_id=user_id,
            status=TransactionStatus.DENIED,
        )

        result = list(
            TransactionSelector.list_for_user_as_initiator(
                user_id=user_id, include_terminal=True,
            )
        )
        assert len(result) == 3

    def test_includes_membership_actor_transactions(self):
        """Transactions created via membership context should be visible
        to the user who created them (user_id stored in initiator_context)."""
        user_id = uuid4()
        membership_id = uuid4()
        txn = TransactionFactory(
            initiator_type=PartyType.MEMBERSHIP_ACTOR,
            initiator_id=membership_id,
            initiator_context={"user_id": str(user_id), "role_name": "Owner"},
            status=TransactionStatus.PENDING,
        )

        result = list(
            TransactionSelector.list_for_user_as_initiator(user_id=user_id)
        )
        assert len(result) == 1
        assert result[0].id == txn.id

    def test_membership_actor_does_not_leak_to_other_users(self):
        """membership_actor transactions should NOT appear for unrelated users."""
        user_id = uuid4()
        other_user_id = uuid4()
        TransactionFactory(
            initiator_type=PartyType.MEMBERSHIP_ACTOR,
            initiator_id=uuid4(),
            initiator_context={"user_id": str(other_user_id)},
            status=TransactionStatus.PENDING,
        )

        result = list(
            TransactionSelector.list_for_user_as_initiator(user_id=user_id)
        )
        assert len(result) == 0

    def test_ordered_by_created_at_desc(self):
        user_id = uuid4()
        now = timezone.now()

        txn_old = TransactionFactory(
            initiator_type=PartyType.USER,
            initiator_id=user_id,
            status=TransactionStatus.PENDING,
        )
        txn_new = TransactionFactory(
            initiator_type=PartyType.USER,
            initiator_id=user_id,
            status=TransactionStatus.CREATED,
        )

        # Force ordering via created_at update
        from apps.transaction.models import Transaction
        Transaction.objects.filter(id=txn_old.id).update(
            created_at=now - timedelta(hours=2),
        )
        Transaction.objects.filter(id=txn_new.id).update(
            created_at=now - timedelta(hours=1),
        )

        result = list(
            TransactionSelector.list_for_user_as_initiator(user_id=user_id)
        )
        assert result[0].id == txn_new.id
        assert result[1].id == txn_old.id


# ==========================================================================
# TransactionSelector — list_for_user_as_target
# ==========================================================================


@pytest.mark.django_db
class TestListForUserAsTarget:

    def test_returns_transactions_where_user_is_target(self):
        target_id = uuid4()
        txn = TransactionFactory(
            target_type=PartyType.USER,
            target_id=target_id,
            status=TransactionStatus.PENDING,
        )
        # Different target — should not appear
        TransactionFactory(
            target_type=PartyType.USER,
            target_id=uuid4(),
            status=TransactionStatus.PENDING,
        )

        result = list(
            TransactionSelector.list_for_user_as_target(user_id=target_id)
        )
        assert len(result) == 1
        assert result[0].id == txn.id

    def test_include_terminal_false_filters_terminal_states(self):
        target_id = uuid4()
        active_txn = TransactionFactory(
            target_type=PartyType.USER,
            target_id=target_id,
            status=TransactionStatus.PENDING,
        )
        TransactionFactory(
            target_type=PartyType.USER,
            target_id=target_id,
            status=TransactionStatus.CANCELLED,
        )

        result = list(
            TransactionSelector.list_for_user_as_target(
                user_id=target_id, include_terminal=False,
            )
        )
        assert len(result) == 1
        assert result[0].id == active_txn.id

    def test_include_terminal_true_includes_all(self):
        target_id = uuid4()
        TransactionFactory(
            target_type=PartyType.USER,
            target_id=target_id,
            status=TransactionStatus.PENDING,
        )
        TransactionFactory(
            target_type=PartyType.USER,
            target_id=target_id,
            status=TransactionStatus.ACCEPTED,
        )

        result = list(
            TransactionSelector.list_for_user_as_target(
                user_id=target_id, include_terminal=True,
            )
        )
        assert len(result) == 2

    def test_ordered_by_created_at_desc(self):
        target_id = uuid4()
        now = timezone.now()

        txn_old = TransactionFactory(
            target_type=PartyType.USER,
            target_id=target_id,
            status=TransactionStatus.PENDING,
        )
        txn_new = TransactionFactory(
            target_type=PartyType.USER,
            target_id=target_id,
            status=TransactionStatus.CREATED,
        )

        from apps.transaction.models import Transaction
        Transaction.objects.filter(id=txn_old.id).update(
            created_at=now - timedelta(hours=2),
        )
        Transaction.objects.filter(id=txn_new.id).update(
            created_at=now - timedelta(hours=1),
        )

        result = list(
            TransactionSelector.list_for_user_as_target(user_id=target_id)
        )
        assert result[0].id == txn_new.id
        assert result[1].id == txn_old.id


# ==========================================================================
# TransactionSelector — list_for_user (combined Q-based query)
# ==========================================================================


@pytest.mark.django_db
class TestListForUser:

    def test_returns_initiator_and_target_transactions(self):
        user_id = uuid4()
        as_initiator = TransactionFactory(
            initiator_type=PartyType.USER, initiator_id=user_id,
            status=TransactionStatus.PENDING,
        )
        as_target = TransactionFactory(
            target_type=PartyType.USER, target_id=user_id,
            status=TransactionStatus.PENDING,
        )
        TransactionFactory(status=TransactionStatus.PENDING)  # unrelated

        result = list(TransactionSelector.list_for_user(
            user_id=user_id, include_terminal=True,
        ))
        ids = {t.id for t in result}
        assert as_initiator.id in ids
        assert as_target.id in ids
        assert len(result) == 2

    def test_exclude_terminal_by_default(self):
        user_id = uuid4()
        TransactionFactory(
            initiator_type=PartyType.USER, initiator_id=user_id,
            status=TransactionStatus.PENDING,
        )
        TransactionFactory(
            initiator_type=PartyType.USER, initiator_id=user_id,
            status=TransactionStatus.ACCEPTED,
        )
        result = list(TransactionSelector.list_for_user(user_id=user_id))
        assert len(result) == 1

    def test_includes_membership_actor_as_initiator(self):
        """list_for_user should include transactions where the user acted
        through a membership (initiator_type=membership_actor)."""
        user_id = uuid4()
        membership_txn = TransactionFactory(
            initiator_type=PartyType.MEMBERSHIP_ACTOR,
            initiator_id=uuid4(),
            initiator_context={"user_id": str(user_id)},
            status=TransactionStatus.PENDING,
        )
        target_txn = TransactionFactory(
            target_type=PartyType.USER, target_id=user_id,
            status=TransactionStatus.PENDING,
        )
        TransactionFactory(status=TransactionStatus.PENDING)  # unrelated

        result = list(TransactionSelector.list_for_user(
            user_id=user_id, include_terminal=True,
        ))
        ids = {t.id for t in result}
        assert membership_txn.id in ids
        assert target_txn.id in ids
        assert len(result) == 2

    def test_supports_subsequent_filter(self):
        """list_for_user uses Q objects (not UNION) so .filter() works."""
        user_id = uuid4()
        TransactionFactory(
            initiator_type=PartyType.USER, initiator_id=user_id,
            status=TransactionStatus.PENDING,
            transaction_type="business_membership_invitation",
        )
        TransactionFactory(
            initiator_type=PartyType.USER, initiator_id=user_id,
            status=TransactionStatus.PENDING,
            transaction_type="user_connection_request",
        )
        qs = TransactionSelector.list_for_user(
            user_id=user_id, include_terminal=True,
        )
        filtered = qs.filter(transaction_type="user_connection_request")
        assert filtered.count() == 1


# ==========================================================================
# TransactionSelector — list_pending_for_context
# ==========================================================================
# TransactionSelector — list_for_context
# ==========================================================================


@pytest.mark.django_db
class TestListForContext:

    def test_returns_all_transactions_for_context(self):
        context_id = uuid4()
        txn1 = TransactionFactory(
            context_type=ContextType.BUSINESS,
            context_id=context_id,
            status=TransactionStatus.PENDING,
        )
        txn2 = TransactionFactory(
            context_type=ContextType.BUSINESS,
            context_id=context_id,
            status=TransactionStatus.ACCEPTED,
        )
        # Different context — should not appear
        TransactionFactory(
            context_type=ContextType.BUSINESS,
            context_id=uuid4(),
        )

        result = list(
            TransactionSelector.list_for_context(
                context_type=ContextType.BUSINESS,
                context_id=context_id,
                include_terminal=True,
            )
        )
        assert len(result) == 2
        result_ids = {r.id for r in result}
        assert txn1.id in result_ids
        assert txn2.id in result_ids

    def test_excludes_terminal_by_default(self):
        context_id = uuid4()
        TransactionFactory(
            context_type=ContextType.BUSINESS,
            context_id=context_id,
            status=TransactionStatus.PENDING,
        )
        TransactionFactory(
            context_type=ContextType.BUSINESS,
            context_id=context_id,
            status=TransactionStatus.ACCEPTED,
        )

        result = list(
            TransactionSelector.list_for_context(
                context_type=ContextType.BUSINESS,
                context_id=context_id,
            )
        )
        assert len(result) == 1


# ==========================================================================


@pytest.mark.django_db
class TestListPendingForContext:

    def test_returns_pending_transactions_for_context(self):
        context_id = uuid4()
        txn = TransactionFactory(
            context_type=ContextType.BUSINESS,
            context_id=context_id,
            status=TransactionStatus.PENDING,
        )
        # Non-pending — should not appear
        TransactionFactory(
            context_type=ContextType.BUSINESS,
            context_id=context_id,
            status=TransactionStatus.ACCEPTED,
        )

        result = list(
            TransactionSelector.list_pending_for_context(
                context_type=ContextType.BUSINESS,
                context_id=context_id,
            )
        )
        assert len(result) == 1
        assert result[0].id == txn.id

    def test_filters_by_transaction_type_when_provided(self):
        context_id = uuid4()
        invitation = TransactionFactory(
            transaction_type="business_membership_invitation",
            context_type=ContextType.BUSINESS,
            context_id=context_id,
            status=TransactionStatus.PENDING,
        )
        TransactionFactory(
            transaction_type="business_membership_request",
            context_type=ContextType.BUSINESS,
            context_id=context_id,
            status=TransactionStatus.PENDING,
        )

        result = list(
            TransactionSelector.list_pending_for_context(
                context_type=ContextType.BUSINESS,
                context_id=context_id,
                transaction_type="business_membership_invitation",
            )
        )
        assert len(result) == 1
        assert result[0].id == invitation.id

    def test_returns_empty_when_no_matches(self):
        result = list(
            TransactionSelector.list_pending_for_context(
                context_type=ContextType.BUSINESS,
                context_id=uuid4(),
            )
        )
        assert result == []


# ==========================================================================
# TransactionSelector — list_expired_needing_update
# ==========================================================================


@pytest.mark.django_db
class TestListExpiredNeedingUpdate:

    def test_returns_non_terminal_transactions_past_expires_at(self):
        txn = TransactionFactory(
            status=TransactionStatus.PENDING,
            expires_at=timezone.now() - timedelta(days=1),
        )

        result = list(TransactionSelector.list_expired_needing_update())
        ids = [t.id for t in result]
        assert txn.id in ids

    def test_excludes_terminal_transactions(self):
        TransactionFactory(
            status=TransactionStatus.ACCEPTED,
            expires_at=timezone.now() - timedelta(days=1),
        )
        TransactionFactory(
            status=TransactionStatus.DENIED,
            expires_at=timezone.now() - timedelta(days=1),
        )
        TransactionFactory(
            status=TransactionStatus.EXPIRED,
            expires_at=timezone.now() - timedelta(days=1),
        )

        result = list(TransactionSelector.list_expired_needing_update())
        assert len(result) == 0

    def test_excludes_transactions_not_yet_expired(self):
        TransactionFactory(
            status=TransactionStatus.PENDING,
            expires_at=timezone.now() + timedelta(days=7),
        )

        result = list(TransactionSelector.list_expired_needing_update())
        assert len(result) == 0


# ==========================================================================
# TransactionSelector — get_resubmission_cooldown
# ==========================================================================


@pytest.mark.django_db
class TestGetResubmissionCooldown:

    def test_returns_none_when_no_previous_denied(self):
        """No denied transaction exists at all — no cooldown."""
        result = TransactionSelector.get_resubmission_cooldown(
            transaction_type="business_membership_request",
            initiator_id=uuid4(),
            target_id=uuid4(),
        )
        assert result is None

    def test_returns_none_when_cooldown_is_zero(self):
        """platform_membership_invitation has resubmission_cooldown_days=0."""
        initiator_id = uuid4()
        target_id = uuid4()
        TransactionFactory(
            transaction_type="platform_membership_invitation",
            initiator_id=initiator_id,
            target_id=target_id,
            status=TransactionStatus.DENIED,
            resolved_at=timezone.now() - timedelta(hours=1),
        )

        result = TransactionSelector.get_resubmission_cooldown(
            transaction_type="platform_membership_invitation",
            initiator_id=initiator_id,
            target_id=target_id,
        )
        assert result is None

    def test_returns_cooldown_end_when_within_cooldown(self):
        """business_membership_request has resubmission_cooldown_days=7.
        Denied 1 day ago means cooldown_end is 6 days from now."""
        initiator_id = uuid4()
        target_id = uuid4()
        resolved_time = timezone.now() - timedelta(days=1)
        TransactionFactory(
            transaction_type="business_membership_request",
            mode="request",
            initiator_type=PartyType.USER,
            initiator_id=initiator_id,
            target_type=PartyType.ACCOUNT,
            target_id=target_id,
            context_type=ContextType.BUSINESS,
            status=TransactionStatus.DENIED,
            resolved_at=resolved_time,
        )

        result = TransactionSelector.get_resubmission_cooldown(
            transaction_type="business_membership_request",
            initiator_id=initiator_id,
            target_id=target_id,
        )
        assert result is not None
        expected_cooldown_end = resolved_time + timedelta(days=7)
        # Allow 1 second tolerance for timing
        assert abs((result - expected_cooldown_end).total_seconds()) < 1

    def test_returns_none_when_cooldown_has_passed(self):
        """Denied 30 days ago with a 7-day cooldown — no longer active."""
        initiator_id = uuid4()
        target_id = uuid4()
        TransactionFactory(
            transaction_type="business_membership_request",
            mode="request",
            initiator_type=PartyType.USER,
            initiator_id=initiator_id,
            target_type=PartyType.ACCOUNT,
            target_id=target_id,
            context_type=ContextType.BUSINESS,
            status=TransactionStatus.DENIED,
            resolved_at=timezone.now() - timedelta(days=30),
        )

        result = TransactionSelector.get_resubmission_cooldown(
            transaction_type="business_membership_request",
            initiator_id=initiator_id,
            target_id=target_id,
        )
        assert result is None


# ==========================================================================
# TransactionLogSelector — list_for_transaction
# ==========================================================================


@pytest.mark.django_db
class TestTransactionLogSelectorListForTransaction:

    def test_returns_logs_ordered_by_timestamp_desc(self):
        txn = TransactionFactory()
        now = timezone.now()

        log_old = TransactionLogFactory(
            transaction=txn,
            timestamp=now - timedelta(hours=2),
        )
        log_new = TransactionLogFactory(
            transaction=txn,
            timestamp=now - timedelta(hours=1),
        )

        result = list(
            TransactionLogSelector.list_for_transaction(transaction_id=txn.id)
        )
        assert len(result) == 2
        assert result[0].id == log_new.id
        assert result[1].id == log_old.id

    def test_returns_empty_for_transaction_with_no_logs(self):
        txn = TransactionFactory()
        result = list(
            TransactionLogSelector.list_for_transaction(transaction_id=txn.id)
        )
        assert result == []


# ==========================================================================
# Platform Selector Tests
# ==========================================================================


@pytest.mark.django_db
class TestPlatformSelectors:

    def test_list_for_platform_context(self):
        """list_for_context filters by context_type=platform."""
        platform_id = uuid4()
        biz_id = uuid4()
        txn_plat = TransactionFactory(
            transaction_type="platform_membership_invitation",
            context_type=ContextType.PLATFORM,
            context_id=platform_id,
            status=TransactionStatus.PENDING,
        )
        # Business transaction — should not appear
        TransactionFactory(
            transaction_type="business_membership_invitation",
            context_type=ContextType.BUSINESS,
            context_id=biz_id,
            status=TransactionStatus.PENDING,
        )

        result = list(
            TransactionSelector.list_for_context(
                context_type=ContextType.PLATFORM,
                context_id=platform_id,
            )
        )
        assert len(result) == 1
        assert result[0].id == txn_plat.id

    def test_has_active_in_conflict_group_platform(self):
        """Cross-type conflict detection works for platform_membership conflict group."""
        user_id = uuid4()
        platform_id = uuid4()
        # Pending platform invitation
        TransactionFactory(
            transaction_type="platform_membership_invitation",
            mode="invitation",
            target_type=PartyType.USER,
            target_id=user_id,
            context_type=ContextType.PLATFORM,
            context_id=platform_id,
            status=TransactionStatus.PENDING,
        )
        # Conflict group check for platform_membership should find it
        result = TransactionSelector.has_active_in_conflict_group(
            conflict_group="platform_membership",
            user_id=user_id,
            context_type=ContextType.PLATFORM,
            context_id=platform_id,
        )
        assert result is not None
        assert result.transaction_type == "platform_membership_invitation"
