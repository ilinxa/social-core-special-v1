# apps/rbac/admin.py
"""
RBAC Admin Configuration
"""

from django.contrib import admin

from apps.rbac.models import Membership, Permission, Role, RolePermission


class RolePermissionInline(admin.TabularInline):
    """Inline for role permissions."""

    model = RolePermission
    extra = 1
    autocomplete_fields = ["permission"]


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    """Admin for Permission model."""

    list_display = ["code", "name", "category", "applicable_scopes"]
    list_filter = ["category"]
    search_fields = ["code", "name", "description"]
    ordering = ["category", "code"]
    readonly_fields = ["id"]

    fieldsets = (
        (None, {"fields": ("id", "code", "name", "category")}),
        ("Details", {"fields": ("description", "applicable_scopes")}),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin for Role model."""

    list_display = ["name", "account_type", "account_id", "level", "is_system_role"]
    list_filter = ["account_type", "is_system_role", "level"]
    search_fields = ["name", "description"]
    ordering = ["account_type", "account_id", "level"]
    readonly_fields = ["id", "created_at", "updated_at"]
    inlines = [RolePermissionInline]

    fieldsets = (
        (None, {"fields": ("id", "name", "description")}),
        ("Account", {"fields": ("account_type", "account_id")}),
        ("Configuration", {"fields": ("level", "is_system_role")}),
        (
            "Audit",
            {
                "fields": ("created_at", "updated_at", "created_by", "updated_by"),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    """Admin for RolePermission model."""

    list_display = ["role", "permission", "scope"]
    list_filter = ["scope", "role__account_type"]
    search_fields = ["role__name", "permission__code"]
    autocomplete_fields = ["role", "permission"]
    readonly_fields = ["id"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("role", "permission")


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    """Admin for Membership model."""

    list_display = [
        "user",
        "account_type",
        "account_id",
        "role",
        "is_owner",
        "status",
        "joined_at",
    ]
    list_filter = ["account_type", "status", "is_owner"]
    search_fields = ["user__email", "user__username", "role__name"]
    autocomplete_fields = ["user", "role"]
    readonly_fields = [
        "id",
        "joined_at",
        "status_changed_at",
        "created_at",
        "updated_at",
    ]
    ordering = ["-joined_at"]

    fieldsets = (
        (None, {"fields": ("id", "user", "role")}),
        ("Account", {"fields": ("account_type", "account_id")}),
        ("Status", {"fields": ("is_owner", "status", "status_reason")}),
        (
            "Timestamps",
            {
                "fields": ("joined_at", "status_changed_at", "status_changed_by"),
                "classes": ("collapse",),
            },
        ),
        (
            "Audit",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "is_deleted",
                    "deleted_at",
                    "deleted_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        """Include soft-deleted memberships in admin."""
        return Membership.all_objects.select_related("user", "role").all()
