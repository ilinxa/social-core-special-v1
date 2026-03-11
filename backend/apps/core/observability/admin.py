"""
Observability Admin Configuration
=================================
Admin interfaces for observability models.

AuditLog is read-only - no modifications allowed through admin.
"""

from django.contrib import admin
from django.utils.html import format_html

from apps.core.observability.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Admin interface for viewing audit logs.

    Read-only - no modifications allowed.
    """

    list_display = [
        "timestamp",
        "colored_outcome",
        "action",
        "actor_display",
        "resource_display",
        "ip_address",
    ]

    list_filter = [
        "outcome",
        "action",
        "actor_type",
        ("timestamp", admin.DateFieldListFilter),
    ]

    search_fields = [
        "actor_email",
        "resource_repr",
        "ip_address",
        "request_id",
    ]

    readonly_fields = [
        "id",
        "timestamp",
        "actor_id",
        "actor_email",
        "actor_type",
        "action",
        "resource_type",
        "resource_id",
        "resource_repr",
        "ip_address",
        "user_agent",
        "request_id",
        "outcome",
        "details",
        "changes",
    ]

    ordering = ["-timestamp"]

    date_hierarchy = "timestamp"

    def has_add_permission(self, request):
        """Prevent adding audit logs through admin."""
        return False

    def has_change_permission(self, request, obj=None):
        """Prevent modifying audit logs through admin."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deleting audit logs through admin."""
        return False

    def colored_outcome(self, obj):
        """Display outcome with color coding."""
        colors = {
            "success": "green",
            "failure": "red",
            "denied": "orange",
        }
        color = colors.get(obj.outcome, "gray")
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.outcome.upper(),
        )

    colored_outcome.short_description = "Outcome"

    def actor_display(self, obj):
        """Display actor email or type."""
        if obj.actor_email:
            return obj.actor_email
        return f"[{obj.actor_type}]"

    actor_display.short_description = "Actor"

    def resource_display(self, obj):
        """Display resource type and representation."""
        if obj.resource_repr:
            return f"{obj.resource_type}: {obj.resource_repr[:30]}"
        return obj.resource_type or "-"

    resource_display.short_description = "Resource"
