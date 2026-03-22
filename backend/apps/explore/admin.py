from django.contrib import admin

from apps.explore.models import SuggestedTag


@admin.register(SuggestedTag)
class SuggestedTagAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "category", "usage_count", "is_active"]
    list_filter = ["category", "is_active"]
    search_fields = ["name", "slug"]
    ordering = ["-usage_count", "name"]
