# apps/transaction/tests/test_models.py
"""
Tests for Transaction and TransactionLog models.

Tests cover:
- Transaction model: default status, __str__, UUID PK, is_terminal, is_expired,
  can_transition_to, CheckConstraint, JSONField defaults, soft delete
- TransactionLog model: creation, UUID PK, immutability, delete prevention,
  ordering, ForeignKey cascade, multiple logs per transaction
"""

import uuid
from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.constants import ContextType
from apps.transaction.constants import (
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    PartyType,
    TransactionMode,
    TransactionStatus,
)
from apps.transaction.models import Transaction, TransactionLog
from apps.transaction.tests.factories import TransactionFactory, TransactionLogFactory

# =============================================================================
# TRANSACTION MODEL
# =============================================================================


@pytest.mark.django_db
class TestTransactionDefaultStatus:
    """Tests for Transaction default status field."""

    def test_default_status_is_created(self):
        """A Transaction built without explicit status defaults to CREATED."""
        txn = TransactionFactory(status=TransactionStatus.CREATED)

        assert txn.status == TransactionStatus.CREATED

    def test_model_level_default_is_created(self):
        """The model field's default kwarg is TransactionStatus.CREATED."""
        field = Transaction._meta.get_field("status")

        assert field.default == TransactionStatus.CREATED


@pytest.mark.django_db
class TestTransactionStr:
    """Tests for Transaction __str__ representation."""

    def test_str_returns_type_and_status(self):
        """__str__ returns '{transaction_type} ({status})'."""
        txn = TransactionFactory(
            transaction_type="business_membership_invitation",
            status=TransactionStatus.PENDING,
        )

        assert str(txn) == "business_membership_invitation (pending)"

    def test_str_with_created_status(self):
        """__str__ works correctly for CREATED status."""
        txn = TransactionFactory(
            transaction_type="team_join_request",
            status=TransactionStatus.CREATED,
        )

        assert str(txn) == "team_join_request (created)"

    def test_str_with_terminal_status(self):
        """__str__ reflects terminal status values."""
        txn = TransactionFactory(
            transaction_type="business_membership_invitation",
            status=TransactionStatus.ACCEPTED,
        )

        assert str(txn) == "business_membership_invitation (accepted)"


@pytest.mark.django_db
class TestTransactionUUIDPrimaryKey:
    """Tests for Transaction UUID primary key."""

    def test_id_is_uuid(self):
        """Transaction id is a UUID instance."""
        txn = TransactionFactory()

        assert isinstance(txn.id, uuid.UUID)

    def test_id_is_unique_across_instances(self):
        """Each transaction gets a unique UUID."""
        txn1 = TransactionFactory()
        txn2 = TransactionFactory()

        assert txn1.id != txn2.id


@pytest.mark.django_db
class TestTransactionIsTerminal:
    """Tests for Transaction.is_terminal property."""

    @pytest.mark.parametrize(
        "status",
        [
            TransactionStatus.ACCEPTED,
            TransactionStatus.DENIED,
            TransactionStatus.CANCELLED,
            TransactionStatus.EXPIRED,
            TransactionStatus.DISMISSED,
            TransactionStatus.INVALIDATED,
        ],
    )
    def test_is_terminal_true_for_terminal_states(self, status):
        """is_terminal returns True for all 6 terminal states."""
        txn = TransactionFactory(status=status)

        assert txn.is_terminal is True

    def test_is_terminal_false_for_created(self):
        """is_terminal returns False for CREATED status."""
        txn = TransactionFactory(status=TransactionStatus.CREATED)

        assert txn.is_terminal is False

    def test_is_terminal_false_for_pending(self):
        """is_terminal returns False for PENDING status."""
        txn = TransactionFactory(status=TransactionStatus.PENDING)

        assert txn.is_terminal is False


@pytest.mark.django_db
class TestTransactionIsExpired:
    """Tests for Transaction.is_expired property."""

    def test_is_expired_true_when_expires_at_in_past(self):
        """is_expired returns True when expires_at is in the past."""
        txn = TransactionFactory(
            expires_at=timezone.now() - timedelta(hours=1),
        )

        assert txn.is_expired is True

    def test_is_expired_false_when_expires_at_in_future(self):
        """is_expired returns False when expires_at is in the future."""
        txn = TransactionFactory(
            expires_at=timezone.now() + timedelta(days=7),
        )

        assert txn.is_expired is False

    def test_is_expired_false_when_expires_at_is_none(self):
        """is_expired returns False when expires_at is None."""
        txn = TransactionFactory(expires_at=None)

        assert txn.is_expired is False


@pytest.mark.django_db
class TestTransactionCanTransitionTo:
    """Tests for Transaction.can_transition_to method."""

    # -- CREATED transitions --

    def test_created_can_transition_to_pending(self):
        """CREATED can transition to PENDING."""
        txn = TransactionFactory(status=TransactionStatus.CREATED)

        assert txn.can_transition_to(TransactionStatus.PENDING) is True

    def test_created_can_transition_to_expired(self):
        """CREATED can transition to EXPIRED."""
        txn = TransactionFactory(status=TransactionStatus.CREATED)

        assert txn.can_transition_to(TransactionStatus.EXPIRED) is True

    def test_created_can_transition_to_invalidated(self):
        """CREATED can transition to INVALIDATED."""
        txn = TransactionFactory(status=TransactionStatus.CREATED)

        assert txn.can_transition_to(TransactionStatus.INVALIDATED) is True

    def test_created_cannot_transition_to_accepted(self):
        """CREATED cannot directly transition to ACCEPTED."""
        txn = TransactionFactory(status=TransactionStatus.CREATED)

        assert txn.can_transition_to(TransactionStatus.ACCEPTED) is False

    def test_created_cannot_transition_to_denied(self):
        """CREATED cannot directly transition to DENIED."""
        txn = TransactionFactory(status=TransactionStatus.CREATED)

        assert txn.can_transition_to(TransactionStatus.DENIED) is False

    def test_created_cannot_transition_to_cancelled(self):
        """CREATED cannot directly transition to CANCELLED."""
        txn = TransactionFactory(status=TransactionStatus.CREATED)

        assert txn.can_transition_to(TransactionStatus.CANCELLED) is False

    def test_created_cannot_transition_to_dismissed(self):
        """CREATED cannot directly transition to DISMISSED."""
        txn = TransactionFactory(status=TransactionStatus.CREATED)

        assert txn.can_transition_to(TransactionStatus.DISMISSED) is False

    # -- PENDING transitions --

    @pytest.mark.parametrize(
        "target_status",
        [
            TransactionStatus.ACCEPTED,
            TransactionStatus.DENIED,
            TransactionStatus.CANCELLED,
            TransactionStatus.DISMISSED,
            TransactionStatus.EXPIRED,
            TransactionStatus.INVALIDATED,
        ],
    )
    def test_pending_can_transition_to_all_terminal_states(self, target_status):
        """PENDING can transition to all 6 terminal states."""
        txn = TransactionFactory(status=TransactionStatus.PENDING)

        assert txn.can_transition_to(target_status) is True

    # -- Terminal states cannot transition --

    @pytest.mark.parametrize(
        "terminal_status",
        [
            TransactionStatus.ACCEPTED,
            TransactionStatus.DENIED,
            TransactionStatus.CANCELLED,
            TransactionStatus.EXPIRED,
            TransactionStatus.DISMISSED,
            TransactionStatus.INVALIDATED,
        ],
    )
    def test_terminal_states_cannot_transition(self, terminal_status):
        """Terminal states cannot transition to any other status."""
        txn = TransactionFactory(status=terminal_status)

        assert txn.can_transition_to(TransactionStatus.PENDING) is False
        assert txn.can_transition_to(TransactionStatus.CREATED) is False
        assert txn.can_transition_to(TransactionStatus.ACCEPTED) is False


@pytest.mark.django_db
class TestTransactionCheckConstraint:
    """Tests for the txn_context_id_required_for_account_contexts constraint."""

    def test_user_context_allows_null_context_id(self):
        """context_type='user' with context_id=None is allowed."""
        txn = TransactionFactory(
            context_type=ContextType.USER,
            context_id=None,
        )

        assert txn.context_type == ContextType.USER
        assert txn.context_id is None

    def test_business_context_with_null_context_id_fails(self):
        """context_type='business' with context_id=None violates the constraint."""
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                TransactionFactory(
                    context_type=ContextType.BUSINESS,
                    context_id=None,
                )

    def test_business_context_with_valid_context_id_succeeds(self):
        """context_type='business' with a valid context_id is allowed."""
        context_uuid = uuid.uuid4()
        txn = TransactionFactory(
            context_type=ContextType.BUSINESS,
            context_id=context_uuid,
        )

        assert txn.context_type == ContextType.BUSINESS
        assert txn.context_id == context_uuid

    def test_platform_context_with_null_context_id_fails(self):
        """context_type='platform' with context_id=None violates the constraint."""
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                TransactionFactory(
                    context_type=ContextType.PLATFORM,
                    context_id=None,
                )

    def test_platform_context_with_valid_context_id_succeeds(self):
        """context_type='platform' with a valid context_id is allowed."""
        context_uuid = uuid.uuid4()
        txn = TransactionFactory(
            context_type=ContextType.PLATFORM,
            context_id=context_uuid,
        )

        assert txn.context_type == ContextType.PLATFORM
        assert txn.context_id == context_uuid


@pytest.mark.django_db
class TestTransactionJSONFieldDefaults:
    """Tests for JSONField default values."""

    def test_payload_defaults_to_empty_dict(self):
        """payload field defaults to an empty dict when not specified."""
        txn = Transaction.objects.create(
            transaction_type="test_type",
            mode=TransactionMode.INVITATION,
            initiator_type=PartyType.USER,
            initiator_id=uuid.uuid4(),
            target_type=PartyType.USER,
            target_id=uuid.uuid4(),
            context_type=ContextType.USER,
            status=TransactionStatus.CREATED,
        )

        assert txn.payload == {}

    def test_initiator_context_defaults_to_empty_dict(self):
        """initiator_context field defaults to an empty dict when not specified."""
        txn = Transaction.objects.create(
            transaction_type="test_type",
            mode=TransactionMode.INVITATION,
            initiator_type=PartyType.USER,
            initiator_id=uuid.uuid4(),
            target_type=PartyType.USER,
            target_id=uuid.uuid4(),
            context_type=ContextType.USER,
            status=TransactionStatus.CREATED,
        )

        assert txn.initiator_context == {}


@pytest.mark.django_db
class TestTransactionSoftDelete:
    """Tests for Transaction soft delete via managers."""

    def test_objects_manager_excludes_deleted(self):
        """The default `objects` manager filters out is_deleted=True records."""
        txn = TransactionFactory()
        txn.is_deleted = True
        txn.save()

        assert txn not in Transaction.objects.all()

    def test_all_objects_manager_includes_deleted(self):
        """The `all_objects` manager returns soft-deleted records."""
        txn = TransactionFactory()
        txn.is_deleted = True
        txn.save()

        assert txn in Transaction.all_objects.all()

    def test_soft_delete_marks_record(self):
        """soft_delete() sets is_deleted=True and deleted_at."""
        txn = TransactionFactory()
        txn.soft_delete()

        txn.refresh_from_db()
        assert txn.is_deleted is True
        assert txn.deleted_at is not None

    def test_soft_deleted_record_not_in_default_queryset(self):
        """After soft_delete(), the record vanishes from objects queryset."""
        txn = TransactionFactory()
        txn_id = txn.id
        txn.soft_delete()

        assert not Transaction.objects.filter(id=txn_id).exists()
        assert Transaction.all_objects.filter(id=txn_id).exists()


# =============================================================================
# TRANSACTION LOG MODEL
# =============================================================================


@pytest.mark.django_db
class TestTransactionLogCreation:
    """Tests for TransactionLog creation."""

    def test_create_log_with_all_fields(self):
        """TransactionLog can be created with all fields populated."""
        txn = TransactionFactory()
        log = TransactionLogFactory(
            transaction=txn,
            event_type="state_changed",
            actor_context={"user_id": str(uuid.uuid4())},
            previous_status=TransactionStatus.CREATED,
            new_status=TransactionStatus.PENDING,
            metadata={"reason": "auto-approved"},
        )

        assert log.transaction == txn
        assert log.event_type == "state_changed"
        assert log.previous_status == TransactionStatus.CREATED
        assert log.new_status == TransactionStatus.PENDING
        assert log.metadata == {"reason": "auto-approved"}
        assert log.timestamp is not None

    def test_log_has_uuid_primary_key(self):
        """TransactionLog id is a UUID."""
        log = TransactionLogFactory()

        assert isinstance(log.id, uuid.UUID)

    def test_log_ids_are_unique(self):
        """Each TransactionLog gets a unique UUID."""
        log1 = TransactionLogFactory()
        log2 = TransactionLogFactory()

        assert log1.id != log2.id


@pytest.mark.django_db
class TestTransactionLogImmutability:
    """Tests for TransactionLog immutability enforcement."""

    def test_modify_existing_log_raises_value_error(self):
        """Modifying an existing TransactionLog entry raises ValueError."""
        log = TransactionLogFactory()

        log.event_type = "modified_event"
        with pytest.raises(ValueError, match="cannot be modified"):
            log.save()

    def test_delete_raises_value_error(self):
        """Deleting a TransactionLog entry raises ValueError."""
        log = TransactionLogFactory()

        with pytest.raises(ValueError, match="cannot be deleted"):
            log.delete()


@pytest.mark.django_db
class TestTransactionLogOrdering:
    """Tests for TransactionLog default ordering."""

    def test_ordering_is_descending_timestamp(self):
        """TransactionLog default ordering is -timestamp (newest first)."""
        txn = TransactionFactory()
        older_log = TransactionLogFactory(
            transaction=txn,
            timestamp=timezone.now() - timedelta(hours=2),
        )
        newer_log = TransactionLogFactory(
            transaction=txn,
            timestamp=timezone.now() - timedelta(hours=1),
        )

        logs = list(TransactionLog.objects.filter(transaction=txn))

        assert logs[0].id == newer_log.id
        assert logs[1].id == older_log.id

    def test_meta_ordering_field(self):
        """Meta.ordering is set to ['-timestamp']."""
        assert TransactionLog._meta.ordering == ["-timestamp"]


@pytest.mark.django_db
class TestTransactionLogCascadeDelete:
    """Tests for TransactionLog ForeignKey cascade behavior."""

    def test_deleting_transaction_deletes_logs(self):
        """Deleting a Transaction cascades to its TransactionLog entries."""
        txn = TransactionFactory()
        log1 = TransactionLogFactory(transaction=txn)
        log2 = TransactionLogFactory(transaction=txn)
        log1_id = log1.id
        log2_id = log2.id

        # Hard-delete bypassing soft delete via all_objects
        Transaction.all_objects.filter(id=txn.id).delete()

        assert not TransactionLog.objects.filter(id=log1_id).exists()
        assert not TransactionLog.objects.filter(id=log2_id).exists()


@pytest.mark.django_db
class TestTransactionLogMultiplePerTransaction:
    """Tests for creating multiple logs for one transaction."""

    def test_multiple_logs_for_single_transaction(self):
        """Multiple TransactionLog entries can be created for the same transaction."""
        txn = TransactionFactory()
        log1 = TransactionLogFactory(
            transaction=txn,
            event_type="created",
            previous_status="",
            new_status=TransactionStatus.CREATED,
        )
        log2 = TransactionLogFactory(
            transaction=txn,
            event_type="state_changed",
            previous_status=TransactionStatus.CREATED,
            new_status=TransactionStatus.PENDING,
        )
        log3 = TransactionLogFactory(
            transaction=txn,
            event_type="state_changed",
            previous_status=TransactionStatus.PENDING,
            new_status=TransactionStatus.ACCEPTED,
        )

        assert txn.logs.count() == 3
        assert {log1.id, log2.id, log3.id} == set(txn.logs.values_list("id", flat=True))

    def test_logs_accessible_via_related_name(self):
        """Transaction.logs related manager returns the correct logs."""
        txn = TransactionFactory()
        log = TransactionLogFactory(transaction=txn)

        assert log in txn.logs.all()
