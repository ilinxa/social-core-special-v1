from celery import shared_task
from django.utils import timezone

from apps.core.observability import get_logger
from apps.core.observability.logging.celery import LoggedTask
from apps.transaction.selectors import TransactionSelector

logger = get_logger(__name__)


@shared_task(base=LoggedTask, soft_time_limit=240, time_limit=300)
def expire_transactions_task():
    """Hourly: expire transactions past their expiration date."""
    from apps.core.feature_config import feature_config

    if not feature_config.is_system_enabled("transaction"):
        logger.info("task.expire.skipped", reason="system_disabled")
        return

    expired = TransactionSelector.list_expired_needing_update()
    count = 0
    for txn in expired:
        from apps.transaction.services import TransactionService

        try:
            TransactionService.expire(transaction_id=txn.id)
            count += 1
        except Exception as e:
            logger.error(
                "task.expire.failed",
                transaction_id=str(txn.id),
                error=str(e),
            )
    logger.info("task.expire.complete", count=count)


@shared_task(
    bind=True, base=LoggedTask, max_retries=3, soft_time_limit=120, time_limit=180
)
def retry_outcome_execution_task(self, transaction_id: str):
    """Retry failed outcome execution with exponential backoff."""
    from apps.core.feature_config import feature_config

    if not feature_config.is_system_enabled("transaction"):
        logger.info("task.retry_outcome.skipped", reason="system_disabled")
        return

    from uuid import UUID

    from apps.core.types import ActorContext
    from apps.transaction.services import TransactionService

    try:
        txn = TransactionSelector.get_by_id(transaction_id=UUID(transaction_id))
        if txn.outcome_executed:
            return
        TransactionService._execute_outcome(
            transaction=txn,
            actor_context=ActorContext.for_system(),
        )
    except Exception as exc:
        logger.error(
            "task.retry_outcome.failed",
            transaction_id=transaction_id,
            error=str(exc),
        )
        raise self.retry(exc=exc, countdown=300)


@shared_task(base=LoggedTask, soft_time_limit=240, time_limit=300)
def cleanup_old_transaction_logs_task(retention_days: int = 90):
    """Daily: delete logs for terminal transactions older than retention."""
    from apps.core.feature_config import feature_config

    if not feature_config.is_system_enabled("transaction"):
        logger.info("task.cleanup.skipped", reason="system_disabled")
        return

    from datetime import timedelta

    from apps.transaction.constants import TERMINAL_STATES
    from apps.transaction.models import TransactionLog

    cutoff = timezone.now() - timedelta(days=retention_days)
    deleted, _ = TransactionLog.objects.filter(
        timestamp__lt=cutoff,
        transaction__status__in=list(TERMINAL_STATES),
    ).delete()
    logger.info("task.cleanup.complete", deleted=deleted)


@shared_task(base=LoggedTask, soft_time_limit=240, time_limit=300)
def send_expiration_reminder_task():
    """Daily: remind targets about transactions expiring in 24-48 hours."""
    from apps.core.feature_config import feature_config

    if not feature_config.is_system_enabled("transaction"):
        logger.info("task.reminder.skipped", reason="system_disabled")
        return

    from datetime import timedelta

    from django.contrib.auth import get_user_model

    from apps.transaction.models import Transaction

    User = get_user_model()

    reminder_hours = feature_config.get_value(
        "transaction.expiration_reminder_hours", 48
    )
    now = timezone.now()
    expiring = Transaction.objects.filter(
        expires_at__gte=now + timedelta(hours=max(1, reminder_hours // 2)),
        expires_at__lt=now + timedelta(hours=reminder_hours),
        status="pending",
    )

    try:
        from apps.notifications.services import NotificationService
    except ImportError:
        return

    count = 0
    for txn in expiring:
        if txn.mode == "invitation" and txn.target_type == "user":
            target = User.objects.filter(id=txn.target_id).first()
            if target:
                NotificationService.send(
                    user=target,
                    notification_type="transaction_expiring_soon",
                    context={
                        "transaction_id": str(txn.id),
                        "expires_at": txn.expires_at.isoformat(),
                    },
                    scope_type=txn.context_type,
                    scope_id=txn.context_id,
                )
                count += 1
    logger.info("task.reminder.complete", count=count)
