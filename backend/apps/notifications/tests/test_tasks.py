"""
Tests for Notification Tasks
=============================
Covers dispatch_notification_task, retry_partial_notification_task,
and cleanup_old_notification_logs Celery tasks.
"""

import uuid
from datetime import timedelta
from unittest.mock import patch, MagicMock

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.notifications.models import NotificationLog
from apps.notifications.tasks import (
    dispatch_notification_task,
    retry_partial_notification_task,
    cleanup_old_notification_logs,
)
from apps.notifications.tests.factories import (
    NotificationLogFactory,
    SentNotificationLogFactory,
    FailedNotificationLogFactory,
    PartialNotificationLogFactory,
    ProcessingNotificationLogFactory,
)


# =============================================================================
# HELPERS
# =============================================================================


def _mock_channel(send_return):
    """Create a mock channel whose .send() returns the given dict."""
    channel = MagicMock()
    channel.send.return_value = send_return
    return channel


# =============================================================================
# DISPATCH NOTIFICATION TASK
# =============================================================================


@pytest.mark.django_db
class TestDispatchNotificationTask:
    """Tests for dispatch_notification_task."""

    def test_dispatch_not_found_returns_none(self):
        """When log_id does not exist, the task returns early without error."""
        fake_id = str(uuid.uuid4())

        result = dispatch_notification_task(fake_id)

        assert result is None

    def test_dispatch_skips_non_pending(self):
        """A log already in PROCESSING status is not re-dispatched (idempotency)."""
        log = ProcessingNotificationLogFactory()

        result = dispatch_notification_task(str(log.id))

        assert result is None

        log.refresh_from_db()
        assert log.status == NotificationLog.Status.PROCESSING

    @patch("apps.notifications.services.channels.get_channel")
    def test_dispatch_sends_to_channels(self, mock_get_channel):
        """All channels receive .send() calls and final status is SENT."""
        email_channel = _mock_channel({"status": "sent", "email_log_id": "abc123"})
        push_channel = _mock_channel({"status": "sent", "push_id": "xyz789"})

        def channel_lookup(name):
            return {"email": email_channel, "push": push_channel}.get(name)

        mock_get_channel.side_effect = channel_lookup

        log = NotificationLogFactory(channels=["email", "push"])

        dispatch_notification_task(str(log.id))

        log.refresh_from_db()
        assert log.status == NotificationLog.Status.SENT

        email_channel.send.assert_called_once_with(
            user=log.user,
            notification_type=log.notification_type,
            context=log.context,
        )
        push_channel.send.assert_called_once_with(
            user=log.user,
            notification_type=log.notification_type,
            context=log.context,
        )

        assert log.channel_results["email"]["status"] == "sent"
        assert log.channel_results["push"]["status"] == "sent"

    @patch("apps.notifications.services.channels.get_channel")
    def test_dispatch_partial_when_some_channels_fail(self, mock_get_channel):
        """Email succeeds but push fails -> PARTIAL status."""
        email_channel = _mock_channel({"status": "sent", "email_log_id": "abc123"})
        push_channel = _mock_channel({"status": "failed", "error": "Push service down"})

        def channel_lookup(name):
            return {"email": email_channel, "push": push_channel}.get(name)

        mock_get_channel.side_effect = channel_lookup

        log = NotificationLogFactory(channels=["email", "push"])

        dispatch_notification_task(str(log.id))

        log.refresh_from_db()
        assert log.status == NotificationLog.Status.PARTIAL
        assert log.channel_results["email"]["status"] == "sent"
        assert log.channel_results["push"]["status"] == "failed"

    @patch("apps.notifications.services.channels.get_channel")
    def test_dispatch_failed_when_all_channels_fail(self, mock_get_channel):
        """All channels return failed -> FAILED status."""
        email_channel = _mock_channel({"status": "failed", "error": "SMTP error"})
        push_channel = _mock_channel({"status": "failed", "error": "Push error"})

        def channel_lookup(name):
            return {"email": email_channel, "push": push_channel}.get(name)

        mock_get_channel.side_effect = channel_lookup

        log = NotificationLogFactory(channels=["email", "push"])

        dispatch_notification_task(str(log.id))

        log.refresh_from_db()
        assert log.status == NotificationLog.Status.FAILED
        assert log.channel_results["email"]["status"] == "failed"
        assert log.channel_results["push"]["status"] == "failed"

    @patch("apps.notifications.services.channels.get_channel")
    def test_dispatch_all_skipped_is_sent(self, mock_get_channel):
        """When all channels return skipped, final status is SENT."""
        email_channel = _mock_channel({"status": "skipped", "reason": "Not configured"})
        push_channel = _mock_channel({"status": "skipped", "reason": "No device"})

        def channel_lookup(name):
            return {"email": email_channel, "push": push_channel}.get(name)

        mock_get_channel.side_effect = channel_lookup

        log = NotificationLogFactory(channels=["email", "push"])

        dispatch_notification_task(str(log.id))

        log.refresh_from_db()
        assert log.status == NotificationLog.Status.SENT

    @patch("apps.notifications.tasks.retry_partial_notification_task")
    @patch("apps.notifications.services.channels.get_channel")
    def test_dispatch_partial_schedules_retry(
        self, mock_get_channel, mock_retry_task
    ):
        """When dispatch results in PARTIAL, retry_partial_notification_task is scheduled."""
        email_channel = _mock_channel({"status": "sent"})
        push_channel = _mock_channel({"status": "failed", "error": "Timeout"})

        def channel_lookup(name):
            return {"email": email_channel, "push": push_channel}.get(name)

        mock_get_channel.side_effect = channel_lookup

        log = NotificationLogFactory(channels=["email", "push"])

        dispatch_notification_task(str(log.id))

        log.refresh_from_db()
        assert log.status == NotificationLog.Status.PARTIAL

        mock_retry_task.apply_async.assert_called_once_with(
            args=[str(log.id)],
            countdown=300,
        )


# =============================================================================
# RETRY PARTIAL NOTIFICATION TASK
# =============================================================================


@pytest.mark.django_db
class TestRetryPartialNotificationTask:
    """Tests for retry_partial_notification_task."""

    @patch("apps.notifications.services.channels.get_channel")
    def test_retry_only_retries_failed_channels(self, mock_get_channel):
        """Only failed channels are retried; 'sent' channels are preserved."""
        push_channel = _mock_channel({"status": "sent", "push_id": "new_push_id"})

        def channel_lookup(name):
            return {"push": push_channel}.get(name)

        mock_get_channel.side_effect = channel_lookup

        log = PartialNotificationLogFactory()
        # PartialNotificationLogFactory sets:
        #   channels=["email", "push"]
        #   channel_results={"email": {"status": "sent", ...}, "push": {"status": "failed", ...}}

        retry_partial_notification_task(str(log.id))

        log.refresh_from_db()

        # Email was already sent -- channel should NOT have been called for email
        assert log.channel_results["email"]["status"] == "sent"
        # Push was failed and should now be retried successfully
        assert log.channel_results["push"]["status"] == "sent"

        # The push channel send was called exactly once (only for push, not email)
        push_channel.send.assert_called_once_with(
            user=log.user,
            notification_type=log.notification_type,
            context=log.context,
        )

        # Final status should now be SENT since all channels succeeded
        assert log.status == NotificationLog.Status.SENT

    def test_retry_skips_non_partial(self):
        """A log that is not PARTIAL is not retried."""
        log = SentNotificationLogFactory()

        result = retry_partial_notification_task(str(log.id))

        assert result is None

        log.refresh_from_db()
        assert log.status == NotificationLog.Status.SENT
        assert log.retry_count == 0

    @patch("apps.notifications.services.channels.get_channel")
    def test_retry_increments_retry_count(self, mock_get_channel):
        """Each retry attempt increments the log's retry_count."""
        push_channel = _mock_channel({"status": "failed", "error": "Still down"})

        def channel_lookup(name):
            return {"push": push_channel}.get(name)

        mock_get_channel.side_effect = channel_lookup

        log = PartialNotificationLogFactory(retry_count=0)
        original_retry_count = log.retry_count

        retry_partial_notification_task(str(log.id))

        log.refresh_from_db()
        assert log.retry_count == original_retry_count + 1


# =============================================================================
# CLEANUP OLD NOTIFICATION LOGS
# =============================================================================


@pytest.mark.django_db
class TestCleanupOldNotificationLogs:
    """Tests for cleanup_old_notification_logs."""

    def test_cleanup_deletes_old_logs(self):
        """Logs older than 90 days (default retention) are deleted."""
        log = NotificationLogFactory()
        old_date = timezone.now() - timedelta(days=91)
        NotificationLog.objects.filter(pk=log.pk).update(created_at=old_date)

        deleted_count = cleanup_old_notification_logs()

        assert deleted_count == 1
        assert not NotificationLog.objects.filter(pk=log.pk).exists()

    def test_cleanup_preserves_recent_logs(self):
        """Logs newer than 90 days are not deleted."""
        log = NotificationLogFactory()
        recent_date = timezone.now() - timedelta(days=30)
        NotificationLog.objects.filter(pk=log.pk).update(created_at=recent_date)

        deleted_count = cleanup_old_notification_logs()

        assert deleted_count == 0
        assert NotificationLog.objects.filter(pk=log.pk).exists()

    @override_settings(NOTIFICATION_LOG_RETENTION_DAYS=30)
    def test_cleanup_respects_retention_setting(self):
        """Uses NOTIFICATION_LOG_RETENTION_DAYS when configured (e.g. 30 days)."""
        old_log = NotificationLogFactory()
        old_date = timezone.now() - timedelta(days=31)
        NotificationLog.objects.filter(pk=old_log.pk).update(created_at=old_date)

        recent_log = NotificationLogFactory()
        recent_date = timezone.now() - timedelta(days=29)
        NotificationLog.objects.filter(pk=recent_log.pk).update(created_at=recent_date)

        deleted_count = cleanup_old_notification_logs()

        assert deleted_count == 1
        assert not NotificationLog.objects.filter(pk=old_log.pk).exists()
        assert NotificationLog.objects.filter(pk=recent_log.pk).exists()
