"""
Tests for Notification app selectors.
======================================
Covers NotificationLogSelector and NotificationPreferenceSelector query logic.
All tests use real DB data (no mocking).
"""

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.notifications.models import NotificationLog, NotificationPreference
from apps.notifications.selectors import (
    NotificationLogSelector,
    NotificationPreferenceSelector,
)
from apps.notifications.tests.factories import (
    FailedNotificationLogFactory,
    NotificationLogFactory,
    NotificationPreferenceFactory,
    PartialNotificationLogFactory,
    SentNotificationLogFactory,
)
from apps.users.tests.factories import UserFactory

# =============================================================================
# NOTIFICATION LOG SELECTOR
# =============================================================================


@pytest.mark.django_db
class TestNotificationLogSelector:
    """Tests for NotificationLogSelector read-only queries."""

    def test_get_by_id_found(self):
        """get_by_id returns the log matching the given UUID."""
        log = NotificationLogFactory()

        result = NotificationLogSelector.get_by_id(log.id)

        assert result is not None
        assert result.id == log.id
        assert result.notification_type == log.notification_type

    def test_get_by_id_not_found(self):
        """get_by_id returns None for a random UUID that does not exist."""
        random_id = uuid.uuid4()

        result = NotificationLogSelector.get_by_id(random_id)

        assert result is None

    def test_get_user_history_returns_user_logs(self):
        """get_user_history returns only logs belonging to the target user."""
        user_a = UserFactory()
        user_b = UserFactory()

        log_a1 = NotificationLogFactory(user=user_a)
        log_a2 = NotificationLogFactory(user=user_a)
        log_b1 = NotificationLogFactory(user=user_b)

        result = list(NotificationLogSelector.get_user_history(user=user_a))

        result_ids = {log.id for log in result}
        assert log_a1.id in result_ids
        assert log_a2.id in result_ids
        assert log_b1.id not in result_ids
        assert len(result) == 2

    def test_get_user_history_filters_by_type(self):
        """get_user_history filters by notification_type when provided."""
        user = UserFactory()

        welcome_log = NotificationLogFactory(user=user, notification_type="welcome")
        login_log = NotificationLogFactory(user=user, notification_type="new_login")

        result = list(
            NotificationLogSelector.get_user_history(
                user=user, notification_type="welcome"
            )
        )

        result_ids = {log.id for log in result}
        assert welcome_log.id in result_ids
        assert login_log.id not in result_ids
        assert len(result) == 1

    def test_get_user_history_filters_by_status(self):
        """get_user_history filters by status when provided."""
        user = UserFactory()

        pending_log = NotificationLogFactory(
            user=user, status=NotificationLog.Status.PENDING
        )
        sent_log = SentNotificationLogFactory(user=user)

        result = list(
            NotificationLogSelector.get_user_history(
                user=user, status=NotificationLog.Status.SENT
            )
        )

        result_ids = {log.id for log in result}
        assert sent_log.id in result_ids
        assert pending_log.id not in result_ids
        assert len(result) == 1

    def test_get_user_history_respects_limit(self):
        """get_user_history truncates results to the specified limit."""
        user = UserFactory()

        for _ in range(5):
            NotificationLogFactory(user=user)

        result = list(NotificationLogSelector.get_user_history(user=user, limit=3))

        assert len(result) == 3

    def test_get_user_history_ordered_by_created_at_desc(self):
        """get_user_history returns logs ordered by -created_at."""
        user = UserFactory()
        now = timezone.now()

        log_old = NotificationLogFactory(user=user)
        log_mid = NotificationLogFactory(user=user)
        log_new = NotificationLogFactory(user=user)

        # Force distinct created_at timestamps via direct DB update
        NotificationLog.objects.filter(pk=log_old.pk).update(
            created_at=now - timedelta(hours=3)
        )
        NotificationLog.objects.filter(pk=log_mid.pk).update(
            created_at=now - timedelta(hours=2)
        )
        NotificationLog.objects.filter(pk=log_new.pk).update(
            created_at=now - timedelta(hours=1)
        )

        result = list(NotificationLogSelector.get_user_history(user=user))

        assert result[0].id == log_new.id
        assert result[1].id == log_mid.id
        assert result[2].id == log_old.id

    def test_get_pending_count(self):
        """get_pending_count returns count of only PENDING notifications."""
        user = UserFactory()

        NotificationLogFactory(user=user, status=NotificationLog.Status.PENDING)
        NotificationLogFactory(user=user, status=NotificationLog.Status.PENDING)
        NotificationLogFactory(user=user, status=NotificationLog.Status.PENDING)
        SentNotificationLogFactory(user=user)
        FailedNotificationLogFactory(user=user)

        count = NotificationLogSelector.get_pending_count(user=user)

        assert count == 3

    def test_get_pending_count_zero(self):
        """get_pending_count returns 0 when user has no pending logs."""
        user = UserFactory()
        SentNotificationLogFactory(user=user)

        count = NotificationLogSelector.get_pending_count(user=user)

        assert count == 0

    def test_get_failed_logs(self):
        """get_failed_logs returns only FAILED logs and respects limit."""
        FailedNotificationLogFactory()
        FailedNotificationLogFactory()
        FailedNotificationLogFactory()
        SentNotificationLogFactory()
        PartialNotificationLogFactory()
        NotificationLogFactory(status=NotificationLog.Status.PENDING)

        # Without limit - should return all 3 failed
        all_failed = list(NotificationLogSelector.get_failed_logs())
        assert len(all_failed) == 3
        assert all(log.status == NotificationLog.Status.FAILED for log in all_failed)

        # With limit
        limited = list(NotificationLogSelector.get_failed_logs(limit=2))
        assert len(limited) == 2
        assert all(log.status == NotificationLog.Status.FAILED for log in limited)

    def test_get_partial_logs(self):
        """get_partial_logs returns only PARTIAL logs."""
        PartialNotificationLogFactory()
        PartialNotificationLogFactory()
        FailedNotificationLogFactory()
        SentNotificationLogFactory()
        NotificationLogFactory(status=NotificationLog.Status.PENDING)

        result = list(NotificationLogSelector.get_partial_logs())

        assert len(result) == 2
        assert all(log.status == NotificationLog.Status.PARTIAL for log in result)


# =============================================================================
# NOTIFICATION PREFERENCE SELECTOR
# =============================================================================


@pytest.mark.django_db
class TestNotificationPreferenceSelector:
    """Tests for NotificationPreferenceSelector read-only queries."""

    def test_get_user_preferences_returns_all_types(self):
        """get_user_preferences returns entries for all notification types."""
        user = UserFactory()

        prefs = NotificationPreferenceSelector.get_user_preferences(user=user)

        expected_types = {
            "verify_email",
            "welcome",
            "password_reset",
            "password_changed",
            "new_login",
            "suspicious_activity",
            "newsletter",
            "promotions",
            "transaction_invitation_received",
            "transaction_accepted",
            "transaction_denied",
            "transaction_cancelled",
            "transaction_expired",
            "transaction_expiring_soon",
            "transaction_info_requested",
            "transaction_resubmitted",
            "transaction_pending_approval",
            # Social / Network
            "new_follower",
            "follow_request_received",
            "follow_request_accepted",
            "connection_request_received",
            "connection_accepted",
            # Social / Chat
            "chat_message_received",
            "chat_request_received",
            "chat_request_accepted",
            "chat_group_added",
            "chat_reaction_received",
        }
        assert set(prefs.keys()) == expected_types
        assert len(prefs) == 27

        # Each entry has the required keys
        for type_name, entry in prefs.items():
            assert "display_name" in entry
            assert "description" in entry
            assert "category" in entry
            assert "user_configurable" in entry
            assert "email_enabled" in entry
            assert "push_enabled" in entry
            assert "sms_enabled" in entry

    def test_get_user_preferences_uses_stored_overrides(self):
        """Stored preference overrides default channel settings."""
        user = UserFactory()

        # 'welcome' defaults to email only. Override to disable email, enable push.
        NotificationPreferenceFactory(
            user=user,
            notification_type="welcome",
            email_enabled=False,
            push_enabled=True,
            sms_enabled=True,
        )

        prefs = NotificationPreferenceSelector.get_user_preferences(user=user)

        welcome = prefs["welcome"]
        assert welcome["email_enabled"] is False
        assert welcome["push_enabled"] is True
        assert welcome["sms_enabled"] is True

    def test_get_user_preferences_uses_defaults_when_no_override(self):
        """Without a stored preference, defaults from NotificationTypeConfig are used."""
        user = UserFactory()

        prefs = NotificationPreferenceSelector.get_user_preferences(user=user)

        # 'welcome' defaults: email=True (default channel), push=False, sms=False
        welcome = prefs["welcome"]
        assert welcome["email_enabled"] is True
        assert welcome["push_enabled"] is False
        assert welcome["sms_enabled"] is False

        # 'suspicious_activity' defaults: email=True, push=True (both default), sms=False
        suspicious = prefs["suspicious_activity"]
        assert suspicious["email_enabled"] is True
        assert suspicious["push_enabled"] is True
        assert suspicious["sms_enabled"] is False

    def test_get_users_with_channel_enabled_default_channel(self):
        """
        For a default channel (email for 'welcome'), returns all active users
        except those who explicitly disabled it.
        """
        user_a = UserFactory()
        user_b = UserFactory()
        user_disabled = UserFactory()

        # user_disabled explicitly disables email for 'welcome'
        NotificationPreferenceFactory(
            user=user_disabled,
            notification_type="welcome",
            email_enabled=False,
        )

        result = NotificationPreferenceSelector.get_users_with_channel_enabled(
            notification_type="welcome",
            channel="email",
        )

        result_ids = {u.id for u in result}
        assert user_a.id in result_ids
        assert user_b.id in result_ids
        assert user_disabled.id not in result_ids

    def test_get_users_with_channel_enabled_non_default_channel(self):
        """
        For a non-default channel (push for 'newsletter'), returns only users
        who explicitly enabled it.
        """
        user_default = UserFactory()  # No preference stored, push not in defaults
        user_enabled = UserFactory()
        user_disabled = UserFactory()

        # user_enabled explicitly enables push for 'newsletter'
        NotificationPreferenceFactory(
            user=user_enabled,
            notification_type="newsletter",
            push_enabled=True,
        )

        # user_disabled explicitly disables push for 'newsletter'
        NotificationPreferenceFactory(
            user=user_disabled,
            notification_type="newsletter",
            push_enabled=False,
        )

        result = NotificationPreferenceSelector.get_users_with_channel_enabled(
            notification_type="newsletter",
            channel="push",
        )

        result_ids = {u.id for u in result}
        # Only user_enabled should be included - they explicitly enabled push
        assert user_enabled.id in result_ids
        # user_default has no stored preference and push is not a default channel
        assert user_default.id not in result_ids
        # user_disabled explicitly disabled push
        assert user_disabled.id not in result_ids

    def test_get_users_with_channel_enabled_unknown_type(self):
        """Returns empty list for an unknown notification type."""
        result = NotificationPreferenceSelector.get_users_with_channel_enabled(
            notification_type="nonexistent_type",
            channel="email",
        )

        assert result == []

    def test_get_users_with_channel_enabled_unknown_channel(self):
        """Returns empty list for an unknown channel name."""
        result = NotificationPreferenceSelector.get_users_with_channel_enabled(
            notification_type="welcome",
            channel="carrier_pigeon",
        )

        assert result == []


# =============================================================================
# OFFSET PAGINATION (ISSUE-7 tests)
# =============================================================================


@pytest.mark.django_db
class TestNotificationLogSelectorOffset:
    """Verify offset parameter on get_user_history."""

    def test_offset_skips_results(self):
        """offset=2 skips the first 2 results."""
        user = UserFactory()
        for _ in range(5):
            NotificationLogFactory(user=user)

        results = NotificationLogSelector.get_user_history(
            user=user, offset=2, limit=10
        )

        assert len(results) == 3  # 5 total - 2 skipped

    def test_offset_and_limit_combined(self):
        """offset=1, limit=2 returns middle slice."""
        user = UserFactory()
        for _ in range(5):
            NotificationLogFactory(user=user)

        results = NotificationLogSelector.get_user_history(user=user, offset=1, limit=2)

        assert len(results) == 2

    def test_offset_zero_returns_all(self):
        """offset=0 (default) returns from the beginning."""
        user = UserFactory()
        for _ in range(3):
            NotificationLogFactory(user=user)

        results = NotificationLogSelector.get_user_history(user=user, offset=0)

        assert len(results) == 3


# =============================================================================
# SCOPE FILTERING
# =============================================================================


@pytest.mark.django_db
class TestNotificationLogSelectorScope:
    """Verify scope filtering on get_user_history."""

    def test_scope_type_filter(self):
        """scope_type filter returns only matching logs."""
        from apps.notifications.tests.factories import ScopedNotificationLogFactory

        user = UserFactory()
        NotificationLogFactory(user=user)  # user-scoped
        ScopedNotificationLogFactory(user=user)  # business-scoped

        results = NotificationLogSelector.get_user_history(
            user=user, scope_type="business"
        )
        assert len(results) == 1
        assert results[0].scope_type == "business"

    def test_scope_id_filter(self):
        """scope_id filter returns only matching logs."""
        import uuid

        from apps.notifications.tests.factories import ScopedNotificationLogFactory

        user = UserFactory()
        biz_id = uuid.uuid4()
        ScopedNotificationLogFactory(user=user, scope_id=biz_id)
        ScopedNotificationLogFactory(user=user, scope_id=uuid.uuid4())

        results = NotificationLogSelector.get_user_history(
            user=user, scope_type="business", scope_id=biz_id
        )
        assert len(results) == 1
        assert results[0].scope_id == biz_id

    def test_no_scope_filter_returns_all(self):
        """Without scope params, returns all scopes."""
        from apps.notifications.tests.factories import ScopedNotificationLogFactory

        user = UserFactory()
        NotificationLogFactory(user=user)
        ScopedNotificationLogFactory(user=user)

        results = NotificationLogSelector.get_user_history(user=user)
        assert len(results) == 2


@pytest.mark.django_db
class TestNotificationLogSelectorScopes:
    """Tests for get_user_notification_scopes."""

    def test_returns_distinct_scopes(self):
        """Returns distinct scope_type/scope_id combinations with counts."""
        from apps.notifications.tests.factories import ScopedNotificationLogFactory

        user = UserFactory()
        NotificationLogFactory(user=user)
        NotificationLogFactory(user=user)
        ScopedNotificationLogFactory(user=user)

        scopes = list(NotificationLogSelector.get_user_notification_scopes(user=user))

        assert len(scopes) >= 2
        scope_types = {s["scope_type"] for s in scopes}
        assert "user" in scope_types
        assert "business" in scope_types

    def test_empty_for_new_user(self):
        """Returns empty for user with no notifications."""
        user = UserFactory()
        scopes = list(NotificationLogSelector.get_user_notification_scopes(user=user))
        assert scopes == []
