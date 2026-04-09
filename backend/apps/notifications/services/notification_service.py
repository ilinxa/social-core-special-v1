"""
Notification Service
====================
Main service for sending notifications through multiple channels.
"""

from typing import Any, Callable, Dict, List
from uuid import UUID

from django.db import transaction

from apps.core.exceptions import NotFound, ValidationError
from apps.core.feature_config import feature_config
from apps.core.observability import get_logger
from apps.notifications.models import NotificationLog
from apps.notifications.services.preference_service import PreferenceService
from apps.notifications.types import NotificationTypeConfig, get_notification_type

logger = get_logger(__name__)


def _resolve_final_status(channel_results: dict) -> str:
    """
    Determine final notification status from per-channel results.

    Shared by _dispatch_now(), dispatch_notification_task(), and
    retry_partial_notification_task() to ensure consistent behavior.

    Rules:
    - "skipped" channels are excluded (channel not available/configured)
    - If no effective results (all skipped or empty): SENT
    - If all effective channels sent: SENT
    - If some sent, some failed: PARTIAL
    - If none sent: FAILED
    """
    statuses = [r.get("status") for r in channel_results.values()]
    effective = [s for s in statuses if s != "skipped"]
    if not effective or all(s == "sent" for s in effective):
        return NotificationLog.Status.SENT
    elif any(s == "sent" for s in effective):
        return NotificationLog.Status.PARTIAL
    return NotificationLog.Status.FAILED


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
        scope_type: str = "user",
        scope_id: UUID | None = None,
    ) -> NotificationLog:
        """
        Send a notification to a specific user (direct-target mode).

        Args:
            user: User instance
            notification_type: Name from NOTIFICATION_TYPES
            context: Template variables
            force_channels: Override user preferences (for critical notifications)
            async_dispatch: Send asynchronously via Celery (default True)
            scope_type: Isolation scope ('user', 'business', 'platform')
            scope_id: Org UUID (required when scope_type != 'user')

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

        # Validate scope
        if scope_type != "user" and scope_id is None:
            raise ValidationError(
                message=f"scope_id required for scope_type '{scope_type}'"
            )

        # Feature gate: skip non-critical notifications when feature disabled.
        # Mandatory types (verify_email, password_reset, etc.) always pass —
        # only blocked by System Gate, never by Feature Gate.
        if type_config.user_configurable:
            if not feature_config.is_feature_enabled("user.notifications.enabled"):
                logger.info(
                    "notification.send.skipped",
                    type=notification_type,
                    reason="feature_disabled",
                )
                return None

        # Determine channels to use
        if force_channels:
            channels = force_channels
        else:
            channels = PreferenceService.get_enabled_channels(
                user=user,
                notification_type=notification_type,
                scope_type=scope_type,
                scope_id=scope_id,
            )

        # Deployment-level channel filter (config overrides user preference)
        _channel_config = {
            "email": feature_config.get_value("notifications.email_enabled", True),
            "push": feature_config.get_value("notifications.push_enabled", False),
            "sms": feature_config.get_value("notifications.sms_enabled", False),
        }
        channels = [ch for ch in channels if _channel_config.get(ch, True)]

        if not channels:
            # User has disabled all channels for this type
            log = NotificationLog.objects.create(
                user=user,
                notification_type=notification_type,
                channels=[],
                context=context,
                status=NotificationLog.Status.SENT,
                channel_results={"note": "No channels enabled"},
                scope_type=scope_type,
                scope_id=scope_id,
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
            scope_type=scope_type,
            scope_id=scope_id,
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
    def send_to_org(
        *,
        scope_type: str,
        scope_id: UUID,
        notification_type: str,
        context: Dict[str, Any],
        recipient_permissions: List[str] | None = None,
        force_channels: List[str] | None = None,
        async_dispatch: bool = True,
        exclude_user_ids: List[UUID] | None = None,
    ) -> List[NotificationLog]:
        """
        Send notification to org members with matching permissions + owner.

        Permission resolution:
        1. If recipient_permissions provided → use it (caller override)
        2. Else → use type_config.default_recipient_permissions (code config)
        3. If neither → raise ValidationError

        Args:
            scope_type: 'business' or 'platform'
            scope_id: Org UUID
            notification_type: Name from NOTIFICATION_TYPES
            context: Template variables
            recipient_permissions: Override type config default permissions
            force_channels: Override user preferences
            async_dispatch: Send asynchronously via Celery (default True)
            exclude_user_ids: Skip specific users (e.g., the actor)

        Returns:
            List of NotificationLog records (one per recipient)
        """
        # Feature gate: skip when notifications feature is disabled
        if not feature_config.is_feature_enabled("user.notifications.enabled"):
            logger.info(
                "notification.send_to_org.skipped",
                type=notification_type,
                reason="feature_disabled",
            )
            return []

        type_config = get_notification_type(notification_type)
        if not type_config:
            raise NotFound(
                message=f"Unknown notification type: {notification_type}",
                resource="NotificationType",
            )

        # Resolve permissions: caller override > type config default
        perms = recipient_permissions or type_config.default_recipient_permissions
        if not perms:
            raise ValidationError(
                message=(
                    f"Notification type '{notification_type}' has no "
                    f"recipient_permissions configured and none were provided"
                )
            )

        if scope_type == "user":
            raise ValidationError(
                message="send_to_org() requires business or platform scope"
            )

        # Resolve recipients: members with ANY of the permissions + owner
        from apps.rbac.selectors import MembershipSelector

        recipients = set()
        for perm_code in perms:
            users = MembershipSelector.get_users_with_permission(
                account_type=scope_type,
                account_id=scope_id,
                permission_code=perm_code,
            )
            recipients.update(u.id for u in users)

        # Owner always gets notified
        owner_membership = MembershipSelector.get_owner_membership(
            account_type=scope_type, account_id=scope_id
        )
        if owner_membership:
            recipients.add(owner_membership.user_id)

        # Exclude specific users if requested
        if exclude_user_ids:
            recipients -= set(exclude_user_ids)

        if not recipients:
            logger.info(
                "notification.send_to_org.no_recipients",
                type=notification_type,
                scope_type=scope_type,
                scope_id=str(scope_id),
            )
            return []

        # Send to each recipient
        from django.contrib.auth import get_user_model

        User = get_user_model()
        users = User.objects.filter(id__in=recipients, is_active=True)

        logs = []
        for user in users:
            try:
                log = NotificationService.send(
                    user=user,
                    notification_type=notification_type,
                    context=context,
                    scope_type=scope_type,
                    scope_id=scope_id,
                    force_channels=force_channels,
                    async_dispatch=async_dispatch,
                )
                logs.append(log)
            except Exception as e:
                logger.error(
                    "notification.send_to_org.failed",
                    user_id=str(user.id),
                    type=notification_type,
                    error=str(e),
                )

        logger.info(
            "notification.send_to_org.complete",
            type=notification_type,
            scope_type=scope_type,
            scope_id=str(scope_id),
            recipient_count=len(logs),
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
                    error=result.get("error", ""),
                )

        # Determine final status (shared helper filters "skipped" channels)
        final_status = _resolve_final_status(channel_results)

        # Update log
        locked_log.channel_results = channel_results
        locked_log.status = final_status
        locked_log.save(update_fields=["channel_results", "status"])
