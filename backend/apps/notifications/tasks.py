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
    retry_backoff=True,
    soft_time_limit=120,
    time_limit=180,
)
def dispatch_notification_task(self, log_id: str):
    """
    Dispatch notification to all enabled channels with idempotency.

    Uses select_for_update to prevent duplicate dispatches from concurrent workers.
    """
    from apps.core.feature_config import feature_config
    from apps.notifications.models import NotificationLog
    from apps.notifications.services.channels import get_channel

    if not feature_config.is_system_enabled("notifications"):
        logger.info("notification.task.dispatch.skipped", reason="system_disabled")
        return

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
                reason="Already processed",
            )
            return

        # Mark as processing to prevent concurrent dispatch
        log.status = NotificationLog.Status.PROCESSING
        log.save(update_fields=["status"])

    # Dispatch to channels (outside lock - don't hold during I/O)
    channel_results = log.channel_results or {}

    for channel_name in log.channels:
        # Skip already successful channels (for partial retry)
        if channel_results.get(channel_name, {}).get("status") == "sent":
            continue

        channel = get_channel(channel_name)
        if channel:
            try:
                result = channel.send(
                    user=log.user,
                    notification_type=log.notification_type,
                    context=log.context,
                )
            except Exception as e:
                logger.error(
                    "notification.dispatch.channel.error",
                    log_id=str(log.id),
                    channel=channel_name,
                    error=str(e),
                )
                result = {"status": "failed", "error": str(e)}
            channel_results[channel_name] = result

            status_label = "sent" if result.get("status") == "sent" else "failed"
            logger.info(
                f"notification.channel.{status_label}",
                log_id=str(log.id),
                channel=channel_name,
                status=result.get("status"),
            )

    # Determine final status (shared helper filters "skipped" channels)
    from apps.notifications.services.notification_service import _resolve_final_status

    final_status = _resolve_final_status(channel_results)

    # Update log
    log.channel_results = channel_results
    log.status = final_status
    log.save(update_fields=["channel_results", "status"])

    logger.info(
        "notification.dispatched",
        log_id=str(log.id),
        final_status=final_status,
        channels=list(channel_results.keys()),
    )

    # Schedule retry for partial failures
    if final_status == NotificationLog.Status.PARTIAL:
        retry_partial_notification_task.apply_async(
            args=[str(log.id)], countdown=300  # 5 minutes
        )


@shared_task(bind=True, max_retries=2, soft_time_limit=120, time_limit=180)
def retry_partial_notification_task(self, log_id: str):
    """
    Retry only failed channels for a partial notification.
    """
    from apps.core.feature_config import feature_config
    from apps.notifications.models import NotificationLog
    from apps.notifications.services.channels import get_channel

    if not feature_config.is_system_enabled("notifications"):
        logger.info("notification.task.retry.skipped", reason="system_disabled")
        return

    with transaction.atomic():
        log = NotificationLog.objects.select_for_update().filter(id=log_id).first()

        if not log or log.status != NotificationLog.Status.PARTIAL:
            return

        # Prevent concurrent retry
        log.status = NotificationLog.Status.RETRYING
        log.retry_count = log.retry_count + 1
        log.save(update_fields=["status", "retry_count"])

    channel_results = log.channel_results or {}

    # Only retry failed channels
    for channel_name in log.channels:
        prev_result = channel_results.get(channel_name, {})
        if prev_result.get("status") in ("sent", "skipped"):
            continue  # Already succeeded or skipped

        channel = get_channel(channel_name)
        if channel:
            try:
                result = channel.send(
                    user=log.user,
                    notification_type=log.notification_type,
                    context=log.context,
                )
            except Exception as e:
                logger.error(
                    "notification.retry.channel.error",
                    log_id=str(log.id),
                    channel=channel_name,
                    error=str(e),
                    retry_count=log.retry_count,
                )
                result = {"status": "failed", "error": str(e)}
            channel_results[channel_name] = result

            logger.info(
                "notification.retry.channel",
                log_id=str(log.id),
                channel=channel_name,
                status=result.get("status"),
                retry_count=log.retry_count,
            )

    # Determine final status (shared helper filters "skipped" channels)
    from apps.notifications.services.notification_service import _resolve_final_status

    final_status = _resolve_final_status(channel_results)

    log.channel_results = channel_results
    log.status = final_status
    log.save(update_fields=["channel_results", "status"])

    logger.info(
        "notification.retry.complete",
        log_id=str(log.id),
        final_status=final_status,
        retry_count=log.retry_count,
    )


@shared_task(soft_time_limit=240, time_limit=300)
def cleanup_old_notification_logs():
    """
    Delete notification logs older than retention period.
    """
    from datetime import timedelta

    from django.utils import timezone

    from apps.core.feature_config import feature_config
    from apps.notifications.models import NotificationLog

    if not feature_config.is_system_enabled("notifications"):
        logger.info("notification.task.cleanup.skipped", reason="system_disabled")
        return 0

    retention_days = feature_config.get_value("notifications.log_retention_days", 90)
    cutoff = timezone.now() - timedelta(days=retention_days)

    deleted_count, _ = NotificationLog.objects.filter(created_at__lt=cutoff).delete()

    logger.info(
        "notification.cleanup.complete",
        deleted_count=deleted_count,
        retention_days=retention_days,
    )

    return deleted_count
