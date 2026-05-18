"""
Email Celery Tasks
==================
Asynchronous tasks for email sending and maintenance.

Tasks:
    - send_email_task: Send a queued email
    - retry_failed_emails_task: Retry failed emails
    - cleanup_old_email_logs: Clean up old logs (daily)
"""

from datetime import timedelta

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.db import models
from django.utils import timezone

from apps.core.observability import get_logger

logger = get_logger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 1 minute
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,  # Max 5 minutes between retries
    soft_time_limit=120,
    time_limit=180,
)
def send_email_task(self, log_id: str, priority: str = "normal"):
    """
    Async task to send an email.

    Args:
        log_id: UUID of the EmailLog
        priority: Priority level (not currently used, for future queue routing)

    Note:
        Uses exponential backoff on failure.
        Max retries configured at task level.
    """
    from apps.email.models import EmailLog
    from apps.email.services.email_service import EmailService

    log = EmailLog.objects.filter(id=log_id).first()
    if not log:
        logger.warning("email.task.not_found", log_id=log_id)
        return

    if log.status not in (EmailLog.Status.PENDING, EmailLog.Status.QUEUED):
        logger.debug("email.task.already_processed", log_id=log_id, status=log.status)
        return

    try:
        EmailService._send_now(log)
        logger.info("email.task.sent", log_id=log_id)

    except Exception:
        # Update retry tracking
        log.refresh_from_db()
        log.retry_count += 1

        if log.retry_count < log.max_retries:
            # Calculate next retry time with exponential backoff
            delay_minutes = 5 * (2 ** (log.retry_count - 1))  # 5, 10, 20 minutes
            log.next_retry_at = timezone.now() + timedelta(minutes=delay_minutes)
            log.save(update_fields=["retry_count", "next_retry_at"])
            logger.warning(
                "email.task.retry_scheduled",
                log_id=log_id,
                retry_count=log.retry_count,
                max_retries=log.max_retries,
                next_retry_at=str(log.next_retry_at),
            )
        else:
            log.save(update_fields=["retry_count"])
            logger.error(
                "email.task.failed_permanently",
                log_id=log_id,
                retry_count=log.retry_count,
            )

        # Re-raise to trigger Celery's retry mechanism
        raise


@shared_task(soft_time_limit=120, time_limit=180)
def retry_failed_emails_task():
    """
    Retry emails that have failed but haven't exceeded max retries.

    This is a safety net for emails that weren't retried by the task retry mechanism.
    Run periodically via Celery Beat.
    """
    from apps.email.models import EmailLog

    # Find failed emails that can be retried and are due
    failed_logs = EmailLog.objects.filter(
        status=EmailLog.Status.FAILED,
        retry_count__lt=models.F("max_retries"),
        next_retry_at__lte=timezone.now(),
    ).values_list("id", flat=True)[
        :100
    ]  # Limit batch size

    count = 0
    for log_id in failed_logs:
        send_email_task.delay(str(log_id))
        count += 1

    if count > 0:
        logger.info("email.task.retry_queued", count=count)

    return f"Queued {count} emails for retry"


@shared_task(soft_time_limit=300, time_limit=600)
def cleanup_old_email_logs():
    """
    Clean up email logs older than retention period.

    Run daily via Celery Beat.
    Default retention: 90 days (configurable via deployment config ``infra.email_log_retention_days``).
    """
    from apps.core.feature_config import feature_config
    from apps.email.models import EmailLog

    retention_days = int(feature_config.get_value("infra.email_log_retention_days", 90))
    cutoff = timezone.now() - timedelta(days=retention_days)

    # Delete in batches to avoid long-running transactions
    total_deleted = 0
    batch_size = 1000

    try:
        while True:
            # Get IDs to delete
            ids_to_delete = list(
                EmailLog.objects.filter(created_at__lt=cutoff).values_list(
                    "id", flat=True
                )[:batch_size]
            )

            if not ids_to_delete:
                break

            deleted, _ = EmailLog.objects.filter(id__in=ids_to_delete).delete()
            total_deleted += deleted

            logger.info("email.task.cleanup_batch", deleted=deleted)
    except SoftTimeLimitExceeded:
        logger.warning(
            "email.task.cleanup_time_limit",
            total_deleted=total_deleted,
            retention_days=retention_days,
        )

    logger.info(
        "email.task.cleanup_complete",
        total_deleted=total_deleted,
        retention_days=retention_days,
    )
    return f"Deleted {total_deleted} old email logs"
