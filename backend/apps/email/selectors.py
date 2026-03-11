"""
Email Selectors
===============
Query helpers for email data.

All read operations should go through selectors.
"""

from typing import Optional, List
from datetime import timedelta

from django.db.models import QuerySet
from django.utils import timezone

from apps.email.models import EmailTemplate, EmailLog


class EmailTemplateSelector:
    """Selectors for EmailTemplate queries."""

    @staticmethod
    def get_by_name(name: str) -> Optional[EmailTemplate]:
        """
        Get the current active version of a template by name.

        Args:
            name: Template name

        Returns:
            EmailTemplate or None
        """
        return EmailTemplate.objects.filter(
            name=name,
            is_active=True,
            is_current=True
        ).first()

    @staticmethod
    def get_all_current() -> QuerySet[EmailTemplate]:
        """
        Get all current template versions.

        Returns:
            QuerySet of current EmailTemplates
        """
        return EmailTemplate.objects.filter(is_current=True)

    @staticmethod
    def get_by_category(category: str) -> QuerySet[EmailTemplate]:
        """
        Get all current templates in a category.

        Args:
            category: Category name

        Returns:
            QuerySet of EmailTemplates
        """
        return EmailTemplate.objects.filter(
            category=category,
            is_current=True
        )

    @staticmethod
    def get_version_history(name: str) -> QuerySet[EmailTemplate]:
        """
        Get all versions of a template.

        Args:
            name: Template name

        Returns:
            QuerySet ordered by version descending
        """
        return EmailTemplate.objects.filter(
            name=name
        ).order_by('-version')

    @staticmethod
    def template_exists(name: str) -> bool:
        """
        Check if a template exists.

        Args:
            name: Template name

        Returns:
            True if exists
        """
        return EmailTemplate.objects.filter(
            name=name,
            is_current=True
        ).exists()


class EmailLogSelector:
    """Selectors for EmailLog queries."""

    @staticmethod
    def get_by_id(log_id: str) -> Optional[EmailLog]:
        """
        Get email log by ID.

        Args:
            log_id: UUID string

        Returns:
            EmailLog or None
        """
        return EmailLog.objects.filter(id=log_id).first()

    @staticmethod
    def get_by_message_id(message_id: str) -> Optional[EmailLog]:
        """
        Get email log by provider message ID.

        Args:
            message_id: SES/SMTP message ID

        Returns:
            EmailLog or None
        """
        return EmailLog.objects.filter(message_id=message_id).first()

    @staticmethod
    def get_by_email(
        email: str,
        *,
        limit: int = 100
    ) -> QuerySet[EmailLog]:
        """
        Get email logs for a recipient.

        Args:
            email: Recipient email address
            limit: Maximum records to return

        Returns:
            QuerySet ordered by created_at descending
        """
        return EmailLog.objects.filter(
            to_email=email
        ).order_by('-created_at')[:limit]

    @staticmethod
    def get_failed_for_retry() -> QuerySet[EmailLog]:
        """
        Get failed emails that can be retried.

        Returns:
            QuerySet of retryable EmailLogs
        """
        return EmailLog.objects.filter(
            status=EmailLog.Status.FAILED,
        ).exclude(
            retry_count__gte=models.F('max_retries')
        ).order_by('next_retry_at')

    @staticmethod
    def get_pending() -> QuerySet[EmailLog]:
        """
        Get emails in pending/queued state.

        Returns:
            QuerySet of pending EmailLogs
        """
        return EmailLog.objects.filter(
            status__in=[EmailLog.Status.PENDING, EmailLog.Status.QUEUED]
        ).order_by('created_at')

    @staticmethod
    def get_by_status(
        status: str,
        *,
        days: int = 7
    ) -> QuerySet[EmailLog]:
        """
        Get emails by status within a time range.

        Args:
            status: Status value
            days: Number of days to look back

        Returns:
            QuerySet of EmailLogs
        """
        cutoff = timezone.now() - timedelta(days=days)
        return EmailLog.objects.filter(
            status=status,
            created_at__gte=cutoff
        ).order_by('-created_at')

    @staticmethod
    def get_bounced(*, days: int = 30) -> QuerySet[EmailLog]:
        """
        Get bounced emails.

        Args:
            days: Number of days to look back

        Returns:
            QuerySet of bounced EmailLogs
        """
        cutoff = timezone.now() - timedelta(days=days)
        return EmailLog.objects.filter(
            status=EmailLog.Status.BOUNCED,
            created_at__gte=cutoff
        ).order_by('-bounced_at')

    @staticmethod
    def get_complained(*, days: int = 30) -> QuerySet[EmailLog]:
        """
        Get complained emails.

        Args:
            days: Number of days to look back

        Returns:
            QuerySet of complained EmailLogs
        """
        cutoff = timezone.now() - timedelta(days=days)
        return EmailLog.objects.filter(
            status=EmailLog.Status.COMPLAINED,
            created_at__gte=cutoff
        ).order_by('-complained_at')


# Import models at module level for F expression
from django.db import models
