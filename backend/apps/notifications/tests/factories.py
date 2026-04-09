# apps/notifications/tests/factories.py
"""
Factory-boy factories for Notifications app tests.

Usage:
    from apps.notifications.tests.factories import (
        NotificationPreferenceFactory,
        NotificationLogFactory,
        SentNotificationLogFactory,
    )
"""

import uuid

import factory
from factory.django import DjangoModelFactory

from apps.notifications.models import NotificationLog, NotificationPreference
from apps.users.tests.factories import UserFactory

# =============================================================================
# NOTIFICATION PREFERENCE FACTORIES
# =============================================================================


class NotificationPreferenceFactory(DjangoModelFactory):
    """Factory for NotificationPreference."""

    class Meta:
        model = NotificationPreference
        skip_postgeneration_save = True

    user = factory.SubFactory(UserFactory)
    notification_type = "new_login"
    email_enabled = True
    push_enabled = True
    sms_enabled = False


class DisabledPreferenceFactory(NotificationPreferenceFactory):
    """Factory for a preference with all channels disabled."""

    email_enabled = False
    push_enabled = False
    sms_enabled = False


# =============================================================================
# NOTIFICATION LOG FACTORIES
# =============================================================================


class NotificationLogFactory(DjangoModelFactory):
    """Factory for NotificationLog (default: PENDING)."""

    class Meta:
        model = NotificationLog
        skip_postgeneration_save = True

    id = factory.LazyFunction(uuid.uuid4)
    user = factory.SubFactory(UserFactory)
    notification_type = "welcome"
    channels = factory.LazyFunction(lambda: ["email"])
    context = factory.LazyFunction(dict)
    status = NotificationLog.Status.PENDING
    retry_count = 0
    channel_results = factory.LazyFunction(dict)
    error_message = ""


class SentNotificationLogFactory(NotificationLogFactory):
    """Factory for SENT notification logs."""

    status = NotificationLog.Status.SENT
    channel_results = factory.LazyFunction(
        lambda: {"email": {"status": "sent", "email_log_id": str(uuid.uuid4())}}
    )


class FailedNotificationLogFactory(NotificationLogFactory):
    """Factory for FAILED notification logs."""

    status = NotificationLog.Status.FAILED
    channel_results = factory.LazyFunction(
        lambda: {"email": {"status": "failed", "error": "SMTP connection refused"}}
    )
    error_message = "All channels failed"


class PartialNotificationLogFactory(NotificationLogFactory):
    """Factory for PARTIAL notification logs (some channels succeeded, some failed)."""

    status = NotificationLog.Status.PARTIAL
    channels = factory.LazyFunction(lambda: ["email", "push"])
    channel_results = factory.LazyFunction(
        lambda: {
            "email": {"status": "sent", "email_log_id": str(uuid.uuid4())},
            "push": {"status": "failed", "error": "Push service unavailable"},
        }
    )


class ProcessingNotificationLogFactory(NotificationLogFactory):
    """Factory for PROCESSING notification logs."""

    status = NotificationLog.Status.PROCESSING


class ScopedNotificationLogFactory(NotificationLogFactory):
    """Factory for business-scoped notification logs."""

    scope_type = "business"
    scope_id = factory.LazyFunction(uuid.uuid4)


class ScopedPreferenceFactory(NotificationPreferenceFactory):
    """Factory for business-scoped notification preferences."""

    scope_type = "business"
    scope_id = factory.LazyFunction(uuid.uuid4)
