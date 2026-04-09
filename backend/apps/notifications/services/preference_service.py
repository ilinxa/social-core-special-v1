"""
Preference Service
==================
Manage user notification preferences.
"""

from typing import Dict, List

from django.http import HttpRequest

from apps.core.exceptions import NotFound, ValidationError
from apps.core.observability import get_logger
from apps.core.observability.audit import AuditLog, AuditService
from apps.notifications.models import NotificationPreference
from apps.notifications.types import (
    Channel,
    get_configurable_types,
    get_notification_type,
)

logger = get_logger(__name__)


class PreferenceService:
    """
    Manage user notification preferences.
    """

    @staticmethod
    def get_enabled_channels(
        *,
        user,
        notification_type: str,
        scope_type: str = "user",
        scope_id=None,
    ) -> List[str]:
        """
        Get enabled channels for a user and notification type.

        Resolution order:
        1. Scoped preference (user + type + scope_type + scope_id) — if scope provided
        2. Global user preference (user + type + scope_type='user')
        3. Type defaults from NotificationTypeConfig.default_channels
        """
        type_config = get_notification_type(notification_type)
        if not type_config:
            return []

        # 1. Check scoped preference (if org scope provided)
        if scope_type != "user" and scope_id is not None:
            scoped_pref = NotificationPreference.objects.filter(
                user=user,
                notification_type=notification_type,
                scope_type=scope_type,
                scope_id=scope_id,
            ).first()
            if scoped_pref:
                return scoped_pref.get_enabled_channels()

        # 2. Check global user preference
        global_pref = NotificationPreference.objects.filter(
            user=user,
            notification_type=notification_type,
            scope_type="user",
            scope_id__isnull=True,
        ).first()
        if global_pref:
            return global_pref.get_enabled_channels()

        # 3. Return type defaults
        return [c.value for c in type_config.default_channels]

    @staticmethod
    def update_preference(
        *,
        user,
        notification_type: str,
        email_enabled: bool | None = None,
        push_enabled: bool | None = None,
        sms_enabled: bool | None = None,
        request: HttpRequest | None = None,
    ) -> NotificationPreference:
        """
        Update user's preference for a notification type.

        Args:
            user: User instance
            notification_type: Notification type name
            email_enabled: Enable/disable email channel
            push_enabled: Enable/disable push channel
            sms_enabled: Enable/disable SMS channel
            request: HTTP request for audit context (optional)

        Raises:
            NotFound: Unknown notification type
            ValidationError: Type is not user_configurable
        """
        type_config = get_notification_type(notification_type)
        if not type_config:
            raise NotFound(
                message=f"Unknown notification type: {notification_type}",
                resource="NotificationType",
            )

        if not type_config.user_configurable:
            raise ValidationError(
                message=f"Cannot modify preferences for '{notification_type}'"
            )

        preference, created = NotificationPreference.objects.get_or_create(
            user=user,
            notification_type=notification_type,
            defaults={
                "email_enabled": Channel.EMAIL in type_config.default_channels,
                "push_enabled": Channel.PUSH in type_config.default_channels,
                "sms_enabled": Channel.SMS in type_config.default_channels,
            },
        )

        changes = {}

        if email_enabled is not None and preference.email_enabled != email_enabled:
            changes["email_enabled"] = {
                "old": preference.email_enabled,
                "new": email_enabled,
            }
            preference.email_enabled = email_enabled
        if push_enabled is not None and preference.push_enabled != push_enabled:
            changes["push_enabled"] = {
                "old": preference.push_enabled,
                "new": push_enabled,
            }
            preference.push_enabled = push_enabled
        if sms_enabled is not None and preference.sms_enabled != sms_enabled:
            changes["sms_enabled"] = {"old": preference.sms_enabled, "new": sms_enabled}
            preference.sms_enabled = sms_enabled

        preference.save()

        logger.info(
            "notification.preference.changed",
            user_id=str(user.id),
            type=notification_type,
            email_enabled=preference.email_enabled,
            push_enabled=preference.push_enabled,
            sms_enabled=preference.sms_enabled,
        )

        # Audit: Preference updated
        if changes:
            AuditService.log(
                action=AuditLog.Action.NOTIFICATION_PREFERENCE_UPDATED,
                actor=user,
                resource=preference,
                request=request,
                changes=changes,
                details={"notification_type": notification_type},
            )

        return preference

    @staticmethod
    def get_preference(*, user, notification_type: str) -> Dict:
        """
        Get preference for a specific notification type.

        Returns dict with current state (from preference or defaults).
        """
        type_config = get_notification_type(notification_type)
        if not type_config:
            raise NotFound(
                message=f"Unknown notification type: {notification_type}",
                resource="NotificationType",
            )

        # Get user's override if exists
        preference = NotificationPreference.objects.filter(
            user=user, notification_type=notification_type
        ).first()

        if preference:
            channels = preference.get_enabled_channels()
        else:
            channels = [c.value for c in type_config.default_channels]

        return {
            "notification_type": type_config.name,
            "display_name": type_config.display_name,
            "description": type_config.description,
            "category": type_config.category.value,
            "user_configurable": type_config.user_configurable,
            "email_enabled": "email" in channels,
            "push_enabled": "push" in channels,
            "sms_enabled": "sms" in channels,
        }

    @staticmethod
    def get_all_preferences(*, user) -> Dict[str, Dict]:
        """
        Get all preferences for a user (for settings UI).

        Returns dict with all configurable types and their status.
        """
        # Get user's overrides
        overrides = {
            p.notification_type: p
            for p in NotificationPreference.objects.filter(user=user)
        }

        result = {}
        for type_config in get_configurable_types():
            if type_config.name in overrides:
                pref = overrides[type_config.name]
                channels = pref.get_enabled_channels()
            else:
                channels = [c.value for c in type_config.default_channels]

            result[type_config.name] = {
                "display_name": type_config.display_name,
                "description": type_config.description,
                "category": type_config.category.value,
                "email_enabled": "email" in channels,
                "push_enabled": "push" in channels,
                "sms_enabled": "sms" in channels,
            }

        return result

    @staticmethod
    def reset_preference(*, user, notification_type: str) -> None:
        """
        Reset preference to defaults by deleting the override.
        """
        type_config = get_notification_type(notification_type)
        if not type_config:
            raise NotFound(
                message=f"Unknown notification type: {notification_type}",
                resource="NotificationType",
            )

        if not type_config.user_configurable:
            raise ValidationError(
                message=f"Cannot modify preferences for '{notification_type}'"
            )

        NotificationPreference.objects.filter(
            user=user, notification_type=notification_type
        ).delete()

        logger.info(
            "notification.preference.reset",
            user_id=str(user.id),
            type=notification_type,
        )
        AuditService.log(
            action=AuditLog.Action.NOTIFICATION_PREFERENCE_UPDATED,
            actor=user,
            resource=user,
            details={
                "notification_type": notification_type,
                "action": "reset_to_defaults",
            },
        )
