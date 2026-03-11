"""
Notification Tasks
==================
Celery tasks for async notification dispatch.
"""

from celery import shared_task
from django.db import transaction

from apps.core.observability import get_logger

logger = get_logger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True
)
def dispatch_notification_task(self, log_id: str):
    """
    Dispatch notification to all enabled channels with idempotency.

    Uses select_for_update to prevent duplicate dispatches from concurrent workers.
    """
    from apps.notifications.models import NotificationLog
    from apps.notifications.services.channels import get_channel

    # Idempotent dispatch: acquire lock and check status
    with transaction.atomic():
        log = NotificationLog.objects.select_for_update().filter(id=log_id).first()

        if not log:
            logger.warning("notification.task.not_found", log_id=log_id)
            return

        # Only process if pending (idempotency check)
        if log.status != NotificationLog.Status.PENDING:
            logger.info(
                "notification.task.skipped",
                log_id=log_id,
                status=log.status,
                reason='Already processed',
            )
            return

        # Mark as processing to prevent concurrent dispatch
        log.status = NotificationLog.Status.PROCESSING
        log.save(update_fields=['status'])

    # Dispatch to channels (outside lock - don't hold during I/O)
    channel_results = log.channel_results or {}

    for channel_name in log.channels:
        # Skip already successful channels (for partial retry)
        if channel_results.get(channel_name, {}).get('status') == 'sent':
            continue

        channel = get_channel(channel_name)
        if channel:
            result = channel.send(
                user=log.user,
                notification_type=log.notification_type,
                context=log.context
            )
            channel_results[channel_name] = result

            status_label = 'sent' if result.get('status') == 'sent' else 'result'
            logger.info(
                f"notification.channel.{status_label}",
                log_id=str(log.id),
                channel=channel_name,
                status=result.get('status'),
            )

    # Determine final status
    statuses = [r.get('status') for r in channel_results.values()]

    # Consider 'skipped' as successful (channel not available)
    effective_statuses = [s for s in statuses if s != 'skipped']

    if not effective_statuses:
        # All channels skipped
        final_status = NotificationLog.Status.SENT
    elif all(s == 'sent' for s in effective_statuses):
        final_status = NotificationLog.Status.SENT
    elif any(s == 'sent' for s in effective_statuses):
        final_status = NotificationLog.Status.PARTIAL
    else:
        final_status = NotificationLog.Status.FAILED

    # Update log
    log.channel_results = channel_results
    log.status = final_status
    log.save(update_fields=['channel_results', 'status'])

    logger.info(
        "notification.dispatched",
        log_id=str(log.id),
        final_status=final_status,
        channels=list(channel_results.keys()),
    )

    # Schedule retry for partial failures
    if final_status == NotificationLog.Status.PARTIAL:
        retry_partial_notification_task.apply_async(
            args=[str(log.id)],
            countdown=300  # 5 minutes
        )


@shared_task(bind=True, max_retries=2)
def retry_partial_notification_task(self, log_id: str):
    """
    Retry only failed channels for a partial notification.
    """
    from apps.notifications.models import NotificationLog
    from apps.notifications.services.channels import get_channel

    with transaction.atomic():
        log = NotificationLog.objects.select_for_update().filter(id=log_id).first()

        if not log or log.status != NotificationLog.Status.PARTIAL:
            return

        # Prevent concurrent retry
        log.status = NotificationLog.Status.RETRYING
        log.retry_count = log.retry_count + 1
        log.save(update_fields=['status', 'retry_count'])

    channel_results = log.channel_results or {}

    # Only retry failed channels
    for channel_name in log.channels:
        prev_result = channel_results.get(channel_name, {})
        if prev_result.get('status') in ('sent', 'skipped'):
            continue  # Already succeeded or skipped

        channel = get_channel(channel_name)
        if channel:
            result = channel.send(
                user=log.user,
                notification_type=log.notification_type,
                context=log.context
            )
            channel_results[channel_name] = result

            logger.info(
                "notification.retry.channel",
                log_id=str(log.id),
                channel=channel_name,
                status=result.get('status'),
                retry_count=log.retry_count,
            )

    # Update final status
    statuses = [r.get('status') for r in channel_results.values()]
    effective_statuses = [s for s in statuses if s != 'skipped']

    if not effective_statuses or all(s == 'sent' for s in effective_statuses):
        final_status = NotificationLog.Status.SENT
    elif any(s == 'sent' for s in effective_statuses):
        final_status = NotificationLog.Status.PARTIAL  # Still partial
    else:
        final_status = NotificationLog.Status.FAILED

    log.channel_results = channel_results
    log.status = final_status
    log.save(update_fields=['channel_results', 'status'])

    logger.info(
        "notification.retry.complete",
        log_id=str(log.id),
        final_status=final_status,
        retry_count=log.retry_count,
    )


@shared_task
def cleanup_old_notification_logs():
    """
    Delete notification logs older than retention period.
    """
    from datetime import timedelta

    from django.conf import settings
    from django.utils import timezone

    from apps.notifications.models import NotificationLog

    retention_days = getattr(settings, 'NOTIFICATION_LOG_RETENTION_DAYS', 90)
    cutoff = timezone.now() - timedelta(days=retention_days)

    deleted_count, _ = NotificationLog.objects.filter(
        created_at__lt=cutoff
    ).delete()

    logger.info(
        "notification.cleanup.complete",
        deleted_count=deleted_count,
        retention_days=retention_days,
    )

    return deleted_count
