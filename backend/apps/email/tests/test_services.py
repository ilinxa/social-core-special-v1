"""
Tests for EmailService and TemplateRenderer.

Covers:
    - EmailService.send (template-based)
    - EmailService.send_raw (no template)
    - EmailService._send_now (sync delivery with idempotency)
    - EmailService._validate_context (variable schema validation)
    - EmailService.resend (retry failed emails)
    - EmailService.get_stats (statistics)
    - TemplateRenderer.render (template rendering)
    - TemplateRenderer._html_to_text (HTML to plain text)
"""

import uuid
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from django.utils import timezone

from apps.core.exceptions import NotFound, ValidationError
from apps.email.models import EmailLog, EmailTemplate
from apps.email.services.email_service import EmailService
from apps.email.services.template_renderer import TemplateRenderer
from apps.email.tests.factories import (
    ArchivedEmailTemplateFactory,
    EmailLogFactory,
    EmailTemplateFactory,
    FailedEmailLogFactory,
    InactiveEmailTemplateFactory,
    QueuedEmailLogFactory,
    SentEmailLogFactory,
)

# =============================================================================
# TestEmailServiceSend
# =============================================================================


@pytest.mark.django_db
class TestEmailServiceSend:
    """Tests for EmailService.send() — template-based email sending."""

    def _make_template(self, **kwargs):
        """Helper to create a template with standard variables."""
        defaults = dict(
            name="welcome",
            subject="Welcome {{ user_name }}!",
            html_body="<h1>Welcome {{ user_name }}</h1>",
            text_body="Welcome {{ user_name }}",
            variables={
                "user_name": {"type": "string", "required": True},
            },
        )
        defaults.update(kwargs)
        return EmailTemplateFactory(**defaults)

    @patch("apps.email.tasks.send_email_task")
    def test_send_creates_log_with_pending_status(self, mock_task):
        """send() creates an EmailLog. After async queueing it becomes QUEUED,
        but the initial creation used PENDING."""
        template = self._make_template()
        log = EmailService.send(
            template_name="welcome",
            to_email="user@example.com",
            context={"user_name": "Alice"},
        )
        assert isinstance(log, EmailLog)
        # After async send the status is updated to QUEUED
        assert log.status == EmailLog.Status.QUEUED

    @patch("apps.email.tasks.send_email_task")
    def test_send_async_queues_task(self, mock_task):
        """Async send calls send_email_task.delay with the log id."""
        template = self._make_template()
        log = EmailService.send(
            template_name="welcome",
            to_email="user@example.com",
            context={"user_name": "Alice"},
        )
        mock_task.delay.assert_called_once_with(str(log.id), priority="normal")

    @patch("apps.email.tasks.send_email_task")
    def test_send_async_updates_status_to_queued(self, mock_task):
        """After queuing the task, log status is updated to QUEUED."""
        template = self._make_template()
        log = EmailService.send(
            template_name="welcome",
            to_email="user@example.com",
            context={"user_name": "Alice"},
        )
        log.refresh_from_db()
        assert log.status == EmailLog.Status.QUEUED
        assert log.queued_at is not None

    @patch("apps.email.services.email_service.EmailService._send_now")
    def test_send_sync_calls_send_now(self, mock_send_now):
        """When async_send=False, _send_now is called directly."""
        template = self._make_template()
        log = EmailService.send(
            template_name="welcome",
            to_email="user@example.com",
            context={"user_name": "Alice"},
            async_send=False,
        )
        mock_send_now.assert_called_once_with(log)

    def test_send_not_found_template_raises(self):
        """Raises NotFound when template_name doesn't match any template."""
        with pytest.raises(NotFound):
            EmailService.send(
                template_name="nonexistent",
                to_email="user@example.com",
                context={},
            )

    @patch("apps.email.tasks.send_email_task")
    def test_send_inactive_template_raises(self, mock_task):
        """Raises NotFound for inactive templates (is_active=False)."""
        InactiveEmailTemplateFactory(name="inactive_tpl")
        with pytest.raises(NotFound):
            EmailService.send(
                template_name="inactive_tpl",
                to_email="user@example.com",
                context={},
            )

    @patch("apps.email.tasks.send_email_task")
    def test_send_archived_template_raises(self, mock_task):
        """Raises NotFound for archived templates (is_current=False)."""
        ArchivedEmailTemplateFactory(name="archived_tpl")
        with pytest.raises(NotFound):
            EmailService.send(
                template_name="archived_tpl",
                to_email="user@example.com",
                context={},
            )

    def test_send_missing_required_variable_raises_validation_error(self):
        """Raises ValidationError when required variable is missing from context."""
        self._make_template()
        with pytest.raises(ValidationError) as exc_info:
            EmailService.send(
                template_name="welcome",
                to_email="user@example.com",
                context={},  # missing 'user_name'
            )
        assert "user_name" in str(exc_info.value)

    @patch("apps.email.tasks.send_email_task")
    def test_send_renders_template_correctly(self, mock_task):
        """Rendered subject is stored correctly in the log."""
        self._make_template()
        log = EmailService.send(
            template_name="welcome",
            to_email="user@example.com",
            context={"user_name": "Alice"},
        )
        log.refresh_from_db()
        assert log.subject == "Welcome Alice!"
        assert "Welcome Alice" in log.html_body

    @patch("apps.email.tasks.send_email_task")
    def test_send_uses_default_from_email(self, mock_task):
        """When from_email is not provided, settings.DEFAULT_FROM_EMAIL is used."""
        self._make_template()
        log = EmailService.send(
            template_name="welcome",
            to_email="user@example.com",
            context={"user_name": "Alice"},
        )
        log.refresh_from_db()
        assert log.from_email == settings.DEFAULT_FROM_EMAIL

    @patch("apps.email.tasks.send_email_task")
    def test_send_custom_from_email(self, mock_task):
        """Custom from_email overrides the default."""
        self._make_template()
        log = EmailService.send(
            template_name="welcome",
            to_email="user@example.com",
            context={"user_name": "Alice"},
            from_email="custom@sender.com",
        )
        log.refresh_from_db()
        assert log.from_email == "custom@sender.com"

    @patch("apps.email.tasks.send_email_task")
    def test_send_custom_reply_to(self, mock_task):
        """Custom reply_to is stored on the log."""
        self._make_template()
        log = EmailService.send(
            template_name="welcome",
            to_email="user@example.com",
            context={"user_name": "Alice"},
            reply_to="reply@example.com",
        )
        log.refresh_from_db()
        assert log.reply_to == "reply@example.com"


# =============================================================================
# TestEmailServiceSendRaw
# =============================================================================


@pytest.mark.django_db
class TestEmailServiceSendRaw:
    """Tests for EmailService.send_raw() — raw email sending (no template)."""

    @patch("apps.email.tasks.send_email_task")
    def test_send_raw_creates_log(self, mock_task):
        """send_raw creates an EmailLog record."""
        log = EmailService.send_raw(
            to_email="user@example.com",
            subject="Test Subject",
            html_body="<p>Hello</p>",
        )
        assert isinstance(log, EmailLog)
        assert EmailLog.objects.filter(id=log.id).exists()

    @patch("apps.email.tasks.send_email_task")
    def test_send_raw_template_name_is_raw(self, mock_task):
        """Raw emails have template_name='_raw' and template_version=0."""
        log = EmailService.send_raw(
            to_email="user@example.com",
            subject="Test",
            html_body="<p>Hello</p>",
        )
        log.refresh_from_db()
        assert log.template_name == "_raw"
        assert log.template_version == 0

    @patch("apps.email.tasks.send_email_task")
    def test_send_raw_auto_generates_text_body(self, mock_task):
        """When text_body is empty, it is auto-generated from HTML."""
        log = EmailService.send_raw(
            to_email="user@example.com",
            subject="Test",
            html_body="<p>Hello World</p>",
        )
        log.refresh_from_db()
        assert log.text_body  # non-empty
        assert "Hello World" in log.text_body

    @patch("apps.email.tasks.send_email_task")
    def test_send_raw_preserves_provided_text_body(self, mock_task):
        """When text_body is explicitly provided, it is used as-is."""
        log = EmailService.send_raw(
            to_email="user@example.com",
            subject="Test",
            html_body="<p>Hello</p>",
            text_body="Custom text body",
        )
        log.refresh_from_db()
        assert log.text_body == "Custom text body"

    @patch("apps.email.tasks.send_email_task")
    def test_send_raw_async_queues_task(self, mock_task):
        """Async raw send calls send_email_task.delay."""
        log = EmailService.send_raw(
            to_email="user@example.com",
            subject="Test",
            html_body="<p>Hello</p>",
        )
        mock_task.delay.assert_called_once_with(str(log.id))

    @patch("apps.email.services.email_service.EmailService._send_now")
    def test_send_raw_sync(self, mock_send_now):
        """sync send_raw calls _send_now directly."""
        log = EmailService.send_raw(
            to_email="user@example.com",
            subject="Test",
            html_body="<p>Hello</p>",
            async_send=False,
        )
        mock_send_now.assert_called_once_with(log)


# =============================================================================
# TestEmailServiceSendNow
# =============================================================================


@pytest.mark.django_db
class TestEmailServiceSendNow:
    """Tests for EmailService._send_now() — synchronous sending with idempotency."""

    @patch("apps.email.services.backends.get_email_backend")
    def test_send_now_success(self, mock_get_backend):
        """Successful send sets status to SENT."""
        mock_backend = MagicMock()
        mock_backend.send.return_value = "msg-id-123"
        mock_get_backend.return_value = mock_backend

        log = EmailLogFactory(status=EmailLog.Status.PENDING)
        EmailService._send_now(log)

        log.refresh_from_db()
        assert log.status == EmailLog.Status.SENT

    @patch("apps.email.services.backends.get_email_backend")
    def test_send_now_idempotent_skip(self, mock_get_backend):
        """Already SENT emails are not sent again."""
        mock_backend = MagicMock()
        mock_get_backend.return_value = mock_backend

        log = SentEmailLogFactory()
        EmailService._send_now(log)

        mock_backend.send.assert_not_called()

    @patch("apps.email.services.backends.get_email_backend")
    def test_send_now_failure_sets_failed(self, mock_get_backend):
        """Backend exception sets status to FAILED."""
        mock_backend = MagicMock()
        mock_backend.send.side_effect = Exception("SMTP error")
        mock_get_backend.return_value = mock_backend

        log = EmailLogFactory(status=EmailLog.Status.PENDING)

        with pytest.raises(Exception, match="SMTP error"):
            EmailService._send_now(log)

        log.refresh_from_db()
        assert log.status == EmailLog.Status.FAILED

    @patch("apps.email.services.backends.get_email_backend")
    def test_send_now_stores_message_id(self, mock_get_backend):
        """The message_id returned by the backend is saved on the log."""
        mock_backend = MagicMock()
        mock_backend.send.return_value = "ses-abc-123"
        mock_get_backend.return_value = mock_backend

        log = EmailLogFactory(status=EmailLog.Status.PENDING)
        EmailService._send_now(log)

        log.refresh_from_db()
        assert log.message_id == "ses-abc-123"

    @patch("apps.email.services.backends.get_email_backend")
    def test_send_now_sets_sent_at(self, mock_get_backend):
        """sent_at timestamp is set on success."""
        mock_backend = MagicMock()
        mock_backend.send.return_value = "msg-id-456"
        mock_get_backend.return_value = mock_backend

        log = EmailLogFactory(status=EmailLog.Status.PENDING)
        assert log.sent_at is None

        EmailService._send_now(log)

        log.refresh_from_db()
        assert log.sent_at is not None

    @patch("apps.email.services.backends.get_email_backend")
    def test_send_now_failure_re_raises(self, mock_get_backend):
        """Backend exception is re-raised after updating the log."""
        mock_backend = MagicMock()
        mock_backend.send.side_effect = ConnectionError("Connection refused")
        mock_get_backend.return_value = mock_backend

        log = EmailLogFactory(status=EmailLog.Status.PENDING)

        with pytest.raises(ConnectionError, match="Connection refused"):
            EmailService._send_now(log)


# =============================================================================
# TestEmailServiceValidation
# =============================================================================


@pytest.mark.django_db
class TestEmailServiceValidation:
    """Tests for EmailService._validate_context() — variable schema validation."""

    def test_validate_context_passes_with_valid_data(self):
        """No exception when all required variables are present with correct types."""
        template = EmailTemplateFactory(
            variables={
                "user_name": {"type": "string", "required": True},
                "count": {"type": "int", "required": True},
            }
        )
        # Should not raise
        EmailService._validate_context(template, {"user_name": "Alice", "count": 5})

    def test_validate_context_fails_missing_required(self):
        """Raises ValidationError when a required variable is missing."""
        template = EmailTemplateFactory(
            variables={
                "user_name": {"type": "string", "required": True},
            }
        )
        with pytest.raises(ValidationError) as exc_info:
            EmailService._validate_context(template, {})
        assert "user_name" in str(exc_info.value)

    def test_validate_context_fails_wrong_type_string(self):
        """Raises ValidationError when a string variable receives a non-string."""
        template = EmailTemplateFactory(
            variables={
                "user_name": {"type": "string", "required": True},
            }
        )
        with pytest.raises(ValidationError) as exc_info:
            EmailService._validate_context(template, {"user_name": 123})
        assert "user_name" in str(exc_info.value)
        assert "string" in str(exc_info.value)

    def test_validate_context_fails_wrong_type_int(self):
        """bool should not pass int validation (isinstance(True, int) is True,
        but the validator explicitly excludes bools)."""
        template = EmailTemplateFactory(
            variables={
                "count": {"type": "int", "required": True},
            }
        )
        with pytest.raises(ValidationError) as exc_info:
            EmailService._validate_context(template, {"count": True})
        assert "count" in str(exc_info.value)

    def test_validate_context_passes_optional_missing(self):
        """Optional (required=False) variables do not raise when absent."""
        template = EmailTemplateFactory(
            variables={
                "nickname": {"type": "string", "required": False},
            }
        )
        # Should not raise
        EmailService._validate_context(template, {})

    def test_validate_context_empty_schema_passes(self):
        """Templates with no variable schema accept any context."""
        template = EmailTemplateFactory(variables={})
        # Should not raise
        EmailService._validate_context(template, {"anything": "goes"})


# =============================================================================
# TestEmailServiceResend
# =============================================================================


@pytest.mark.django_db
class TestEmailServiceResend:
    """Tests for EmailService.resend() — retry failed emails."""

    @patch("apps.email.tasks.send_email_task")
    def test_resend_increments_retry_count(self, mock_task):
        """Resend increments the retry_count by 1."""
        log = FailedEmailLogFactory(retry_count=0, max_retries=3)
        updated = EmailService.resend(log_id=str(log.id))
        assert updated.retry_count == 1

    @patch("apps.email.tasks.send_email_task")
    def test_resend_sets_status_pending(self, mock_task):
        """Resend resets status to PENDING."""
        log = FailedEmailLogFactory(retry_count=0, max_retries=3)
        updated = EmailService.resend(log_id=str(log.id))
        updated.refresh_from_db()
        assert updated.status == EmailLog.Status.PENDING

    def test_resend_not_found_raises(self):
        """Raises NotFound if the log_id does not exist."""
        fake_id = str(uuid.uuid4())
        with pytest.raises(NotFound):
            EmailService.resend(log_id=fake_id)

    def test_resend_max_retries_reached_raises(self):
        """Raises ValidationError if retry_count >= max_retries."""
        log = FailedEmailLogFactory(retry_count=3, max_retries=3)
        with pytest.raises(ValidationError):
            EmailService.resend(log_id=str(log.id))

    def test_resend_not_failed_raises(self):
        """Raises ValidationError if the email is not in FAILED status."""
        log = SentEmailLogFactory()
        with pytest.raises(ValidationError):
            EmailService.resend(log_id=str(log.id))


# =============================================================================
# TestEmailServiceGetStats
# =============================================================================


@pytest.mark.django_db
class TestEmailServiceGetStats:
    """Tests for EmailService.get_stats() — email statistics."""

    def test_get_stats_returns_correct_format(self):
        """get_stats returns dict with by_status, total, and period_days."""
        EmailLogFactory(status=EmailLog.Status.SENT)
        EmailLogFactory(status=EmailLog.Status.SENT)
        EmailLogFactory(status=EmailLog.Status.FAILED)

        stats = EmailService.get_stats()

        assert "by_status" in stats
        assert "total" in stats
        assert "period_days" in stats
        assert stats["total"] == 3
        assert stats["period_days"] == 7

    def test_get_stats_filters_by_template(self):
        """get_stats with template_name only counts logs for that template."""
        EmailLogFactory(template_name="welcome", status=EmailLog.Status.SENT)
        EmailLogFactory(template_name="welcome", status=EmailLog.Status.SENT)
        EmailLogFactory(template_name="password_reset", status=EmailLog.Status.SENT)

        stats = EmailService.get_stats(template_name="welcome")
        assert stats["total"] == 2
        assert stats["template"] == "welcome"

    def test_get_stats_filters_by_days(self):
        """get_stats respects the days parameter to exclude older logs."""
        # Recent log
        EmailLogFactory(status=EmailLog.Status.SENT)

        # Old log — created_at is auto-set by TimeStampedModel, so update directly
        old_log = EmailLogFactory(status=EmailLog.Status.SENT)
        EmailLog.objects.filter(id=old_log.id).update(
            created_at=timezone.now() - timedelta(days=30)
        )

        stats = EmailService.get_stats(days=7)
        assert stats["total"] == 1


# =============================================================================
# TestTemplateRenderer
# =============================================================================


@pytest.mark.django_db
class TestTemplateRenderer:
    """Tests for TemplateRenderer — template rendering and HTML-to-text conversion."""

    def test_render_subject_with_variables(self):
        """Subject is rendered with context variables."""
        template = EmailTemplateFactory(
            subject="Hello {{ name }}!",
            html_body="<p>Body</p>",
            text_body="Body",
        )
        result = TemplateRenderer.render(template, {"name": "Bob"})
        assert result["subject"] == "Hello Bob!"

    def test_render_html_body_with_variables(self):
        """HTML body is rendered with context variables."""
        template = EmailTemplateFactory(
            subject="Subject",
            html_body="<h1>Welcome {{ user }}</h1><p>Your code: {{ code }}</p>",
            text_body="Text",
        )
        result = TemplateRenderer.render(template, {"user": "Eve", "code": "1234"})
        assert "Welcome Eve" in result["html_body"]
        assert "1234" in result["html_body"]

    def test_render_text_body_with_variables(self):
        """Text body is rendered when provided on the template."""
        template = EmailTemplateFactory(
            subject="Subject",
            html_body="<p>HTML</p>",
            text_body="Hello {{ user }}, your code is {{ code }}.",
        )
        result = TemplateRenderer.render(template, {"user": "Eve", "code": "5678"})
        assert "Hello Eve" in result["text_body"]
        assert "5678" in result["text_body"]

    def test_render_auto_generates_text_from_html(self):
        """When template.text_body is empty, text_body is generated from HTML."""
        template = EmailTemplateFactory(
            subject="Subject",
            html_body="<h1>Hello {{ name }}</h1><p>Welcome aboard!</p>",
            text_body="",  # empty — triggers auto-generation
        )
        result = TemplateRenderer.render(template, {"name": "Charlie"})
        assert result["text_body"]  # non-empty
        assert "Hello Charlie" in result["text_body"]
        assert "Welcome aboard" in result["text_body"]
        # Should not contain HTML tags
        assert "<h1>" not in result["text_body"]
        assert "<p>" not in result["text_body"]

    def test_html_to_text_strips_tags(self):
        """_html_to_text removes HTML tags and returns plain text."""
        html = "<h1>Title</h1><p>Paragraph with <strong>bold</strong> text.</p>"
        text = TemplateRenderer._html_to_text(html)
        assert "Title" in text
        assert "bold" in text
        assert "<h1>" not in text
        assert "<strong>" not in text
