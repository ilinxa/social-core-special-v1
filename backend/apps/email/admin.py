"""
Email Admin Configuration
=========================
Django admin interface for email templates and logs.
"""

from django.contrib import admin
from django.utils.html import format_html

from apps.email.models import EmailLog, EmailTemplate


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    """
    Admin configuration for EmailTemplate.

    Features:
        - List view with key fields
        - Category and status filtering
        - Search by name, subject, description
        - Read-only versioning fields
    """

    list_display = [
        "name",
        "category",
        "subject_preview",
        "is_active_badge",
        "version",
        "is_current",
        "updated_at",
    ]
    list_filter = ["is_active", "is_current", "category"]
    search_fields = ["name", "subject", "description"]
    readonly_fields = ["version", "is_current", "created_at", "updated_at"]
    ordering = ["category", "name", "-version"]

    fieldsets = (
        (None, {"fields": ("name", "category", "description", "is_active")}),
        (
            "Content",
            {
                "fields": ("subject", "html_body", "text_body"),
                "description": (
                    "Use Django template syntax: {{ variable_name }}. "
                    "Text body is auto-generated from HTML if left empty."
                ),
            },
        ),
        (
            "Variables",
            {
                "fields": ("variables",),
                "description": (
                    "JSON schema defining expected variables. "
                    'Example: {"user_name": {"type": "string", "required": true}}'
                ),
            },
        ),
        (
            "Versioning",
            {
                "fields": ("version", "is_current", "created_at", "updated_at"),
                "classes": ("collapse",),
                "description": "Each edit creates a new version. Previous versions are preserved.",
            },
        ),
    )

    def subject_preview(self, obj):
        """Show truncated subject."""
        if len(obj.subject) > 50:
            return obj.subject[:50] + "..."
        return obj.subject

    subject_preview.short_description = "Subject"

    def is_active_badge(self, obj):
        """Show colored badge for active status."""
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">Active</span>'
            )
        return format_html('<span style="color: red;">Inactive</span>')

    is_active_badge.short_description = "Status"

    def get_queryset(self, request):
        """Default to showing only current versions."""
        qs = super().get_queryset(request)
        # Show all versions in admin (can filter to current)
        return qs


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    """
    Admin configuration for EmailLog.

    Features:
        - List view with status badges
        - Status and date filtering
        - Search by email, subject, message ID
        - All fields read-only (audit log)
        - Date hierarchy for time-based browsing
    """

    list_display = [
        "id_short",
        "to_email",
        "template_name",
        "subject_preview",
        "status_badge",
        "created_at",
        "sent_at",
    ]
    list_filter = ["status", "template_name", "created_at"]
    search_fields = ["to_email", "subject", "message_id", "id"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]

    # All fields read-only - this is an audit log
    readonly_fields = [
        "id",
        "to_email",
        "from_email",
        "reply_to",
        "template",
        "template_name",
        "template_version",
        "subject",
        "html_body",
        "text_body",
        "context",
        "status",
        "message_id",
        "error_message",
        "error_code",
        "retry_count",
        "max_retries",
        "next_retry_at",
        "queued_at",
        "sent_at",
        "delivered_at",
        "bounced_at",
        "complained_at",
        "failed_at",
        "bounce_type",
        "bounce_subtype",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        ("Recipient", {"fields": ("id", "to_email", "from_email", "reply_to")}),
        ("Template", {"fields": ("template", "template_name", "template_version")}),
        (
            "Content",
            {
                "fields": ("subject", "html_body", "text_body", "context"),
                "classes": ("collapse",),
            },
        ),
        ("Status", {"fields": ("status", "message_id", "error_message", "error_code")}),
        (
            "Retry Info",
            {
                "fields": ("retry_count", "max_retries", "next_retry_at"),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "queued_at",
                    "sent_at",
                    "delivered_at",
                    "bounced_at",
                    "complained_at",
                    "failed_at",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Bounce Details",
            {"fields": ("bounce_type", "bounce_subtype"), "classes": ("collapse",)},
        ),
    )

    def id_short(self, obj):
        """Show shortened UUID."""
        return str(obj.id)[:8] + "..."

    id_short.short_description = "ID"

    def subject_preview(self, obj):
        """Show truncated subject."""
        if len(obj.subject) > 30:
            return obj.subject[:30] + "..."
        return obj.subject

    subject_preview.short_description = "Subject"

    def status_badge(self, obj):
        """Show colored badge for status."""
        colors = {
            "pending": "#6c757d",  # Gray
            "queued": "#17a2b8",  # Blue
            "sending": "#17a2b8",  # Blue
            "sent": "#28a745",  # Green
            "delivered": "#28a745",  # Green
            "bounced": "#dc3545",  # Red
            "complained": "#fd7e14",  # Orange
            "failed": "#dc3545",  # Red
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.status.upper(),
        )

    status_badge.short_description = "Status"

    def has_add_permission(self, request):
        """Disable adding logs manually."""
        return False

    def has_change_permission(self, request, obj=None):
        """Disable editing logs."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Allow deletion for cleanup."""
        return True
