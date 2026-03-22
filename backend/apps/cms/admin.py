# apps/cms/admin.py
"""
CMS Django Admin Configuration
================================
Superuser-only interface for managing CMS structure.
"""

from django.contrib import admin

from apps.cms.models import (
    BlockTemplate,
    CMSApiKey,
    ContentVersion,
    MediaFile,
    MediaFolder,
    Page,
    PageSectionPlacement,
    SectionBlockPlacement,
    SectionTemplate,
    Site,
)


class PageSectionPlacementInline(admin.TabularInline):
    model = PageSectionPlacement
    extra = 0
    fields = ["template", "order", "is_required", "is_visible", "label"]
    readonly_fields = []
    ordering = ["order"]


class SectionBlockPlacementInline(admin.TabularInline):
    model = SectionBlockPlacement
    extra = 0
    fields = ["template", "order", "is_required", "is_visible", "label", "status"]
    readonly_fields = ["status"]
    ordering = ["order"]


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ["name", "owner_type", "domain", "is_active", "created_at"]
    list_filter = ["owner_type", "is_active"]
    search_fields = ["name", "domain"]
    readonly_fields = ["id", "created_at", "updated_at", "created_by", "updated_by"]
    fieldsets = [
        ("Basic Info", {"fields": ["name", "slug", "domain", "description"]}),
        ("Ownership", {"fields": ["owner_type", "owner_id"]}),
        (
            "Settings",
            {"fields": ["default_locale", "metadata", "is_active", "homepage"]},
        ),
        (
            "Audit",
            {"fields": ["id", "created_at", "updated_at", "created_by", "updated_by"]},
        ),
    ]


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ["title", "site", "path", "status", "published_at", "order"]
    list_filter = ["site", "status", "page_type"]
    search_fields = ["title", "slug", "path"]
    readonly_fields = ["id", "published_at", "created_at", "updated_at"]
    inlines = [PageSectionPlacementInline]
    fieldsets = [
        ("Basic Info", {"fields": ["title", "slug", "path", "description"]}),
        ("Site", {"fields": ["site"]}),
        ("Type & SEO", {"fields": ["page_type", "metadata"]}),
        (
            "Status",
            {
                "fields": [
                    "status",
                    "published_at",
                    "order",
                    "is_required",
                    "is_visible",
                ]
            },
        ),
    ]
    actions = ["publish_pages", "archive_pages"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("site")

    @admin.action(description="Publish selected pages")
    def publish_pages(self, request, queryset):
        pass

    @admin.action(description="Archive selected pages")
    def archive_pages(self, request, queryset):
        queryset.update(status="archived")


@admin.register(SectionTemplate)
class SectionTemplateAdmin(admin.ModelAdmin):
    list_display = ["display_name", "section_type", "slug"]
    search_fields = ["name", "display_name"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(BlockTemplate)
class BlockTemplateAdmin(admin.ModelAdmin):
    list_display = ["display_name", "block_type", "schema_version", "slug"]
    search_fields = ["name", "display_name"]
    readonly_fields = ["id", "schema_version", "created_at", "updated_at"]


@admin.register(PageSectionPlacement)
class PageSectionPlacementAdmin(admin.ModelAdmin):
    list_display = ["label_or_template", "page", "order", "is_visible"]
    list_filter = ["page__site", "template"]
    search_fields = ["label", "page__title"]
    inlines = [SectionBlockPlacementInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("page", "template")

    @admin.display(description="Label")
    def label_or_template(self, obj):
        return obj.label or obj.template.display_name


@admin.register(SectionBlockPlacement)
class SectionBlockPlacementAdmin(admin.ModelAdmin):
    list_display = ["label_or_template", "status", "order"]
    list_filter = ["template", "status"]
    readonly_fields = ["template", "published_content", "section_placement"]

    @admin.display(description="Label")
    def label_or_template(self, obj):
        return obj.label or obj.template.display_name


@admin.register(ContentVersion)
class ContentVersionAdmin(admin.ModelAdmin):
    list_display = [
        "block_placement",
        "version_number",
        "action",
        "created_by",
        "created_at",
    ]
    list_filter = ["action"]
    readonly_fields = [
        "block_placement",
        "content_snapshot",
        "version_number",
        "action",
        "created_by",
        "created_at",
        "notes",
    ]


@admin.register(MediaFile)
class MediaFileAdmin(admin.ModelAdmin):
    list_display = [
        "original_filename",
        "mime_type",
        "file_size",
        "folder",
        "is_tombstoned",
    ]
    list_filter = ["mime_type", "is_tombstoned"]
    search_fields = ["original_filename", "title", "alt_text"]
    readonly_fields = ["id", "storage_key", "created_at", "updated_at"]


@admin.register(MediaFolder)
class MediaFolderAdmin(admin.ModelAdmin):
    list_display = ["name", "path", "owner_type"]
    search_fields = ["name", "path"]


@admin.register(CMSApiKey)
class CMSApiKeyAdmin(admin.ModelAdmin):
    list_display = ["name", "site", "key_prefix", "is_active", "last_used_at"]
    list_filter = ["is_active", "site"]
    readonly_fields = ["key_prefix", "key_hash", "last_used_at"]
