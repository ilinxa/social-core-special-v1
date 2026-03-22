# apps/organization/platform/admin.py
"""
Platform Admin Configuration.
"""

from django.contrib import admin

from apps.organization.platform.models import PlatformAccount, PlatformProfile


class PlatformProfileInline(admin.StackedInline):
    """Inline admin for PlatformProfile."""

    model = PlatformProfile
    can_delete = False
    verbose_name_plural = "Profile"
    fieldsets = (
        ("Branding", {"fields": ("name", "tagline", "description", "logo", "favicon")}),
        ("Colors", {"fields": ("primary_color", "secondary_color")}),
        ("Contact", {"fields": ("contact_email", "contact_phone", "address")}),
        ("Social", {"fields": ("social_links",)}),
    )


@admin.register(PlatformAccount)
class PlatformAccountAdmin(admin.ModelAdmin):
    """Admin configuration for PlatformAccount."""

    list_display = (
        "id",
        "is_configured",
        "max_members",
        "open_member_request",
        "created_at",
        "updated_at",
    )
    readonly_fields = (
        "id",
        "singleton_key",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    )
    inlines = [PlatformProfileInline]

    fieldsets = (
        (None, {"fields": ("id", "singleton_key", "is_configured")}),
        ("Membership", {"fields": ("max_members", "open_member_request")}),
        ("Settings", {"fields": ("settings",)}),
        (
            "Audit",
            {
                "fields": ("created_at", "updated_at", "created_by", "updated_by"),
                "classes": ("collapse",),
            },
        ),
    )

    def has_add_permission(self, request):
        """Only allow one platform account."""
        return not PlatformAccount.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of platform account."""
        return False
