"""
Email Models
============
Data models for email templates and delivery tracking.

Models:
    - EmailTemplate: Admin-manageable versioned email templates
    - EmailLog: Audit log for all sent emails with full lifecycle tracking
"""

import uuid

from django.db import models

from apps.core.models import TimeStampedModel


class EmailTemplate(TimeStampedModel):
    """
    Admin-manageable email templates with versioning.

    Templates use Django template syntax: {{ variable_name }}
    Variables are validated against the `variables` JSON schema.

    Versioning Strategy:
        - Each edit creates a NEW row with incremented version
        - Old versions are marked is_current=False
        - This preserves complete history for audit/debugging

    Fields:
        name: Unique identifier (e.g., 'welcome', 'password_reset')
        subject: Email subject line (supports {{ variables }})
        html_body: HTML email content (supports {{ variables }})
        text_body: Plain text fallback (auto-generated from HTML if empty)
        variables: JSON schema defining expected variables
        category: For organization (auth, transactional, marketing)
        is_active: Inactive templates cannot be used
        version: Version number (auto-incremented)
        is_current: True only for the latest version
    """

    # Identification
    name = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Unique identifier (e.g., 'welcome', 'password_reset')"
    )

    # Content
    subject = models.CharField(
        max_length=255,
        help_text="Email subject line. Supports {{ variables }}"
    )
    html_body = models.TextField(
        help_text="HTML email content. Supports {{ variables }}"
    )
    text_body = models.TextField(
        blank=True,
        help_text="Plain text fallback. Auto-generated from HTML if empty."
    )

    # Variable schema for validation
    variables = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "JSON schema defining expected variables. "
            "Example: {'user_name': {'type': 'string', 'required': true}}"
        )
    )

    # Metadata
    description = models.TextField(
        blank=True,
        help_text="Internal description for admins"
    )
    category = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        help_text="Category for organization (auth, transactional, marketing)"
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Inactive templates cannot be used"
    )

    # Versioning
    version = models.PositiveIntegerField(
        default=1,
        help_text="Version number (new row created on each edit)"
    )
    is_current = models.BooleanField(
        default=True,
        db_index=True,
        help_text="True for the latest version of each template"
    )

    class Meta:
        db_table = 'email_templates'
        ordering = ['category', 'name', '-version']
        verbose_name = 'email template'
        verbose_name_plural = 'email templates'
        constraints = [
            # Enforce unique (name, version) pairs
            models.UniqueConstraint(
                fields=['name', 'version'],
                name='unique_template_version'
            ),
            # Only one current version per template name
            models.UniqueConstraint(
                fields=['name'],
                condition=models.Q(is_current=True),
                name='unique_current_template'
            ),
        ]

    def __str__(self):
        return f"{self.name} (v{self.version})"

    def __repr__(self):
        return f"<EmailTemplate name={self.name} version={self.version}>"

    def save(self, *args, **kwargs):
        """
        Versioning strategy: Clone on edit.

        When updating an existing template:
        1. Mark current version as not current
        2. Create new row with incremented version

        This preserves complete history.
        """
        if self.pk:
            # Editing existing template - create new version
            old = EmailTemplate.objects.get(pk=self.pk)

            # Archive the old version
            EmailTemplate.objects.filter(pk=self.pk).update(is_current=False)

            # Create new version (new row)
            self.pk = None  # Force INSERT
            self.version = old.version + 1
            self.is_current = True

        super().save(*args, **kwargs)


class EmailLog(TimeStampedModel):
    """
    Audit log for all sent emails.

    Tracks the full lifecycle: pending → queued → sending → sent → delivered/bounced/complained

    Fields:
        id: UUID for external reference
        to_email: Recipient (no FK to User - emails can go to non-users)
        from_email: Sender address
        reply_to: Reply-to address
        template: FK to EmailTemplate (nullable - for raw emails)
        template_name: Template name at time of send
        template_version: Template version at time of send
        subject: Rendered subject
        html_body: Rendered HTML content
        text_body: Rendered text content
        context: Variables used for rendering (for debugging)
        status: Current status in lifecycle
        message_id: Provider message ID (SES Message-ID)
        error_message: Error details if failed
        error_code: Error code if failed
        retry_count: Number of retry attempts
        max_retries: Maximum retries allowed
        next_retry_at: When to attempt next retry
        queued_at, sent_at, delivered_at, bounced_at, complained_at, failed_at: Timestamps
        bounce_type: permanent/transient (from webhook)
        bounce_subtype: Detailed bounce reason (from webhook)
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        QUEUED = 'queued', 'Queued'
        SENDING = 'sending', 'Sending'
        SENT = 'sent', 'Sent'
        DELIVERED = 'delivered', 'Delivered'
        BOUNCED = 'bounced', 'Bounced'
        COMPLAINED = 'complained', 'Complained'
        FAILED = 'failed', 'Failed'

    # Use UUID for external reference
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Recipient (no FK to User - emails can go to non-users)
    to_email = models.EmailField(db_index=True)
    from_email = models.EmailField()
    reply_to = models.EmailField(blank=True)

    # Template reference (for tracking, template may change later)
    template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs'
    )
    template_name = models.CharField(
        max_length=100,
        help_text="Template name at time of send"
    )
    template_version = models.PositiveIntegerField(
        default=1,
        help_text="Template version at time of send"
    )

    # Rendered content (stored for debugging/resend)
    subject = models.CharField(max_length=255)
    html_body = models.TextField()
    text_body = models.TextField(blank=True)

    # Context used for rendering (for debugging)
    context = models.JSONField(
        default=dict,
        blank=True,
        help_text="Variables used to render template"
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )

    # SES tracking
    message_id = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Provider message ID (SES Message-ID)"
    )

    # Error tracking
    error_message = models.TextField(blank=True)
    error_code = models.CharField(max_length=50, blank=True)

    # Retry tracking
    retry_count = models.PositiveSmallIntegerField(default=0)
    max_retries = models.PositiveSmallIntegerField(default=3)
    next_retry_at = models.DateTimeField(null=True, blank=True)

    # Timestamps for lifecycle
    queued_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    bounced_at = models.DateTimeField(null=True, blank=True)
    complained_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)

    # Bounce details (populated by webhook)
    bounce_type = models.CharField(
        max_length=20,
        blank=True,
        help_text="permanent/transient"
    )
    bounce_subtype = models.CharField(
        max_length=50,
        blank=True,
        help_text="e.g., General, NoEmail, Suppressed"
    )

    class Meta:
        db_table = 'email_logs'
        ordering = ['-created_at']
        verbose_name = 'email log'
        verbose_name_plural = 'email logs'
        indexes = [
            models.Index(
                fields=['to_email', 'created_at'],
                name='emaillogs_to_created_idx'
            ),
            models.Index(
                fields=['status', 'created_at'],
                name='emaillogs_status_created_idx'
            ),
            models.Index(
                fields=['template_name', 'created_at'],
                name='emaillogs_tpl_created_idx'
            ),
            models.Index(
                fields=['message_id'],
                name='emaillogs_message_id_idx'
            ),
            # Partial index for retry queue scanning (only failed emails)
            models.Index(
                fields=['next_retry_at'],
                condition=models.Q(status='failed'),
                name='emaillogs_failed_retry_idx'
            ),
        ]

    def __str__(self):
        return f"{self.template_name} -> {self.to_email} ({self.status})"

    def __repr__(self):
        return f"<EmailLog id={self.id} status={self.status}>"

    @property
    def can_retry(self):
        """Check if this email can be retried."""
        return (
            self.status == self.Status.FAILED and
            self.retry_count < self.max_retries
        )
