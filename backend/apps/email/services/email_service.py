"""
Email Service
=============
High-level API for sending emails.

Usage:
    # Send with template
    log = EmailService.send(
        template_name='welcome',
        to_email='user@example.com',
        context={'user_name': 'John'}
    )

    # Send raw email (no template)
    log = EmailService.send_raw(
        to_email='user@example.com',
        subject='Test',
        html_body='<h1>Test</h1>'
    )
"""

from typing import Any, Dict

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.core.exceptions import NotFound, ValidationError

# Observability
from apps.core.observability import get_logger
from apps.email.models import EmailLog, EmailTemplate
from apps.email.services.template_renderer import TemplateRenderer

logger = get_logger(__name__)


class EmailService:
    """
    High-level email sending API.

    Features:
        - Template-based sending with variable validation
        - Async sending via Celery (default)
        - Sync sending option for critical emails
        - Idempotency protection for concurrent workers
        - Full audit logging
    """

    @staticmethod
    def send(
        *,
        template_name: str,
        to_email: str,
        context: Dict[str, Any],
        from_email: str | None = None,
        reply_to: str | None = None,
        priority: str = "normal",
        async_send: bool = True,
    ) -> EmailLog:
        """
        Send an email using a template.

        Args:
            template_name: EmailTemplate.name
            to_email: Recipient email address
            context: Variables for template rendering
            from_email: Override default sender
            reply_to: Reply-to address
            priority: Queue priority ('high', 'normal', 'low')
            async_send: If True, queue via Celery; if False, send immediately

        Returns:
            EmailLog record

        Raises:
            NotFound: Template not found or inactive
            ValidationError: Missing required template variables
        """
        # Get active current template
        template = EmailTemplate.objects.filter(
            name=template_name, is_active=True, is_current=True
        ).first()

        if not template:
            raise NotFound(
                message=f"Email template '{template_name}' not found or inactive",
                resource="EmailTemplate",
            )

        # Validate context against template schema
        EmailService._validate_context(template, context)

        # Render template
        rendered = TemplateRenderer.render(template, context)

        # Create log entry
        log = EmailLog.objects.create(
            to_email=to_email,
            from_email=from_email or settings.DEFAULT_FROM_EMAIL,
            reply_to=reply_to or "",
            template=template,
            template_name=template.name,
            template_version=template.version,
            subject=rendered["subject"],
            html_body=rendered["html_body"],
            text_body=rendered["text_body"],
            context=context,
            status=EmailLog.Status.PENDING,
        )

        logger.info(
            "email.send.attempt",
            log_id=str(log.id),
            template=template_name,
            to_email_hash=hash(to_email),
        )

        # Queue or send
        if async_send:
            from apps.email.tasks import send_email_task

            send_email_task.delay(str(log.id), priority=priority)
            log.status = EmailLog.Status.QUEUED
            log.queued_at = timezone.now()
            log.save(update_fields=["status", "queued_at"])
        else:
            EmailService._send_now(log)

        return log

    @staticmethod
    def send_raw(
        *,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str = "",
        from_email: str | None = None,
        reply_to: str | None = None,
        async_send: bool = True,
    ) -> EmailLog:
        """
        Send email without template (for system emails, testing).

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML content
            text_body: Plain text content (auto-generated from HTML if empty)
            from_email: Sender email address
            reply_to: Reply-to address
            async_send: If True, queue via Celery; if False, send immediately

        Returns:
            EmailLog record
        """
        # Auto-generate text body if not provided
        if not text_body:
            text_body = TemplateRenderer._html_to_text(html_body)

        log = EmailLog.objects.create(
            to_email=to_email,
            from_email=from_email or settings.DEFAULT_FROM_EMAIL,
            reply_to=reply_to or "",
            template_name="_raw",
            template_version=0,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            status=EmailLog.Status.PENDING,
        )

        logger.info(
            "email.send_raw.attempt",
            log_id=str(log.id),
            to_email_hash=hash(to_email),
        )

        if async_send:
            from apps.email.tasks import send_email_task

            send_email_task.delay(str(log.id))
            log.status = EmailLog.Status.QUEUED
            log.queued_at = timezone.now()
            log.save(update_fields=["status", "queued_at"])
        else:
            EmailService._send_now(log)

        return log

    @staticmethod
    def _send_now(log: EmailLog) -> None:
        """
        Synchronously send an email with idempotency protection.

        Uses select_for_update to prevent duplicate sends from concurrent workers.

        Args:
            log: EmailLog to send
        """
        from apps.email.services.backends import get_email_backend

        backend = get_email_backend()

        # Acquire lock and verify status atomically
        with transaction.atomic():
            locked_log = EmailLog.objects.select_for_update().get(id=log.id)

            # Idempotency check: only send if still pending/queued
            if locked_log.status not in (
                EmailLog.Status.PENDING,
                EmailLog.Status.QUEUED,
            ):
                # Already being processed or completed
                logger.debug(
                    f"Email {log.id} already processed, status={locked_log.status}"
                )
                return

            locked_log.status = EmailLog.Status.SENDING
            locked_log.save(update_fields=["status"])

        # Send outside the lock (don't hold DB lock during network I/O)
        try:
            message_id = backend.send(
                to_email=log.to_email,
                from_email=log.from_email,
                subject=log.subject,
                html_body=log.html_body,
                text_body=log.text_body,
                reply_to=log.reply_to,
            )

            log.status = EmailLog.Status.SENT
            log.message_id = message_id
            log.sent_at = timezone.now()
            log.save(update_fields=["status", "message_id", "sent_at"])

            logger.info(
                "email.send.success",
                log_id=str(log.id),
                message_id=message_id,
            )

        except Exception as e:
            log.status = EmailLog.Status.FAILED
            log.error_message = str(e)
            log.failed_at = timezone.now()
            log.save(update_fields=["status", "error_message", "failed_at"])

            logger.error(
                "email.send.failed",
                log_id=str(log.id),
                error=str(e),
            )
            raise

    @staticmethod
    def _validate_context(template: EmailTemplate, context: Dict) -> None:
        """
        Validate context against template's variable schema.

        Schema format:
        {
            "var_name": {
                "type": "string|int|bool|list|dict",
                "required": true|false
            }
        }

        Args:
            template: EmailTemplate with variables schema
            context: Context dict to validate

        Raises:
            ValidationError: If validation fails
        """
        schema = template.variables or {}

        TYPE_VALIDATORS = {
            "string": lambda v: isinstance(v, str),
            "int": lambda v: isinstance(v, int) and not isinstance(v, bool),
            "bool": lambda v: isinstance(v, bool),
            "list": lambda v: isinstance(v, list),
            "dict": lambda v: isinstance(v, dict),
        }

        errors = []

        for var_name, var_config in schema.items():
            # Check required
            if var_config.get("required", False) and var_name not in context:
                errors.append(f"Missing required variable: {var_name}")
                continue

            # Check type if value is present
            if var_name in context:
                expected_type = var_config.get("type")
                value = context[var_name]

                if expected_type and expected_type in TYPE_VALIDATORS:
                    validator = TYPE_VALIDATORS[expected_type]
                    if not validator(value):
                        errors.append(
                            f"Variable '{var_name}' must be {expected_type}, "
                            f"got {type(value).__name__}"
                        )

        if errors:
            raise ValidationError(message="; ".join(errors), field="context")

    @staticmethod
    def resend(*, log_id: str) -> EmailLog:
        """
        Resend a failed email.

        Args:
            log_id: UUID of the EmailLog to resend

        Returns:
            Updated EmailLog

        Raises:
            NotFound: If log not found
            ValidationError: If email cannot be retried
        """
        log = EmailLog.objects.filter(id=log_id).first()
        if not log:
            raise NotFound(resource="EmailLog", resource_id=log_id)

        if not log.can_retry:
            raise ValidationError(
                message="Email cannot be retried (max retries reached or not failed)"
            )

        log.retry_count += 1
        log.status = EmailLog.Status.PENDING
        log.error_message = ""
        log.save(update_fields=["retry_count", "status", "error_message"])

        from apps.email.tasks import send_email_task

        send_email_task.delay(str(log.id))

        logger.info(
            "email.resend.queued",
            log_id=str(log.id),
            retry_count=log.retry_count,
        )

        return log

    @staticmethod
    def get_stats(*, template_name: str | None = None, days: int = 7) -> Dict:
        """
        Get email sending statistics.

        Args:
            template_name: Filter by template (optional)
            days: Number of days to look back

        Returns:
            Dict with counts by status
        """
        from datetime import timedelta

        from django.db.models import Count

        cutoff = timezone.now() - timedelta(days=days)

        queryset = EmailLog.objects.filter(created_at__gte=cutoff)
        if template_name:
            queryset = queryset.filter(template_name=template_name)

        stats = queryset.values("status").annotate(count=Count("id")).order_by("status")

        return {
            "period_days": days,
            "template": template_name,
            "by_status": {item["status"]: item["count"] for item in stats},
            "total": sum(item["count"] for item in stats),
        }
