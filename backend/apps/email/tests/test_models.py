# apps/email/tests/test_models.py
"""
Tests for Email app models.

Covers:
    - EmailTemplate: creation, defaults, ordering, unique constraints,
      save() versioning, str representation, JSON fields
    - EmailLog: creation, defaults, UUID primary key, ordering, can_retry
      property, template FK relationship, status choices, bounce fields
"""

import uuid

import pytest
from django.db import IntegrityError

from apps.email.models import EmailTemplate, EmailLog
from apps.email.tests.factories import (
    EmailTemplateFactory,
    InactiveEmailTemplateFactory,
    ArchivedEmailTemplateFactory,
    EmailLogFactory,
    SentEmailLogFactory,
    DeliveredEmailLogFactory,
    FailedEmailLogFactory,
    BouncedEmailLogFactory,
    ComplainedEmailLogFactory,
    QueuedEmailLogFactory,
)


# =============================================================================
# EMAIL TEMPLATE TESTS
# =============================================================================


@pytest.mark.django_db
class TestEmailTemplate:
    """Tests for the EmailTemplate model."""

    def test_creation_with_factory(self):
        """EmailTemplate can be created via factory with valid data."""
        template = EmailTemplateFactory()

        assert template.pk is not None
        assert template.name is not None
        assert template.subject is not None
        assert template.html_body is not None
        assert template.created_at is not None
        assert template.updated_at is not None

    def test_str_representation(self):
        """__str__ returns 'name (vX)' format."""
        template = EmailTemplateFactory(name="welcome", version=3)

        assert str(template) == "welcome (v3)"

    def test_default_values(self):
        """New templates have correct defaults: is_active=True, version=1, is_current=True, variables={}."""
        template = EmailTemplateFactory()

        assert template.is_active is True
        assert template.version == 1
        assert template.is_current is True
        assert template.variables == {}

    def test_ordering(self):
        """Templates are ordered by category, name, then -version."""
        assert EmailTemplate._meta.ordering == ['category', 'name', '-version']

    def test_unique_constraint_name_version(self):
        """Two templates with the same name and version raise IntegrityError."""
        EmailTemplateFactory(name="duplicate", version=1)

        with pytest.raises(IntegrityError):
            EmailTemplateFactory(name="duplicate", version=1)

    def test_unique_current_per_name(self):
        """Two templates with the same name and is_current=True raise IntegrityError."""
        EmailTemplateFactory(name="unique_test", is_current=True, version=1)

        with pytest.raises(IntegrityError):
            EmailTemplateFactory(name="unique_test", is_current=True, version=2)

    def test_save_versioning_creates_new_row(self):
        """Editing an existing template creates a new row with version+1."""
        template = EmailTemplateFactory(name="versioned", version=1)
        original_pk = template.pk

        # Simulate editing the existing template
        template.subject = "Updated subject"
        template.save()

        # A new row should have been created
        assert template.pk != original_pk
        assert template.version == 2
        assert template.is_current is True

        # Total should be 2 rows for this template name
        count = EmailTemplate.objects.filter(name="versioned").count()
        assert count == 2

    def test_save_versioning_archives_old(self):
        """Editing an existing template sets is_current=False on the old version."""
        template = EmailTemplateFactory(name="archive_test", version=1)
        original_pk = template.pk

        # Edit the template to trigger versioning
        template.subject = "New subject"
        template.save()

        # The old version should be archived
        old_version = EmailTemplate.objects.get(pk=original_pk)
        assert old_version.is_current is False
        assert old_version.version == 1

        # The new version should be current
        assert template.is_current is True
        assert template.version == 2

    def test_save_new_template_no_versioning(self):
        """First save of a new template does not trigger versioning logic."""
        template = EmailTemplate(
            name="brand_new",
            subject="Hello",
            html_body="<p>Hello</p>",
        )
        template.save()

        assert template.version == 1
        assert template.is_current is True

        # Only one row should exist
        count = EmailTemplate.objects.filter(name="brand_new").count()
        assert count == 1

    def test_inactive_template(self):
        """InactiveEmailTemplateFactory creates a template with is_active=False."""
        template = InactiveEmailTemplateFactory()

        assert template.is_active is False

    def test_variables_json_field(self):
        """The variables JSONField correctly stores and retrieves a dict."""
        variables = {
            "user_name": {"type": "string", "required": True},
            "reset_link": {"type": "string", "required": True},
        }
        template = EmailTemplateFactory(variables=variables)
        template.refresh_from_db()

        assert template.variables == variables
        assert template.variables["user_name"]["type"] == "string"
        assert template.variables["reset_link"]["required"] is True

    def test_category_field(self):
        """Category field allows blank values."""
        template = EmailTemplateFactory(category="")

        assert template.category == ""

        template_with_category = EmailTemplateFactory(category="marketing")
        assert template_with_category.category == "marketing"


# =============================================================================
# EMAIL LOG TESTS
# =============================================================================


@pytest.mark.django_db
class TestEmailLog:
    """Tests for the EmailLog model."""

    def test_creation_with_factory(self):
        """EmailLog can be created via factory with valid data."""
        log = EmailLogFactory()

        assert log.pk is not None
        assert log.to_email is not None
        assert log.from_email is not None
        assert log.template_name is not None
        assert log.subject is not None
        assert log.created_at is not None

    def test_str_representation(self):
        """__str__ returns 'template_name -> to_email (status)' format."""
        log = EmailLogFactory(
            template_name="welcome",
            to_email="user@example.com",
            status=EmailLog.Status.PENDING,
        )

        assert str(log) == "welcome -> user@example.com (pending)"

    def test_default_status_is_pending(self):
        """New email logs default to PENDING status."""
        log = EmailLogFactory()

        assert log.status == EmailLog.Status.PENDING

    def test_uuid_primary_key(self):
        """EmailLog uses a UUID as its primary key."""
        log = EmailLogFactory()

        assert isinstance(log.id, uuid.UUID)

        # Two logs should have different UUIDs
        log2 = EmailLogFactory()
        assert log.id != log2.id

    def test_ordering_by_created_at_desc(self):
        """Email logs are ordered by -created_at (newest first)."""
        log1 = EmailLogFactory()
        log2 = EmailLogFactory()
        log3 = EmailLogFactory()

        logs = list(EmailLog.objects.all())

        # Most recently created should come first
        assert logs[0] == log3
        assert logs[1] == log2
        assert logs[2] == log1

    def test_can_retry_true_when_failed_and_retries_left(self):
        """can_retry is True when status is FAILED and retry_count < max_retries."""
        log = FailedEmailLogFactory(retry_count=1, max_retries=3)

        assert log.can_retry is True

    def test_can_retry_false_when_not_failed(self):
        """can_retry is False when status is not FAILED (e.g., SENT)."""
        log = SentEmailLogFactory(retry_count=0, max_retries=3)

        assert log.can_retry is False

    def test_can_retry_false_when_max_retries_reached(self):
        """can_retry is False when retry_count equals max_retries."""
        log = FailedEmailLogFactory(retry_count=3, max_retries=3)

        assert log.can_retry is False

    def test_can_retry_false_when_pending(self):
        """can_retry is False when status is PENDING."""
        log = EmailLogFactory(status=EmailLog.Status.PENDING)

        assert log.can_retry is False

    def test_template_relationship(self):
        """EmailLog can reference an EmailTemplate via FK, and template is nullable."""
        template = EmailTemplateFactory()
        log_with_template = EmailLogFactory(template=template)

        assert log_with_template.template == template
        assert log_with_template.template.pk == template.pk

        # Nullable: log without template
        log_without_template = EmailLogFactory(template=None)
        assert log_without_template.template is None

    def test_template_on_delete_set_null(self):
        """Deleting an EmailTemplate sets the FK on related EmailLog to NULL."""
        template = EmailTemplateFactory()
        log = EmailLogFactory(template=template)
        template_pk = template.pk

        # Delete the template
        EmailTemplate.objects.filter(pk=template_pk).delete()

        # Refresh the log and verify FK is set to NULL
        log.refresh_from_db()
        assert log.template is None

    def test_status_choices_all_valid(self):
        """All defined Status choices can be used to create EmailLog entries."""
        expected_statuses = [
            EmailLog.Status.PENDING,
            EmailLog.Status.QUEUED,
            EmailLog.Status.SENDING,
            EmailLog.Status.SENT,
            EmailLog.Status.DELIVERED,
            EmailLog.Status.BOUNCED,
            EmailLog.Status.COMPLAINED,
            EmailLog.Status.FAILED,
        ]

        for status in expected_statuses:
            log = EmailLogFactory(status=status)
            assert log.status == status

        # Verify we covered all choices
        assert len(expected_statuses) == len(EmailLog.Status.choices)

    def test_default_retry_values(self):
        """New email logs have retry_count=0 and max_retries=3 by default."""
        log = EmailLogFactory()

        assert log.retry_count == 0
        assert log.max_retries == 3

    def test_bounce_fields(self):
        """BouncedEmailLogFactory correctly populates bounce_type and bounce_subtype."""
        log = BouncedEmailLogFactory()

        assert log.bounce_type == "Permanent"
        assert log.bounce_subtype == "General"
        assert log.status == EmailLog.Status.BOUNCED
        assert log.bounced_at is not None

        # Verify bounce fields allow blank strings
        log_no_bounce = EmailLogFactory()
        assert log_no_bounce.bounce_type == ""
        assert log_no_bounce.bounce_subtype == ""
