# apps/cms/api/serializers.py
"""
CMS Serializers
================
Input (validation) and Output (response shaping) serializers.
"""

from rest_framework import serializers
from apps.cms.models import (
    Site, Page, SectionTemplate, BlockTemplate,
    PageSectionPlacement, SectionBlockPlacement,
    ContentVersion, MediaFolder, MediaFile, MediaUsage, CMSApiKey,
)


# ---------------------------------------------------------------------------
# Input Serializers
# ---------------------------------------------------------------------------

class SiteCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    slug = serializers.SlugField(max_length=100)
    domain = serializers.CharField(max_length=255, required=False, default="")
    description = serializers.CharField(required=False, default="")
    metadata = serializers.JSONField(required=False, default=None)


class SiteUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    domain = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False)
    metadata = serializers.JSONField(required=False)
    is_active = serializers.BooleanField(required=False)


class PageCreateSerializer(serializers.Serializer):
    site_id = serializers.UUIDField()
    title = serializers.CharField(max_length=255)
    slug = serializers.SlugField(max_length=100)
    path = serializers.CharField(max_length=500)
    page_type = serializers.CharField(max_length=50)
    order = serializers.IntegerField(min_value=0)
    description = serializers.CharField(required=False, default="")
    metadata = serializers.JSONField(required=False, default=None)
    is_required = serializers.BooleanField(required=False, default=False)


class PageUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False)
    path = serializers.CharField(max_length=500, required=False)
    metadata = serializers.JSONField(required=False)
    is_visible = serializers.BooleanField(required=False)


class SectionTemplateCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    display_name = serializers.CharField(max_length=255)
    slug = serializers.SlugField(max_length=100)
    section_type = serializers.CharField(max_length=50)
    description = serializers.CharField(required=False, default="")
    metadata = serializers.JSONField(required=False, default=None)
    ui_config = serializers.JSONField(required=False, default=None)


class BlockTemplateCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    display_name = serializers.CharField(max_length=255)
    slug = serializers.SlugField(max_length=100)
    block_type = serializers.CharField(max_length=50)
    schema = serializers.JSONField()
    description = serializers.CharField(required=False, default="")
    default_content = serializers.JSONField(required=False, default=None)
    metadata = serializers.JSONField(required=False, default=None)
    ui_config = serializers.JSONField(required=False, default=None)


class BlockSchemaUpdateSerializer(serializers.Serializer):
    schema = serializers.JSONField()


class DraftContentUpdateSerializer(serializers.Serializer):
    draft_content = serializers.JSONField()


class ReorderSerializer(serializers.Serializer):
    ordered_ids = serializers.ListField(child=serializers.UUIDField())


class MediaUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    folder_id = serializers.UUIDField(required=False, default=None)
    alt_text = serializers.CharField(max_length=255, required=False, default="")
    title = serializers.CharField(max_length=255, required=False, default="")


class MediaUpdateSerializer(serializers.Serializer):
    alt_text = serializers.CharField(max_length=255, required=False)
    title = serializers.CharField(max_length=255, required=False)
    folder_id = serializers.UUIDField(required=False)


class ApiKeyCreateSerializer(serializers.Serializer):
    site_id = serializers.UUIDField()
    name = serializers.CharField(max_length=255)
    allowed_origins = serializers.ListField(
        child=serializers.CharField(), required=False, default=list,
    )
    rate_limit = serializers.IntegerField(min_value=1, required=False, default=60)
    expires_at = serializers.DateTimeField(required=False, default=None)


class ApiKeyUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    allowed_origins = serializers.ListField(
        child=serializers.CharField(), required=False,
    )
    is_active = serializers.BooleanField(required=False)
    rate_limit = serializers.IntegerField(min_value=1, required=False)


class PageImportSerializer(serializers.Serializer):
    """Import data matching export format (spec Section 10.1)."""
    export_version = serializers.CharField()
    page = serializers.JSONField()


# ---------------------------------------------------------------------------
# Output Serializers
# ---------------------------------------------------------------------------

class SiteOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = [
            "id", "owner_type", "owner_id", "name", "slug", "domain",
            "description", "default_locale", "metadata", "is_active",
            "created_at", "updated_at",
        ]


class PageOutputSerializer(serializers.ModelSerializer):
    site_slug = serializers.CharField(source="site.slug", read_only=True)

    class Meta:
        model = Page
        fields = [
            "id", "site", "site_slug", "title", "slug", "description",
            "path", "page_type", "metadata", "status", "published_at",
            "order", "is_required", "is_visible", "created_at", "updated_at",
        ]


class SectionTemplateOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectionTemplate
        fields = [
            "id", "name", "display_name", "slug", "description",
            "section_type", "metadata", "ui_config", "created_at",
        ]


class BlockTemplateOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlockTemplate
        fields = [
            "id", "name", "display_name", "slug", "description",
            "block_type", "schema", "schema_version", "default_content",
            "metadata", "ui_config", "created_at",
        ]


class SectionPlacementOutputSerializer(serializers.ModelSerializer):
    template = SectionTemplateOutputSerializer(read_only=True)

    class Meta:
        model = PageSectionPlacement
        fields = [
            "id", "page", "template", "label", "order",
            "is_required", "is_visible", "config_overrides",
            "created_at",
        ]


class BlockPlacementOutputSerializer(serializers.ModelSerializer):
    template = BlockTemplateOutputSerializer(read_only=True)

    class Meta:
        model = SectionBlockPlacement
        fields = [
            "id", "section_placement", "template", "label", "order",
            "is_required", "is_visible", "config_overrides",
            "schema_version_validated", "draft_content", "published_content",
            "status", "created_at", "updated_at",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Public API: exclude draft_content
        if self.context.get("public"):
            data.pop("draft_content", None)
        return data


class PageDetailOutputSerializer(serializers.ModelSerializer):
    """Page with full tree: sections -> blocks."""
    section_placements = serializers.SerializerMethodField()
    site_slug = serializers.CharField(source="site.slug", read_only=True)

    class Meta:
        model = Page
        fields = [
            "id", "site", "site_slug", "title", "slug", "description",
            "path", "page_type", "metadata", "status", "published_at",
            "order", "is_required", "is_visible",
            "section_placements", "created_at", "updated_at",
        ]

    def get_section_placements(self, obj):
        placements = obj.section_placements.order_by("order")
        context = self.context
        result = []
        for sp in placements:
            sp_data = SectionPlacementOutputSerializer(sp).data
            sp_data["block_placements"] = BlockPlacementOutputSerializer(
                sp.block_placements.order_by("order"),
                many=True,
                context=context,
            ).data
            result.append(sp_data)
        return result


class ContentVersionOutputSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(
        source="created_by.username", read_only=True,
    )

    class Meta:
        model = ContentVersion
        fields = [
            "id", "block_placement", "content_snapshot", "version_number",
            "action", "created_by", "created_by_username", "created_at", "notes",
        ]


class MediaFolderOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaFolder
        fields = [
            "id", "owner_type", "owner_id", "name", "slug",
            "parent", "path", "created_at",
        ]


class MediaFileOutputSerializer(serializers.ModelSerializer):
    usage_count = serializers.SerializerMethodField()

    class Meta:
        model = MediaFile
        fields = [
            "id", "owner_type", "owner_id", "folder", "storage_key",
            "original_filename", "mime_type", "file_size", "width", "height",
            "alt_text", "title", "metadata", "is_tombstoned",
            "usage_count", "created_at", "updated_at",
        ]

    def get_usage_count(self, obj):
        return MediaUsage.objects.filter(media_file=obj).count()


class MediaUsageOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaUsage
        fields = [
            "id", "media_file", "block_placement", "field_key",
            "content_layer", "created_at",
        ]


class ApiKeyOutputSerializer(serializers.ModelSerializer):
    """Output for list/detail — never includes full key."""
    class Meta:
        model = CMSApiKey
        fields = [
            "id", "site", "name", "key_prefix", "allowed_origins",
            "is_active", "expires_at", "last_used_at", "rate_limit",
            "created_at",
        ]


class ApiKeyCreatedOutputSerializer(serializers.ModelSerializer):
    """Output for creation — includes key field (added by view)."""
    class Meta:
        model = CMSApiKey
        fields = [
            "id", "site", "name", "key_prefix", "allowed_origins",
            "is_active", "expires_at", "rate_limit", "created_at",
        ]


class PublishErrorOutputSerializer(serializers.Serializer):
    """Structured publish validation error response."""
    section_placement_id = serializers.UUIDField()
    block_placement_id = serializers.UUIDField()
    block_template = serializers.CharField()
    field_key = serializers.CharField()
    error_type = serializers.CharField()
    message = serializers.CharField()


class PageExportOutputSerializer(serializers.Serializer):
    """Export format matching spec Section 10.1."""
    export_version = serializers.CharField()
    exported_at = serializers.DateTimeField()
    exported_by = serializers.CharField()
    source_site = serializers.CharField()
    source_owner_type = serializers.CharField()
    source_owner_id = serializers.CharField()
    page = serializers.JSONField()
