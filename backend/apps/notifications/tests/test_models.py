"""
Tests for Notification app models.
===================================
Covers NotificationPreference and NotificationLog model behavior,
field defaults, constraints, and helper methods.
"""

import uuid

import pytest
from django.db import IntegrityError, transaction

from apps.notifications.models import NotificationLog, NotificationPreference
from apps.notifications.tests.factories import (
    DisabledPreferenceFactory,
    FailedNotificationLogFactory,
    NotificationLogFactory,
    NotificationPreferenceFactory,
    SentNotificationLogFactory,
)
from apps.users.tests.factories import UserFactory

# =============================================================================
# NOTIFICATION PREFERENCE
# =============================================================================


@pytest.mark.django_db
class TestNotificationPreference:
    """Tests for the NotificationPreference model."""

    def test_creation_with_factory(self):
        """Factory creates a valid NotificationPreference with all fields set."""
        pref = NotificationPreferenceFactory()

        assert pref.pk is not None
        assert pref.user is not None
        assert pref.notification_type == "new_login"
        assert pref.email_enabled is True
        assert pref.push_enabled is True
        assert pref.sms_enabled is False
        assert pref.created_at is not None
        assert pref.updated_at is not None

    def test_str_representation(self):
        """__str__ returns '{user.email} - {notification_type}'."""
        pref = NotificationPreferenceFactory(notification_type="campaign_update")

        expected = f"{pref.user.email} - campaign_update"
        assert str(pref) == expected

    def test_default_values(self):
        """Default channel booleans: email=True, push=True, sms=False."""
        pref = NotificationPreferenceFactory()

        assert pref.email_enabled is True
        assert pref.push_enabled is True
        assert pref.sms_enabled is False

    def test_unique_together_constraint(self):
        """Cannot create two preferences for the same user + notification_type."""
        pref = NotificationPreferenceFactory(notification_type="weekly_digest")

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                NotificationPreferenceFactory(
                    user=pref.user,
                    notification_type="weekly_digest",
                )

    def test_get_enabled_channels_all_enabled(self):
        """When all three channels are enabled, returns ['email', 'push', 'sms']."""
        pref = NotificationPreferenceFactory(
            email_enabled=True,
            push_enabled=True,
            sms_enabled=True,
        )

        assert pref.get_enabled_channels() == ["email", "push", "sms"]

    def test_get_enabled_channels_default(self):
        """Default values yield ['email', 'push'] (sms disabled by default)."""
        pref = NotificationPreferenceFactory()

        assert pref.get_enabled_channels() == ["email", "push"]

    def test_get_enabled_channels_none_enabled(self):
        """When all channels are disabled, returns an empty list."""
        pref = DisabledPreferenceFactory()

        assert pref.get_enabled_channels() == []

    def test_get_enabled_channels_email_only(self):
        """When only email is enabled, returns ['email']."""
        pref = NotificationPreferenceFactory(
            email_enabled=True,
            push_enabled=False,
            sms_enabled=False,
        )

        assert pref.get_enabled_channels() == ["email"]


# =============================================================================
# NOTIFICATION LOG
# =============================================================================


@pytest.mark.django_db
class TestNotificationLog:
    """Tests for the NotificationLog model."""

    def test_creation_with_factory(self):
        """Factory creates a valid NotificationLog with all expected fields."""
        log = NotificationLogFactory()

        assert log.pk is not None
        assert log.user is not None
        assert log.notification_type == "welcome"
        assert log.channels == ["email"]
        assert log.context == {}
        assert log.status == NotificationLog.Status.PENDING
        assert log.retry_count == 0
        assert log.channel_results == {}
        assert log.error_message == ""
        assert log.created_at is not None
        assert log.updated_at is not None

    def test_str_representation(self):
        """__str__ returns '{notification_type} -> {user.email} ({status})' when user exists."""
        log = NotificationLogFactory(notification_type="order_confirmation")

        expected = f"order_confirmation \u2192 {log.user.email} ({log.status})"
        assert str(log) == expected

    def test_str_representation_null_user(self):
        """__str__ shows 'Unknown' when user is None."""
        log = NotificationLogFactory(user=None, notification_type="system_alert")

        expected = "system_alert \u2192 Unknown (pending)"
        assert str(log) == expected

    def test_uuid_primary_key(self):
        """The id field is a UUID instance."""
        log = NotificationLogFactory()

        assert isinstance(log.id, uuid.UUID)

    def test_default_status_is_pending(self):
        """A newly created log defaults to PENDING status."""
        log = NotificationLogFactory()

        assert log.status == NotificationLog.Status.PENDING
        assert log.status == "pending"

    def test_ordering_by_created_at_desc(self):
        """Model Meta ordering is ['-created_at']."""
        assert NotificationLog._meta.ordering == ["-created_at"]

    def test_status_choices_all_valid(self):
        """All six status choices can be saved without error."""
        all_statuses = [
            NotificationLog.Status.PENDING,
            NotificationLog.Status.PROCESSING,
            NotificationLog.Status.SENT,
            NotificationLog.Status.PARTIAL,
            NotificationLog.Status.RETRYING,
            NotificationLog.Status.FAILED,
        ]

        for status_value in all_statuses:
            log = NotificationLogFactory(status=status_value)
            log.refresh_from_db()
            assert log.status == status_value

    def test_default_json_fields(self):
        """Default JSON fields: channels=[], context={}, channel_results={}."""
        log = NotificationLogFactory()

        assert log.channels == ["email"]  # factory default

        # Verify model-level defaults by creating directly
        from apps.users.tests.factories import UserFactory

        user = UserFactory()
        direct_log = NotificationLog.objects.create(
            user=user,
            notification_type="test_direct",
        )
        assert direct_log.channels == []
        assert direct_log.context == {}
        assert direct_log.channel_results == {}

    def test_user_on_delete_set_null(self):
        """Deleting the associated user sets user to None (SET_NULL)."""
        log = NotificationLogFactory()
        user_pk = log.user.pk

        log.user.delete()
        log.refresh_from_db()

        assert log.user is None

    def test_retry_count_default_zero(self):
        """Default retry_count is 0."""
        log = NotificationLogFactory()

        assert log.retry_count == 0


# =============================================================================
# SCOPE FIELDS
# =============================================================================


@pytest.mark.django_db
class TestNotificationLogScope:
    """Tests for scope fields on NotificationLog."""

    def test_default_scope_type_is_user(self):
        """Default scope_type is 'user'."""
        log = NotificationLogFactory()
        assert log.scope_type == "user"

    def test_default_scope_id_is_none(self):
        """Default scope_id is None."""
        log = NotificationLogFactory()
        assert log.scope_id is None

    def test_business_scope(self):
        """Can create log with business scope."""
        from apps.notifications.tests.factories import ScopedNotificationLogFactory

        log = ScopedNotificationLogFactory()
        assert log.scope_type == "business"
        assert log.scope_id is not None

    def test_str_includes_scope(self):
        """__str__ includes scope for non-user scopes."""
        from apps.notifications.tests.factories import ScopedNotificationLogFactory

        log = ScopedNotificationLogFactory()
        assert "[business]" in str(log)

    def test_str_excludes_scope_for_user(self):
        """__str__ does not include scope for user scope."""
        log = NotificationLogFactory()
        assert "[user]" not in str(log)


@pytest.mark.django_db
class TestNotificationPreferenceScope:
    """Tests for scope fields on NotificationPreference."""

    def test_default_scope_type_is_user(self):
        """Default scope_type is 'user'."""
        pref = NotificationPreferenceFactory()
        assert pref.scope_type == "user"

    def test_scoped_preference_creation(self):
        """Can create a business-scoped preference."""
        from apps.notifications.tests.factories import ScopedPreferenceFactory

        pref = ScopedPreferenceFactory()
        assert pref.scope_type == "business"
        assert pref.scope_id is not None

    def test_unique_global_constraint(self):
        """Cannot create two global preferences for same user+type."""
        pref = NotificationPreferenceFactory(notification_type="new_login")

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                NotificationPreferenceFactory(
                    user=pref.user,
                    notification_type="new_login",
                )

    def test_scoped_and_global_coexist(self):
        """A user can have both global and scoped preferences for same type."""
        import uuid

        user = UserFactory()
        # Global preference
        NotificationPreferenceFactory(user=user, notification_type="new_login")
        # Scoped preference for a business
        from apps.notifications.tests.factories import ScopedPreferenceFactory

        ScopedPreferenceFactory(
            user=user,
            notification_type="new_login",
            scope_id=uuid.uuid4(),
        )
        # Should have 2 preferences
        assert (
            NotificationPreference.objects.filter(
                user=user, notification_type="new_login"
            ).count()
            == 2
        )
