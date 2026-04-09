"""
Notification Models
===================
Data models for notification preferences and logging.
"""

import uuid
from typing import List

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel
from apps.notifications.constants import NotificationScope


class NotificationPreference(TimeStampedModel):
    """
    User preferences for notification channels per type.

    Only stores OVERRIDES from defaults. If no record exists,
    use the default_channels from NotificationTypeConfig.

    Supports scoped preferences: a user can have different channel
    settings per org (business/platform) for the same notification type.
    Resolution order: scoped preference → global user preference → type defaults.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )

    notification_type = models.CharField(
        max_length=100, db_index=True, help_text="NotificationTypeConfig.name"
    )

    # Scope isolation
    scope_type = models.CharField(
        max_length=20,
        choices=NotificationScope.choices,
        default=NotificationScope.USER,
        db_index=True,
        help_text="Isolation scope: user (global default), business, or platform",
    )
    scope_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Null for user scope, UUID for org scope",
    )

    # Channel preferences (True = enabled, False = disabled)
    email_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)

    class Meta:
        db_table = "notification_preferences"
        verbose_name = "notification preference"
        verbose_name_plural = "notification preferences"
        indexes = [
            models.Index(
                fields=["user", "notification_type"], name="notifpref_user_type_idx"
            ),
            models.Index(
                fields=["user", "notification_type", "scope_type", "scope_id"],
                name="notifpref_user_type_scope_idx",
            ),
        ]
        constraints = [
            # Scoped preferences: one per user+type+scope_type+scope_id
            models.UniqueConstraint(
                fields=["user", "notification_type", "scope_type", "scope_id"],
                condition=models.Q(scope_id__isnull=False),
                name="notifpref_user_type_scope_uniq",
            ),
            # Global/user-scoped preferences: one per user+type+scope_type
            models.UniqueConstraint(
                fields=["user", "notification_type", "scope_type"],
                condition=models.Q(scope_id__isnull=True),
                name="notifpref_user_type_global_uniq",
            ),
        ]

    def __str__(self):
        scope_str = f" [{self.scope_type}]" if self.scope_type != "user" else ""
        return f"{self.user.email} - {self.notification_type}{scope_str}"

    def get_enabled_channels(self) -> List[str]:
        """Return list of enabled channels."""
        channels = []
        if self.email_enabled:
            channels.append("email")
        if self.push_enabled:
            channels.append("push")
        if self.sms_enabled:
            channels.append("sms")
        return channels


class NotificationLog(TimeStampedModel):
    """
    Audit log for all notifications sent.
    Tracks delivery status per channel.

    Supports scope isolation: notifications carry the org context
    (business/platform) they relate to, enabling frontend filtering
    and org-scoped notification views.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SENT = "sent", "Sent"
        PARTIAL = "partial", "Partially Sent"  # Some channels failed
        RETRYING = "retrying", "Retrying"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="notification_logs",
    )

    notification_type = models.CharField(max_length=100, db_index=True)

    # Scope isolation
    scope_type = models.CharField(
        max_length=20,
        choices=NotificationScope.choices,
        default=NotificationScope.USER,
        db_index=True,
        help_text="Isolation scope: user (personal), business, or platform",
    )
    scope_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Null for user scope, UUID for org scope",
    )

    # Channels used for this notification
    channels = models.JSONField(
        default=list, help_text="List of channels used: ['email', 'push']"
    )

    # Context used for rendering
    context = models.JSONField(default=dict)

    # Status
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )

    # Retry tracking
    retry_count = models.PositiveSmallIntegerField(default=0)

    # Per-channel results
    channel_results = models.JSONField(
        default=dict,
        help_text="Per-channel status: {'email': {'status': 'sent', 'email_log_id': '...'}, ...}",
    )

    # Error tracking
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "notification_logs"
        verbose_name = "notification log"
        verbose_name_plural = "notification logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user", "created_at"], name="notiflog_user_created_idx"
            ),
            models.Index(
                fields=["notification_type", "created_at"],
                name="notiflog_type_created_idx",
            ),
            models.Index(
                fields=["status", "created_at"], name="notiflog_status_created_idx"
            ),
            models.Index(
                fields=["scope_type", "scope_id", "user", "created_at"],
                name="notiflog_scope_user_idx",
            ),
            models.Index(
                fields=["scope_type", "scope_id", "created_at"],
                name="notiflog_scope_created_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(scope_type="user") | models.Q(scope_id__isnull=False),
                name="notiflog_scope_id_required_for_org",
            ),
        ]

    def __str__(self):
        user_str = self.user.email if self.user else "Unknown"
        scope_str = f" [{self.scope_type}]" if self.scope_type != "user" else ""
        return f"{self.notification_type} → {user_str} ({self.status}){scope_str}"
