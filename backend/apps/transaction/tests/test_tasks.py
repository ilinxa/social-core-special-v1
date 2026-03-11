import pytest
from uuid import uuid4
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.utils import timezone

from apps.core.constants import ContextType
from apps.transaction.tasks import (
    expire_transactions_task,
    retry_outcome_execution_task,
    cleanup_old_transaction_logs_task,
    send_expiration_reminder_task,
)
from apps.transaction.models import Transaction, TransactionLog
from apps.transaction.tests.factories import (
    TransactionFactory,
    TransactionLogFactory,
)
from apps.transaction.constants import TransactionStatus, TransactionMode, PartyType


# =========================================================================
# EXPIRE TRANSACTIONS TASK
# =========================================================================

@pytest.mark.django_db
class TestExpireTransactionsTask:

    def test_expires_overdue_transactions(self):
        txn = TransactionFactory(
            status=TransactionStatus.PENDING,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        expire_transactions_task()
        txn.refresh_from_db()
        assert txn.status == TransactionStatus.EXPIRED

    def test_skips_terminal_transactions(self):
        txn = TransactionFactory(
            status=TransactionStatus.ACCEPTED,
            expires_at=timezone.now() - timedelta(hours=1),
            resolved_at=timezone.now() - timedelta(hours=1),
        )
        expire_transactions_task()
        txn.refresh_from_db()
        assert txn.status == TransactionStatus.ACCEPTED

    def test_skips_not_yet_expired(self):
        txn = TransactionFactory(
            status=TransactionStatus.PENDING,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        expire_transactions_task()
        txn.refresh_from_db()
        assert txn.status == TransactionStatus.PENDING


# =========================================================================
# RETRY OUTCOME EXECUTION TASK
# =========================================================================

@pytest.mark.django_db
class TestRetryOutcomeExecutionTask:

    def test_skips_already_executed(self):
        txn = TransactionFactory(
            status=TransactionStatus.ACCEPTED,
            outcome_executed=True,
            resolved_at=timezone.now(),
        )
        # Should not raise or change anything
        retry_outcome_execution_task(str(txn.id))
        txn.refresh_from_db()
        assert txn.outcome_executed is True

    def test_retries_failed_outcome(self):
        from apps.users.tests.factories import UserFactory
        user_a = UserFactory()
        user_b = UserFactory()
        txn = TransactionFactory(
            transaction_type="user_connection_request",
            status=TransactionStatus.ACCEPTED,
            outcome_executed=False,
            context_type=ContextType.USER,
            context_id=None,
            resolved_at=timezone.now(),
            initiator_id=user_a.id,
            target_id=user_b.id,
        )
        from apps.transaction.outcome_handlers import register_all_handlers
        register_all_handlers()

        retry_outcome_execution_task(str(txn.id))
        txn.refresh_from_db()
        assert txn.outcome_executed is True


# =========================================================================
# CLEANUP OLD TRANSACTION LOGS TASK
# =========================================================================

@pytest.mark.django_db
class TestCleanupOldTransactionLogsTask:

    def test_deletes_old_logs_for_terminal_transactions(self):
        txn = TransactionFactory(
            status=TransactionStatus.ACCEPTED,
            resolved_at=timezone.now() - timedelta(days=100),
        )
        log = TransactionLogFactory(transaction=txn)
        # Backdate the log
        TransactionLog.objects.filter(id=log.id).update(
            timestamp=timezone.now() - timedelta(days=100),
        )

        cleanup_old_transaction_logs_task(retention_days=90)
        assert TransactionLog.objects.filter(id=log.id).count() == 0

    def test_preserves_recent_logs(self):
        txn = TransactionFactory(
            status=TransactionStatus.ACCEPTED,
            resolved_at=timezone.now(),
        )
        log = TransactionLogFactory(transaction=txn)

        cleanup_old_transaction_logs_task(retention_days=90)
        assert TransactionLog.objects.filter(id=log.id).count() == 1

    def test_preserves_logs_for_active_transactions(self):
        txn = TransactionFactory(status=TransactionStatus.PENDING)
        log = TransactionLogFactory(transaction=txn)
        TransactionLog.objects.filter(id=log.id).update(
            timestamp=timezone.now() - timedelta(days=100),
        )

        cleanup_old_transaction_logs_task(retention_days=90)
        assert TransactionLog.objects.filter(id=log.id).count() == 1


# =========================================================================
# SEND EXPIRATION REMINDER TASK
# =========================================================================

@pytest.mark.django_db
class TestSendExpirationReminderTask:

    @patch("apps.notifications.services.NotificationService.send")
    def test_sends_reminders_for_expiring_invitations(self, mock_send):
        from apps.users.tests.factories import UserFactory
        target = UserFactory()

        TransactionFactory(
            mode=TransactionMode.INVITATION,
            status=TransactionStatus.PENDING,
            target_type=PartyType.USER,
            target_id=target.id,
            expires_at=timezone.now() + timedelta(hours=36),
        )

        send_expiration_reminder_task()
        mock_send.assert_called_once()

    def test_skips_non_invitations(self):
        TransactionFactory(
            mode=TransactionMode.REQUEST,
            status=TransactionStatus.PENDING,
            target_type=PartyType.ACCOUNT,
            expires_at=timezone.now() + timedelta(hours=36),
        )
        # Should not raise (no notification service needed)
        send_expiration_reminder_task()

    @patch.dict("sys.modules", {"apps.notifications.services": None})
    def test_graceful_without_notification_module(self):
        TransactionFactory(
            mode=TransactionMode.INVITATION,
            status=TransactionStatus.PENDING,
            target_type=PartyType.USER,
            target_id=uuid4(),
            expires_at=timezone.now() + timedelta(hours=36),
        )
        # Should not raise — ImportError is caught
        send_expiration_reminder_task()
