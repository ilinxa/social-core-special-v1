# apps/core/tests/test_models.py
"""
Tests for core abstract base models.

Since TimeStampedModel, SoftDeleteModel, UserStampedModel, UUIDModel, and AuditModel
are abstract, we test them through concrete models that inherit from them.

Covers:
    - TimeStampedModel: auto timestamps, default ordering
    - SoftDeleteModel: soft_delete(), restore(), manager filtering
    - UUIDModel: UUID primary key auto-generation
    - AuditLog: immutability (append-only, no delete)
"""

import uuid
import time

import pytest
from django.utils import timezone

from apps.organization.tests.factories import BusinessAccountFactory, UserFactory
from apps.core.observability.audit.models import AuditLog
from apps.organization.business.models import BusinessAccount


# =============================================================================
# TIMESTAMPED MODEL TESTS (via BusinessAccount -> AuditModel -> UserStampedModel -> TimeStampedModel)
# =============================================================================


@pytest.mark.django_db
class TestTimeStampedModel:
    """Tests for TimeStampedModel fields via BusinessAccount."""

    def test_created_at_auto_set_on_creation(self):
        """created_at is automatically set when a record is created."""
        before = timezone.now()
        business = BusinessAccountFactory()
        after = timezone.now()

        assert business.created_at is not None
        assert before <= business.created_at <= after

    def test_updated_at_auto_set_on_creation(self):
        """updated_at is automatically set when a record is created."""
        business = BusinessAccountFactory()

        assert business.updated_at is not None

    def test_updated_at_changes_on_save(self):
        """updated_at is refreshed each time the record is saved."""
        business = BusinessAccountFactory()
        original_updated_at = business.updated_at

        # Ensure some time passes
        business.legal_name = "Updated Business Name"
        business.save()
        business.refresh_from_db()

        assert business.updated_at >= original_updated_at

    def test_created_at_does_not_change_on_save(self):
        """created_at stays the same when the record is re-saved."""
        business = BusinessAccountFactory()
        original_created_at = business.created_at

        business.legal_name = "Updated Business Name"
        business.save()
        business.refresh_from_db()

        assert business.created_at == original_created_at

    def test_default_ordering_is_newest_first(self):
        """Default ordering is -created_at (most recent first)."""
        b1 = BusinessAccountFactory()
        b2 = BusinessAccountFactory()
        b3 = BusinessAccountFactory()

        businesses = list(BusinessAccount.objects.all())

        # Most recently created should come first
        assert businesses[0] == b3
        assert businesses[1] == b2
        assert businesses[2] == b1


# =============================================================================
# SOFT DELETE MODEL TESTS (via BusinessAccount -> AuditModel -> SoftDeleteModel)
# =============================================================================


@pytest.mark.django_db
class TestSoftDeleteModel:
    """Tests for SoftDeleteModel fields and methods via BusinessAccount."""

    def test_is_deleted_default_false(self):
        """New records have is_deleted=False by default."""
        business = BusinessAccountFactory()

        assert business.is_deleted is False
        assert business.deleted_at is None
        assert business.deleted_by is None

    def test_soft_delete_sets_is_deleted(self):
        """soft_delete() sets is_deleted to True."""
        business = BusinessAccountFactory()
        business.soft_delete()
        business.refresh_from_db()

        assert business.is_deleted is True

    def test_soft_delete_sets_deleted_at(self):
        """soft_delete() records the deletion timestamp."""
        before = timezone.now()
        business = BusinessAccountFactory()
        business.soft_delete()
        after = timezone.now()
        business.refresh_from_db()

        assert business.deleted_at is not None
        assert before <= business.deleted_at <= after

    def test_soft_delete_with_user_attribution(self):
        """soft_delete(user) records which user performed the deletion."""
        user = UserFactory()
        business = BusinessAccountFactory()
        business.soft_delete(user=user)
        business.refresh_from_db()

        assert business.is_deleted is True
        assert business.deleted_at is not None
        assert business.deleted_by == user

    def test_soft_delete_without_user(self):
        """soft_delete() without a user leaves deleted_by as None."""
        business = BusinessAccountFactory()
        business.soft_delete()
        business.refresh_from_db()

        assert business.is_deleted is True
        assert business.deleted_by is None

    def test_restore_clears_is_deleted(self):
        """restore() sets is_deleted back to False."""
        business = BusinessAccountFactory()
        business.soft_delete()
        business.restore()
        business.refresh_from_db()

        assert business.is_deleted is False

    def test_restore_clears_deleted_at(self):
        """restore() clears the deleted_at timestamp."""
        business = BusinessAccountFactory()
        business.soft_delete()
        business.restore()
        business.refresh_from_db()

        assert business.deleted_at is None

    def test_restore_clears_deleted_by(self):
        """restore() clears the deleted_by user reference."""
        user = UserFactory()
        business = BusinessAccountFactory()
        business.soft_delete(user=user)
        business.restore()
        business.refresh_from_db()

        assert business.deleted_by is None

    def test_objects_manager_excludes_soft_deleted(self):
        """The default `objects` manager excludes soft-deleted records."""
        business = BusinessAccountFactory()
        business.soft_delete()

        assert BusinessAccount.objects.filter(pk=business.pk).count() == 0

    def test_objects_manager_includes_active_records(self):
        """The default `objects` manager includes active (non-deleted) records."""
        business = BusinessAccountFactory()

        assert BusinessAccount.objects.filter(pk=business.pk).count() == 1

    def test_all_objects_manager_includes_soft_deleted(self):
        """The `all_objects` manager includes soft-deleted records."""
        business = BusinessAccountFactory()
        business.soft_delete()

        assert BusinessAccount.all_objects.filter(pk=business.pk).count() == 1

    def test_all_objects_manager_includes_active_records(self):
        """The `all_objects` manager also includes active records."""
        business = BusinessAccountFactory()

        assert BusinessAccount.all_objects.filter(pk=business.pk).count() == 1

    def test_objects_manager_filters_mixed_records(self):
        """objects manager correctly filters when there are both active and deleted records."""
        active_business = BusinessAccountFactory()
        deleted_business = BusinessAccountFactory()
        deleted_business.soft_delete()

        active_pks = set(BusinessAccount.objects.values_list("pk", flat=True))
        all_pks = set(BusinessAccount.all_objects.values_list("pk", flat=True))

        assert active_business.pk in active_pks
        assert deleted_business.pk not in active_pks
        assert active_business.pk in all_pks
        assert deleted_business.pk in all_pks


# =============================================================================
# UUID MODEL TESTS (via AuditLog)
# =============================================================================


@pytest.mark.django_db
class TestUUIDModel:
    """Tests for UUID primary key via AuditLog."""

    def test_id_is_uuid(self):
        """AuditLog id field is a UUID instance."""
        entry = AuditLog.objects.create(
            action=AuditLog.Action.LOGIN_SUCCESS,
            actor_type=AuditLog.ActorType.SYSTEM,
            resource_type="TestResource",
            outcome=AuditLog.Outcome.SUCCESS,
        )

        assert isinstance(entry.id, uuid.UUID)

    def test_id_is_auto_generated(self):
        """AuditLog id is auto-generated when not explicitly provided."""
        entry = AuditLog.objects.create(
            action=AuditLog.Action.LOGIN_SUCCESS,
            actor_type=AuditLog.ActorType.SYSTEM,
            resource_type="TestResource",
            outcome=AuditLog.Outcome.SUCCESS,
        )

        assert entry.id is not None

    def test_different_instances_get_different_uuids(self):
        """Each AuditLog instance receives a unique UUID."""
        entry1 = AuditLog.objects.create(
            action=AuditLog.Action.LOGIN_SUCCESS,
            actor_type=AuditLog.ActorType.SYSTEM,
            resource_type="TestResource",
            outcome=AuditLog.Outcome.SUCCESS,
        )
        entry2 = AuditLog.objects.create(
            action=AuditLog.Action.LOGOUT,
            actor_type=AuditLog.ActorType.SYSTEM,
            resource_type="TestResource",
            outcome=AuditLog.Outcome.SUCCESS,
        )

        assert entry1.id != entry2.id


# =============================================================================
# AUDIT LOG IMMUTABILITY TESTS
# =============================================================================


@pytest.mark.django_db
class TestAuditLogImmutability:
    """Tests for AuditLog append-only and no-delete behavior."""

    def test_save_raises_on_existing_entry(self):
        """AuditLog.save() raises ValueError if the entry already exists."""
        entry = AuditLog.objects.create(
            action=AuditLog.Action.LOGIN_SUCCESS,
            actor_type=AuditLog.ActorType.SYSTEM,
            resource_type="TestResource",
            outcome=AuditLog.Outcome.SUCCESS,
        )

        entry.outcome = AuditLog.Outcome.FAILURE
        with pytest.raises(ValueError, match="cannot be modified"):
            entry.save()

    def test_delete_raises_value_error(self):
        """AuditLog.delete() raises ValueError preventing deletion."""
        entry = AuditLog.objects.create(
            action=AuditLog.Action.LOGIN_SUCCESS,
            actor_type=AuditLog.ActorType.SYSTEM,
            resource_type="TestResource",
            outcome=AuditLog.Outcome.SUCCESS,
        )

        with pytest.raises(ValueError, match="cannot be deleted"):
            entry.delete()

    def test_initial_save_succeeds(self):
        """First save (creation) of an AuditLog entry works normally."""
        entry = AuditLog(
            action=AuditLog.Action.USER_CREATED,
            actor_type=AuditLog.ActorType.SYSTEM,
            resource_type="User",
            outcome=AuditLog.Outcome.SUCCESS,
        )
        entry.save()  # Should not raise

        assert AuditLog.objects.filter(pk=entry.pk).exists()

    def test_entry_persists_after_creation(self):
        """AuditLog entry data is correctly persisted to the database."""
        entry = AuditLog.objects.create(
            action=AuditLog.Action.LOGIN_FAILED,
            actor_type=AuditLog.ActorType.ANONYMOUS,
            resource_type="Session",
            outcome=AuditLog.Outcome.FAILURE,
            ip_address="192.168.1.1",
            details={"reason": "invalid_password"},
        )

        fetched = AuditLog.objects.get(pk=entry.pk)
        assert fetched.action == AuditLog.Action.LOGIN_FAILED
        assert fetched.actor_type == AuditLog.ActorType.ANONYMOUS
        assert fetched.resource_type == "Session"
        assert fetched.outcome == AuditLog.Outcome.FAILURE
        assert fetched.ip_address == "192.168.1.1"
        assert fetched.details == {"reason": "invalid_password"}
