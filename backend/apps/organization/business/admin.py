# apps/organization/business/admin.py
"""
Business Admin Configuration.
"""

from django.contrib import admin

from apps.organization.business.models import (
    BusinessAccount,
    BusinessProfile,
    BusinessSlugHistory,
)


class BusinessProfileInline(admin.StackedInline):
    """Inline admin for BusinessProfile."""

    model = BusinessProfile
    can_delete = False
    verbose_name_plural = "Profile"
    fieldsets = (
        ("Display", {"fields": ("display_name", "tagline", "description")}),
        ("Media", {"fields": ("logo", "cover_image")}),
        ("Contact", {"fields": ("website", "contact_email", "contact_phone")}),
        (
            "Details",
            {"fields": ("industry", "company_size", "founded_year", "social_links")},
        ),
        ("Visibility", {"fields": ("is_public",)}),
    )


class BusinessSlugHistoryInline(admin.TabularInline):
    """Inline admin for BusinessSlugHistory."""

    model = BusinessSlugHistory
    extra = 0
    readonly_fields = ("old_slug", "changed_at")
    can_delete = False


@admin.register(BusinessAccount)
class BusinessAccountAdmin(admin.ModelAdmin):
    """Admin configuration for BusinessAccount."""

    list_display = (
        "legal_name",
        "slug",
        "country",
        "status",
        "verification_status",
        "max_members",
        "open_member_request",
        "created_at",
    )
    list_filter = ("status", "verification_status", "business_type", "country", "max_members", "open_member_request")
    list_editable = ("max_members", "open_member_request")
    actions = ["enable_team_membership", "disable_team_membership", "enable_member_requests", "disable_member_requests"]
    search_fields = ("legal_name", "slug", "registration_number", "tax_id")
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "verified_at",
        "verified_by",
        "deleted_at",
        "deleted_by",
    )
    inlines = [BusinessProfileInline, BusinessSlugHistoryInline]
    ordering = ["-created_at"]

    fieldsets = (
        (None, {"fields": ("id", "slug", "legal_name")}),
        (
            "Legal Information",
            {"fields": ("registration_number", "tax_id", "country", "legal_address")},
        ),
        ("Classification", {"fields": ("business_type",)}),
        ("Membership", {"fields": ("max_members", "open_member_request")}),
        ("Status", {"fields": ("status", "is_deleted")}),
        (
            "Verification",
            {
                "fields": (
                    "verification_status",
                    "verified_at",
                    "verified_by",
                ),
            },
        ),
        ("Settings", {"fields": ("settings",), "classes": ("collapse",)}),
        (
            "Audit",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "created_by",
                    "updated_by",
                    "deleted_at",
                    "deleted_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.action(description="Enable team membership (max_members=6)")
    def enable_team_membership(self, request, queryset):
        updated = queryset.update(max_members=6)
        self.message_user(request, f"{updated} businesses updated to max_members=6.")

    @admin.action(description="Disable team membership (max_members=1)")
    def disable_team_membership(self, request, queryset):
        updated = queryset.update(max_members=1)
        self.message_user(request, f"{updated} businesses set to owner-only (max_members=1).")

    @admin.action(description="Enable member requests (open_member_request=True)")
    def enable_member_requests(self, request, queryset):
        updated = queryset.update(open_member_request=True)
        self.message_user(request, f"{updated} businesses now accept member requests.")

    @admin.action(description="Disable member requests (open_member_request=False)")
    def disable_member_requests(self, request, queryset):
        updated = queryset.update(open_member_request=False)
        self.message_user(request, f"{updated} businesses no longer accept member requests.")

    def get_queryset(self, request):
        """Include soft-deleted businesses in admin."""
        return BusinessAccount.all_objects.all()


@admin.register(BusinessSlugHistory)
class BusinessSlugHistoryAdmin(admin.ModelAdmin):
    """Admin configuration for BusinessSlugHistory."""

    list_display = ("old_slug", "business", "changed_at")
    search_fields = ("old_slug", "business__legal_name", "business__slug")
    readonly_fields = ("old_slug", "business", "changed_at")
    ordering = ["-changed_at"]
