"""
Notification Models
===================
Data models for notification preferences and logging.
"""

import uuid
from typing import List

from django.db import models
from django.conf import settings

from apps.core.models import TimeStampedModel


class NotificationPreference(TimeStampedModel):
    """
    User preferences for notification channels per type.

    Only stores OVERRIDES from defaults. If no record exists,
    use the default_channels from NotificationTypeConfig.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )

    notification_type = models.CharField(
        max_length=100,
        db_index=True,
        help_text="NotificationTypeConfig.name"
    )

    # Channel preferences (True = enabled, False = disabled)
    email_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)

    class Meta:
        db_table = 'notification_preferences'
        unique_together = ['user', 'notification_type']
        indexes = [
            models.Index(
                fields=['user', 'notification_type'],
                name='notifpref_user_type_idx'
            ),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.notification_type}"

    def get_enabled_channels(self) -> List[str]:
        """Return list of enabled channels."""
        channels = []
        if self.email_enabled:
            channels.append('email')
        if self.push_enabled:
            channels.append('push')
        if self.sms_enabled:
            channels.append('sms')
        return channels


class NotificationLog(TimeStampedModel):
    """
    Audit log for all notifications sent.
    Tracks delivery status per channel.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        SENT = 'sent', 'Sent'
        PARTIAL = 'partial', 'Partially Sent'  # Some channels failed
        RETRYING = 'retrying', 'Retrying'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='notification_logs'
    )

    notification_type = models.CharField(
        max_length=100,
        db_index=True
    )

    # Channels used for this notification
    channels = models.JSONField(
        default=list,
        help_text="List of channels used: ['email', 'push']"
    )

    # Context used for rendering
    context = models.JSONField(
        default=dict
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )

    # Retry tracking
    retry_count = models.PositiveSmallIntegerField(default=0)

    # Per-channel results
    channel_results = models.JSONField(
        default=dict,
        help_text="Per-channel status: {'email': {'status': 'sent', 'email_log_id': '...'}, ...}"
    )

    # Error tracking
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = 'notification_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(
                fields=['user', 'created_at'],
                name='notiflog_user_created_idx'
            ),
            models.Index(
                fields=['notification_type', 'created_at'],
                name='notiflog_type_created_idx'
            ),
            models.Index(
                fields=['status', 'created_at'],
                name='notiflog_status_created_idx'
            ),
        ]

    def __str__(self):
        user_str = self.user.email if self.user else 'Unknown'
        return f"{self.notification_type} → {user_str} ({self.status})"
