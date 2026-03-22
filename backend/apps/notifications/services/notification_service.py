"""
Notification Service
====================
Main service for sending notifications through multiple channels.
"""

from typing import Any, Callable, Dict, List

from django.db import transaction

from apps.core.exceptions import NotFound, ValidationError
from apps.core.observability import get_logger
from apps.notifications.models import NotificationLog
from apps.notifications.services.preference_service import PreferenceService
from apps.notifications.types import NotificationTypeConfig, get_notification_type

logger = get_logger(__name__)


class NotificationService:
    """
    Main notification service.

    Usage:
        NotificationService.send(
            user=user,
            notification_type='welcome',
            context={'user_name': user.profile.first_name}
        )
    """

    @staticmethod
    def send(
        *,
        user,
        notification_type: str,
        context: Dict[str, Any],
        force_channels: List[str] | None = None,
        async_dispatch: bool = True,
    ) -> NotificationLog:
        """
        Send a notification to a user.

        Args:
            user: User instance
            notification_type: Name from NOTIFICATION_TYPES
            context: Template variables
            force_channels: Override user preferences (for critical notifications)
            async_dispatch: Send asynchronously via Celery (default True)

        Returns:
            NotificationLog record

        Raises:
            NotFound: Unknown notification type
            ValidationError: Type is disabled or missing required context
        """
        # Get notification type config
        type_config = get_notification_type(notification_type)
        if not type_config:
            raise NotFound(
                message=f"Unknown notification type: {notification_type}",
                resource="NotificationType",
            )

        if not type_config.enabled:
            raise ValidationError(
                message=f"Notification type '{notification_type}' is disabled"
            )

        # Validate required context keys
        NotificationService._validate_context(type_config, context)

        # Determine channels to use
        if force_channels:
            channels = force_channels
        else:
            channels = PreferenceService.get_enabled_channels(
                user=user, notification_type=notification_type
            )

        if not channels:
            # User has disabled all channels for this type
            log = NotificationLog.objects.create(
                user=user,
                notification_type=notification_type,
                channels=[],
                context=context,
                status=NotificationLog.Status.SENT,
                channel_results={"note": "No channels enabled"},
            )
            logger.info(
                "notification.skipped",
                log_id=str(log.id),
                type=notification_type,
                user_id=str(user.id),
                reason="No channels enabled",
            )
            return log

        # Create log entry
        log = NotificationLog.objects.create(
            user=user,
            notification_type=notification_type,
            channels=channels,
            context=context,
            status=NotificationLog.Status.PENDING,
        )

        logger.info(
            "notification.triggered",
            log_id=str(log.id),
            type=notification_type,
            user_id=str(user.id),
            channels=channels,
        )

        # Dispatch to channels
        if async_dispatch:
            from apps.notifications.tasks import dispatch_notification_task

            dispatch_notification_task.delay(str(log.id))
        else:
            NotificationService._dispatch_now(log)

        return log

    @staticmethod
    def send_bulk(
        *,
        users: List,
        notification_type: str,
        context_fn: Callable,  # Callable[[User], Dict] - generates context per user
        force_channels: List[str] | None = None,
    ) -> List[NotificationLog]:
        """
        Send notification to multiple users.

        Args:
            users: List of User instances
            notification_type: Notification type name
            context_fn: Function that takes user and returns context dict
            force_channels: Override preferences
        """
        logs = []
        for user in users:
            try:
                context = context_fn(user)
                log = NotificationService.send(
                    user=user,
                    notification_type=notification_type,
                    context=context,
                    force_channels=force_channels,
                )
                logs.append(log)
            except Exception as e:
                logger.error(
                    "notification.bulk.failed",
                    user_id=str(user.id),
                    type=notification_type,
                    error=str(e),
                )

        return logs

    @staticmethod
    def _validate_context(
        type_config: NotificationTypeConfig, context: Dict[str, Any]
    ) -> None:
        """
        Validate context has all required keys for notification type.

        Raises:
            ValidationError: If required context key is missing
        """
        missing = [key for key in type_config.required_context if key not in context]

        if missing:
            raise ValidationError(
                message=f"Missing required context for '{type_config.name}': {', '.join(missing)}",
                field="context",
            )

    @staticmethod
    def _dispatch_now(log: NotificationLog) -> None:
        """
        Dispatch notification to all channels synchronously.
        Used for sync dispatch or testing.
        """
        from apps.notifications.services.channels import get_channel

        # Idempotent dispatch: acquire lock and check status
        with transaction.atomic():
            locked_log = (
                NotificationLog.objects.select_for_update().filter(id=log.id).first()
            )

            if not locked_log:
                return

            # Only process if pending (idempotency check)
            if locked_log.status != NotificationLog.Status.PENDING:
                return

            # Mark as processing to prevent concurrent dispatch
            locked_log.status = NotificationLog.Status.PROCESSING
            locked_log.save(update_fields=["status"])

        # Dispatch to channels (outside lock - don't hold during I/O)
        channel_results = locked_log.channel_results or {}

        for channel_name in locked_log.channels:
            # Skip already successful channels (for partial retry)
            if channel_results.get(channel_name, {}).get("status") == "sent":
                continue

            channel = get_channel(channel_name)
            if channel:
                result = channel.send(
                    user=locked_log.user,
                    notification_type=locked_log.notification_type,
                    context=locked_log.context,
                )
                channel_results[channel_name] = result

                status_label = "sent" if result.get("status") == "sent" else "failed"
                logger.info(
                    f"notification.channel.{status_label}",
                    log_id=str(locked_log.id),
                    channel=channel_name,
                    result_status=result.get("status"),
                )

        # Determine final status
        statuses = [r.get("status") for r in channel_results.values()]
        if all(s == "sent" for s in statuses):
            final_status = NotificationLog.Status.SENT
        elif any(s == "sent" for s in statuses):
            final_status = NotificationLog.Status.PARTIAL
        else:
            final_status = NotificationLog.Status.FAILED

        # Update log
        locked_log.channel_results = channel_results
        locked_log.status = final_status
        locked_log.save(update_fields=["channel_results", "status"])
