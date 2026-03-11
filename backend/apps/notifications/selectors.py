"""
Notification Selectors
======================
Read-only queries for notifications.
"""

from typing import Dict, List, Optional
from uuid import UUID

from django.db.models import QuerySet

from apps.notifications.models import NotificationLog, NotificationPreference
from apps.notifications.types import get_notification_type, get_all_types


class NotificationLogSelector:
    """
    Read-only queries for notification logs.
    """

    @staticmethod
    def get_by_id(log_id: UUID) -> Optional[NotificationLog]:
        """Get notification log by ID."""
        return NotificationLog.objects.filter(id=log_id).first()

    @staticmethod
    def get_user_history(
        *,
        user,
        notification_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> QuerySet[NotificationLog]:
        """
        Get notification history for a user.

        Args:
            user: User instance
            notification_type: Filter by type (optional)
            status: Filter by status (optional)
            limit: Max records to return

        Returns:
            QuerySet of NotificationLog ordered by created_at desc
        """
        qs = NotificationLog.objects.filter(user=user)

        if notification_type:
            qs = qs.filter(notification_type=notification_type)

        if status:
            qs = qs.filter(status=status)

        return qs.order_by('-created_at')[:limit]

    @staticmethod
    def get_pending_count(*, user) -> int:
        """Get count of pending notifications for a user."""
        return NotificationLog.objects.filter(
            user=user,
            status=NotificationLog.Status.PENDING
        ).count()

    @staticmethod
    def get_failed_logs(*, limit: int = 100) -> QuerySet[NotificationLog]:
        """Get recent failed notification logs for monitoring."""
        return NotificationLog.objects.filter(
            status=NotificationLog.Status.FAILED
        ).order_by('-created_at')[:limit]

    @staticmethod
    def get_partial_logs(*, limit: int = 100) -> QuerySet[NotificationLog]:
        """Get partial notification logs needing retry."""
        return NotificationLog.objects.filter(
            status=NotificationLog.Status.PARTIAL
        ).order_by('-created_at')[:limit]


class NotificationPreferenceSelector:
    """
    Read-only queries for notification preferences.
    """

    @staticmethod
    def get_user_preferences(*, user) -> Dict[str, Dict]:
        """
        Get all preferences for a user as a dict.

        Returns dict keyed by notification_type with channel states.
        """
        # Get user's stored preferences
        stored = {
            p.notification_type: p
            for p in NotificationPreference.objects.filter(user=user)
        }

        result = {}
        for type_config in get_all_types():
            if type_config.name in stored:
                pref = stored[type_config.name]
                channels = pref.get_enabled_channels()
            else:
                channels = [c.value for c in type_config.default_channels]

            result[type_config.name] = {
                'display_name': type_config.display_name,
                'description': type_config.description,
                'category': type_config.category.value,
                'user_configurable': type_config.user_configurable,
                'email_enabled': 'email' in channels,
                'push_enabled': 'push' in channels,
                'sms_enabled': 'sms' in channels,
            }

        return result

    @staticmethod
    def get_users_with_channel_enabled(
        *,
        notification_type: str,
        channel: str
    ) -> List:
        """
        Get users who have a specific channel enabled for a notification type.

        Useful for bulk notifications.
        """
        type_config = get_notification_type(notification_type)
        if not type_config:
            return []

        # Get users with explicit preferences
        if channel == 'email':
            disabled_users = NotificationPreference.objects.filter(
                notification_type=notification_type,
                email_enabled=False
            ).values_list('user_id', flat=True)
        elif channel == 'push':
            disabled_users = NotificationPreference.objects.filter(
                notification_type=notification_type,
                push_enabled=False
            ).values_list('user_id', flat=True)
        elif channel == 'sms':
            disabled_users = NotificationPreference.objects.filter(
                notification_type=notification_type,
                sms_enabled=False
            ).values_list('user_id', flat=True)
        else:
            return []

        # Check if channel is in defaults
        from apps.notifications.types import Channel
        channel_enum = Channel(channel)
        is_default_enabled = channel_enum in type_config.default_channels

        if is_default_enabled:
            # Return all users except those who explicitly disabled
            from django.contrib.auth import get_user_model
            User = get_user_model()
            return list(
                User.objects.filter(is_active=True)
                .exclude(id__in=disabled_users)
            )
        else:
            # Return only users who explicitly enabled
            enabled_users = NotificationPreference.objects.filter(
                notification_type=notification_type,
                **{f'{channel}_enabled': True}
            ).values_list('user_id', flat=True)

            from django.contrib.auth import get_user_model
            User = get_user_model()
            return list(
                User.objects.filter(id__in=enabled_users, is_active=True)
            )
