"""
Notification Constants
======================
Enums and constants for the notification system.
"""

from django.db import models


class NotificationScope(models.TextChoices):
    """Isolation scope for notifications."""

    USER = "user", "User"
    BUSINESS = "business", "Business"
    PLATFORM = "platform", "Platform"
