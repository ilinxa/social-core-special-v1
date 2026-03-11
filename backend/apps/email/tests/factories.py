# apps/email/tests/factories.py
"""
Factory-boy factories for Email app tests.

Usage:
    from apps.email.tests.factories import EmailTemplateFactory, EmailLogFactory

    template = EmailTemplateFactory(name='welcome', category='auth')
    log = EmailLogFactory(template=template, status='sent')
"""

import uuid
from datetime import timedelta

import factory
from factory.django import DjangoModelFactory
from django.utils import timezone

from apps.email.models import EmailTemplate, EmailLog


# =============================================================================
# EMAIL TEMPLATE FACTORY
# =============================================================================


class EmailTemplateFactory(DjangoModelFactory):
    """Factory for EmailTemplate."""

    class Meta:
        model = EmailTemplate
        # Skip the custom save() versioning logic — create fresh rows directly
        skip_postgeneration_save = True

    name = factory.Sequence(lambda n: f"template_{n}")
    subject = factory.LazyAttribute(lambda obj: f"Subject for {obj.name}")
    html_body = factory.LazyAttribute(
        lambda obj: f"<h1>Hello</h1><p>Template: {obj.name}</p>"
    )
    text_body = factory.LazyAttribute(
        lambda obj: f"Hello. Template: {obj.name}"
    )
    variables = factory.LazyFunction(dict)
    description = ""
    category = "transactional"
    is_active = True
    version = 1
    is_current = True


class InactiveEmailTemplateFactory(EmailTemplateFactory):
    """Factory for inactive email templates."""

    is_active = False


class ArchivedEmailTemplateFactory(EmailTemplateFactory):
    """Factory for archived (non-current) template versions."""

    is_current = False


# =============================================================================
# EMAIL LOG FACTORY
# =============================================================================


class EmailLogFactory(DjangoModelFactory):
    """Factory for EmailLog."""

    class Meta:
        model = EmailLog

    to_email = factory.Sequence(lambda n: f"recipient_{n}@example.com")
    from_email = "noreply@example.com"
    reply_to = ""
    template = None
    template_name = factory.Sequence(lambda n: f"template_{n}")
    template_version = 1
    subject = factory.LazyAttribute(lambda obj: f"Subject: {obj.template_name}")
    html_body = "<h1>Test</h1>"
    text_body = "Test"
    context = factory.LazyFunction(dict)
    status = EmailLog.Status.PENDING
    message_id = ""
    error_message = ""
    error_code = ""
    retry_count = 0
    max_retries = 3


class SentEmailLogFactory(EmailLogFactory):
    """Factory for sent email logs."""

    status = EmailLog.Status.SENT
    message_id = factory.LazyFunction(lambda: f"ses-{uuid.uuid4()}")
    sent_at = factory.LazyFunction(timezone.now)


class DeliveredEmailLogFactory(EmailLogFactory):
    """Factory for delivered email logs."""

    status = EmailLog.Status.DELIVERED
    message_id = factory.LazyFunction(lambda: f"ses-{uuid.uuid4()}")
    sent_at = factory.LazyFunction(lambda: timezone.now() - timedelta(minutes=1))
    delivered_at = factory.LazyFunction(timezone.now)


class FailedEmailLogFactory(EmailLogFactory):
    """Factory for failed email logs."""

    status = EmailLog.Status.FAILED
    error_message = "Connection refused"
    error_code = "connection_error"
    failed_at = factory.LazyFunction(timezone.now)


class BouncedEmailLogFactory(EmailLogFactory):
    """Factory for bounced email logs."""

    status = EmailLog.Status.BOUNCED
    message_id = factory.LazyFunction(lambda: f"ses-{uuid.uuid4()}")
    bounced_at = factory.LazyFunction(timezone.now)
    bounce_type = "Permanent"
    bounce_subtype = "General"


class ComplainedEmailLogFactory(EmailLogFactory):
    """Factory for complained email logs."""

    status = EmailLog.Status.COMPLAINED
    message_id = factory.LazyFunction(lambda: f"ses-{uuid.uuid4()}")
    complained_at = factory.LazyFunction(timezone.now)


class QueuedEmailLogFactory(EmailLogFactory):
    """Factory for queued email logs."""

    status = EmailLog.Status.QUEUED
    queued_at = factory.LazyFunction(timezone.now)
