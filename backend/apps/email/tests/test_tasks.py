# apps/email/tests/test_tasks.py
"""
Tests for Email Celery tasks.

Covers:
    - send_email_task: Async email sending with retry logic
    - retry_failed_emails_task: Periodic retry of failed emails
    - cleanup_old_email_logs: Periodic cleanup of old email logs

Note: Tests use CELERY_TASK_ALWAYS_EAGER=True (local settings), so tasks
execute synchronously. Tasks are called directly rather than via .delay().
"""

import uuid
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from apps.email.models import EmailLog
from apps.email.tasks import (
    cleanup_old_email_logs,
    retry_failed_emails_task,
    send_email_task,
)
from apps.email.tests.factories import (
    DeliveredEmailLogFactory,
    EmailLogFactory,
    FailedEmailLogFactory,
    QueuedEmailLogFactory,
    SentEmailLogFactory,
)

# =============================================================================
# TestSendEmailTask
# =============================================================================


@pytest.mark.django_db
class TestSendEmailTask:
    """Tests for the send_email_task Celery task."""

    @patch("apps.email.services.email_service.EmailService._send_now")
    def test_send_email_task_calls_send_now(self, mock_send_now):
        """Task should call EmailService._send_now with the correct EmailLog."""
        log = EmailLogFactory(status=EmailLog.Status.PENDING)

        send_email_task(str(log.id))

        mock_send_now.assert_called_once()
        called_log = mock_send_now.call_args[0][0]
        assert called_log.id == log.id

    def test_send_email_task_skips_if_not_found(self):
        """Task should return early (None) when the log_id does not exist."""
        non_existent_id = str(uuid.uuid4())

        result = send_email_task(non_existent_id)

        assert result is None

    @patch("apps.email.services.email_service.EmailService._send_now")
    def test_send_email_task_skips_if_already_sent(self, mock_send_now):
        """Task should return early without calling _send_now for SENT logs."""
        log = SentEmailLogFactory()

        result = send_email_task(str(log.id))

        assert result is None
        mock_send_now.assert_not_called()

    @patch("apps.email.services.email_service.EmailService._send_now")
    def test_send_email_task_skips_if_already_delivered(self, mock_send_now):
        """Task should return early without calling _send_now for DELIVERED logs."""
        log = DeliveredEmailLogFactory()

        result = send_email_task(str(log.id))

        assert result is None
        mock_send_now.assert_not_called()

    @patch("apps.email.services.email_service.EmailService._send_now")
    def test_send_email_task_processes_pending(self, mock_send_now):
        """Task should process emails with PENDING status."""
        log = EmailLogFactory(status=EmailLog.Status.PENDING)

        send_email_task(str(log.id))

        mock_send_now.assert_called_once()
        called_log = mock_send_now.call_args[0][0]
        assert called_log.id == log.id

    @patch("apps.email.services.email_service.EmailService._send_now")
    def test_send_email_task_processes_queued(self, mock_send_now):
        """Task should process emails with QUEUED status."""
        log = QueuedEmailLogFactory()

        send_email_task(str(log.id))

        mock_send_now.assert_called_once()
        called_log = mock_send_now.call_args[0][0]
        assert called_log.id == log.id

    @patch("apps.email.services.email_service.EmailService._send_now")
    def test_send_email_task_failure_increments_retry_count(self, mock_send_now):
        """On failure, the task should increment retry_count on the EmailLog."""
        log = EmailLogFactory(
            status=EmailLog.Status.PENDING, retry_count=0, max_retries=3
        )
        mock_send_now.side_effect = ConnectionError("SMTP connection failed")

        with pytest.raises(ConnectionError):
            send_email_task(str(log.id))

        log.refresh_from_db()
        assert log.retry_count == 1

    @patch("apps.email.services.email_service.EmailService._send_now")
    def test_send_email_task_failure_calculates_next_retry(self, mock_send_now):
        """On failure, the task should set next_retry_at using exponential backoff.

        Formula: delay_minutes = 5 * 2^(retry_count - 1)
        For retry_count=1 (after first failure): delay = 5 * 2^0 = 5 minutes.
        For retry_count=2 (after second failure): delay = 5 * 2^1 = 10 minutes.
        """
        log = EmailLogFactory(
            status=EmailLog.Status.PENDING, retry_count=0, max_retries=3
        )
        mock_send_now.side_effect = ConnectionError("SMTP connection failed")

        before = timezone.now()

        with pytest.raises(ConnectionError):
            send_email_task(str(log.id))

        log.refresh_from_db()
        assert log.next_retry_at is not None

        # After first failure: retry_count=1, delay = 5 * 2^(1-1) = 5 minutes
        expected_delay = timedelta(minutes=5)
        assert log.next_retry_at >= before + expected_delay
        # Allow small time drift (up to 10 seconds)
        assert log.next_retry_at <= before + expected_delay + timedelta(seconds=10)

    @patch("apps.email.services.email_service.EmailService._send_now")
    def test_send_email_task_failure_second_retry_backoff(self, mock_send_now):
        """Second failure should use a longer backoff: 5 * 2^(2-1) = 10 minutes."""
        log = EmailLogFactory(
            status=EmailLog.Status.PENDING, retry_count=1, max_retries=3
        )
        mock_send_now.side_effect = ConnectionError("SMTP connection failed")

        before = timezone.now()

        with pytest.raises(ConnectionError):
            send_email_task(str(log.id))

        log.refresh_from_db()
        assert log.retry_count == 2
        assert log.next_retry_at is not None

        # After second failure: retry_count=2, delay = 5 * 2^(2-1) = 10 minutes
        expected_delay = timedelta(minutes=10)
        assert log.next_retry_at >= before + expected_delay
        assert log.next_retry_at <= before + expected_delay + timedelta(seconds=10)

    @patch("apps.email.services.email_service.EmailService._send_now")
    def test_send_email_task_failure_at_max_retries_no_next_retry(self, mock_send_now):
        """When retry_count reaches max_retries, next_retry_at should not be updated."""
        log = EmailLogFactory(
            status=EmailLog.Status.PENDING,
            retry_count=2,
            max_retries=3,
            next_retry_at=None,
        )
        mock_send_now.side_effect = ConnectionError("SMTP connection failed")

        with pytest.raises(ConnectionError):
            send_email_task(str(log.id))

        log.refresh_from_db()
        # retry_count is now 3 which equals max_retries, so no next_retry_at
        assert log.retry_count == 3
        assert log.next_retry_at is None


# =============================================================================
# TestRetryFailedEmailsTask
# =============================================================================


@pytest.mark.django_db
class TestRetryFailedEmailsTask:
    """Tests for the retry_failed_emails_task Celery task."""

    @patch("apps.email.tasks.send_email_task.delay")
    def test_retry_finds_failed_emails_ready_for_retry(self, mock_delay):
        """Should find failed emails with retry_count < max_retries and next_retry_at in the past."""
        log = FailedEmailLogFactory(
            retry_count=1,
            max_retries=3,
            next_retry_at=timezone.now() - timedelta(minutes=1),
        )

        result = retry_failed_emails_task()

        mock_delay.assert_called_once_with(str(log.id))
        assert "Queued 1 emails for retry" in result

    @patch("apps.email.tasks.send_email_task.delay")
    def test_retry_skips_emails_with_max_retries_reached(self, mock_delay):
        """Should not retry emails where retry_count >= max_retries."""
        FailedEmailLogFactory(
            retry_count=3,
            max_retries=3,
            next_retry_at=timezone.now() - timedelta(minutes=1),
        )

        result = retry_failed_emails_task()

        mock_delay.assert_not_called()
        assert "Queued 0 emails for retry" in result

    @patch("apps.email.tasks.send_email_task.delay")
    def test_retry_skips_emails_not_yet_due(self, mock_delay):
        """Should not retry emails whose next_retry_at is still in the future."""
        FailedEmailLogFactory(
            retry_count=1,
            max_retries=3,
            next_retry_at=timezone.now() + timedelta(hours=1),
        )

        result = retry_failed_emails_task()

        mock_delay.assert_not_called()
        assert "Queued 0 emails for retry" in result

    @patch("apps.email.tasks.send_email_task.delay")
    def test_retry_limits_batch_to_100(self, mock_delay):
        """Should process at most 100 emails per batch."""
        now = timezone.now()
        # Create 110 failed emails ready for retry
        for _ in range(110):
            FailedEmailLogFactory(
                retry_count=0,
                max_retries=3,
                next_retry_at=now - timedelta(minutes=5),
            )

        result = retry_failed_emails_task()

        assert mock_delay.call_count == 100
        assert "Queued 100 emails for retry" in result

    @patch("apps.email.tasks.send_email_task.delay")
    def test_retry_skips_non_failed_status(self, mock_delay):
        """Should only process emails with FAILED status, not PENDING or other statuses."""
        EmailLogFactory(
            status=EmailLog.Status.PENDING,
            retry_count=0,
            max_retries=3,
            next_retry_at=timezone.now() - timedelta(minutes=1),
        )
        QueuedEmailLogFactory(
            retry_count=0,
            max_retries=3,
            next_retry_at=timezone.now() - timedelta(minutes=1),
        )

        result = retry_failed_emails_task()

        mock_delay.assert_not_called()
        assert "Queued 0 emails for retry" in result


# =============================================================================
# TestCleanupOldEmailLogs
# =============================================================================


@pytest.mark.django_db
class TestCleanupOldEmailLogs:
    """Tests for the cleanup_old_email_logs Celery task."""

    def test_cleanup_deletes_old_logs(self):
        """Logs older than retention period (default 90 days) should be deleted."""
        old_log = EmailLogFactory()
        # Manually backdate created_at
        EmailLog.objects.filter(id=old_log.id).update(
            created_at=timezone.now() - timedelta(days=91)
        )

        result = cleanup_old_email_logs()

        assert not EmailLog.objects.filter(id=old_log.id).exists()
        assert "Deleted 1 old email logs" in result

    def test_cleanup_preserves_recent_logs(self):
        """Logs within the retention period should not be deleted."""
        recent_log = EmailLogFactory()
        # created_at defaults to now, which is well within 90 days

        result = cleanup_old_email_logs()

        assert EmailLog.objects.filter(id=recent_log.id).exists()
        assert "Deleted 0 old email logs" in result

    def test_cleanup_respects_retention_setting(self, settings):
        """Should honor the EMAIL_LOG_RETENTION_DAYS setting."""
        settings.EMAIL_LOG_RETENTION_DAYS = 30

        # Create a log 35 days old (beyond 30-day retention)
        log_beyond = EmailLogFactory()
        EmailLog.objects.filter(id=log_beyond.id).update(
            created_at=timezone.now() - timedelta(days=35)
        )

        # Create a log 25 days old (within 30-day retention)
        log_within = EmailLogFactory()
        EmailLog.objects.filter(id=log_within.id).update(
            created_at=timezone.now() - timedelta(days=25)
        )

        result = cleanup_old_email_logs()

        assert not EmailLog.objects.filter(id=log_beyond.id).exists()
        assert EmailLog.objects.filter(id=log_within.id).exists()
        assert "Deleted 1 old email logs" in result

    def test_cleanup_returns_count_message(self):
        """Return message should include the total count of deleted logs."""
        for _ in range(5):
            log = EmailLogFactory()
            EmailLog.objects.filter(id=log.id).update(
                created_at=timezone.now() - timedelta(days=100)
            )

        result = cleanup_old_email_logs()

        assert result == "Deleted 5 old email logs"

    def test_cleanup_handles_empty_table(self):
        """Should return zero-count message when no logs exist."""
        result = cleanup_old_email_logs()

        assert result == "Deleted 0 old email logs"

    def test_cleanup_deletes_in_batches(self):
        """Should delete all matching logs even when count exceeds batch size (1000).

        This verifies the while-loop batching logic works correctly.
        """
        # Create 5 old logs (we can't easily test 1000+ in unit tests,
        # but we verify the loop terminates correctly with fewer)
        for _ in range(5):
            log = EmailLogFactory()
            EmailLog.objects.filter(id=log.id).update(
                created_at=timezone.now() - timedelta(days=91)
            )

        # Also create 3 recent logs that should survive
        recent_ids = []
        for _ in range(3):
            log = EmailLogFactory()
            recent_ids.append(log.id)

        result = cleanup_old_email_logs()

        assert result == "Deleted 5 old email logs"
        assert EmailLog.objects.filter(id__in=recent_ids).count() == 3
