# apps/cms/models.py
"""
CMS Models
==========
Site, Page, SectionTemplate, BlockTemplate, PageSectionPlacement,
SectionBlockPlacement, ContentVersion, MediaFolder, MediaFile,
MediaUsage, CMSApiKey.
"""

import hashlib
import secrets
from django.db import models
from django.conf import settings
from apps.core.models import UUIDModel, AuditModel, TimeStampedModel, UserStampedModel
from apps.core.constants import OwnerType
from apps.cms.constants import (
    PageStatus,
    BlockPlacementStatus,
    ContentVersionAction,
    ContentLayer,
    API_KEY_PREFIX,
)
from apps.cms.managers import (
    SiteManager,
    PageManager,
    SectionTemplateManager,
    BlockTemplateManager,
    MediaFolderManager,
    MediaFileManager,
    CMSApiKeyManager,
)


class Site(UUIDModel, AuditModel):
    """
    Website container — logical grouping of pages managed by the CMS.

    Currently platform-only. Uses owner_type/owner_id polymorphic pattern
    (same as FormTemplate) for future business account expansion.

    INVARIANT: owner_id refers to an account record (PlatformAccount/BusinessAccount), never a user.
    """

    # Ownership (polymorphic — same pattern as FormTemplate)
    owner_type = models.CharField(
        max_length=20,
        choices=OwnerType.choices,
        db_index=True,
        help_text="Which account type owns this site",
    )
    owner_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID of owning account record (PlatformAccount.id or BusinessAccount.id)",
    )

    # Identity
    name = models.CharField(max_length=255, help_text="Display name of the site")
    slug = models.SlugField(max_length=100, help_text="URL-safe identifier")
    domain = models.CharField(
        max_length=255, blank=True, default="", help_text="Associated domain"
    )
    description = models.TextField(blank=True, default="", help_text="Internal description")

    # Configuration
    default_locale = models.CharField(
        max_length=10, default="en", help_text="Default language code"
    )
    metadata = models.JSONField(
        null=True, blank=True, help_text="SEO defaults, theme settings, global config"
    )
    is_active = models.BooleanField(default=True, help_text="Whether the site is live")

    # Homepage reference
    homepage = models.ForeignKey(
        "cms.Page",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Designated homepage for this site",
    )

    # Managers
    objects = SiteManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "cms_site"
        verbose_name = "CMS Site"
        verbose_name_plural = "CMS Sites"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner_type", "owner_id", "slug"],
                condition=models.Q(is_deleted=False),
                name="unique_cms_site_slug_per_owner",
            ),
        ]
        indexes = [
            models.Index(fields=["owner_type", "owner_id"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.name


class Page(UUIDModel, AuditModel):
    """
    A routable page within a Site. Structure (sections, blocks) is defined
    by superuser and immutable by admins. Admins only edit content values.

    INVARIANT: If is_required=True, cannot set is_visible=False and cannot delete.
    INVARIANT: Unique(site, slug), Unique(site, path), Unique(site, order) — all filtered to is_deleted=False.
    """

    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name="pages",
        help_text="The site this page belongs to",
    )

    # Identity
    title = models.CharField(max_length=255, help_text="Page title")
    slug = models.SlugField(max_length=100, help_text="URL-safe identifier")
    description = models.TextField(blank=True, default="", help_text="Internal description")
    path = models.CharField(max_length=500, help_text="URL path relative to site (e.g., /about)")
    page_type = models.CharField(
        max_length=50,
        help_text="Categorization (landing, content, legal, blog_post)",
    )

    # SEO & metadata
    metadata = models.JSONField(
        null=True,
        blank=True,
        help_text="SEO title, description, OG tags, structured data",
    )

    # Status & publishing
    status = models.CharField(
        max_length=20,
        choices=PageStatus.choices,
        default=PageStatus.DRAFT,
        db_index=True,
    )
    published_at = models.DateTimeField(
        null=True, blank=True, help_text="When the page was last published"
    )

    # Ordering & visibility
    order = models.PositiveIntegerField(help_text="Ordering within the site's page list")
    is_required = models.BooleanField(
        default=False,
        help_text="If true, admins cannot delete or hide this page",
    )
    is_visible = models.BooleanField(
        default=True,
        help_text="Admin can toggle false ONLY if is_required=False",
    )

    # Managers
    objects = PageManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "cms_page"
        verbose_name = "CMS Page"
        verbose_name_plural = "CMS Pages"
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["site", "slug"],
                condition=models.Q(is_deleted=False),
                name="unique_cms_page_slug_per_site",
            ),
            models.UniqueConstraint(
                fields=["site", "path"],
                condition=models.Q(is_deleted=False),
                name="unique_cms_page_path_per_site",
            ),
            models.UniqueConstraint(
                fields=["site", "order"],
                condition=models.Q(is_deleted=False),
                name="unique_cms_page_order_per_site",
            ),
        ]
        indexes = [
            models.Index(fields=["site", "status"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.site.name})"

    @property
    def is_published(self) -> bool:
        return self.status == PageStatus.PUBLISHED


class SectionTemplate(UUIDModel, AuditModel):
    """
    Reusable layout definition — structural blueprint for a page region.
    Platform-wide, holds no content. Content lives in block placements.

    Globally unique slug.
    """

    # Identity
    name = models.CharField(max_length=255, help_text="Internal name (e.g., hero_banner)")
    display_name = models.CharField(max_length=255, help_text="Human-readable name for admin UI")
    slug = models.SlugField(max_length=100, help_text="Globally unique identifier (among non-deleted)")
    description = models.TextField(blank=True, default="", help_text="Section purpose")

    # Type & config
    section_type = models.CharField(
        max_length=50,
        help_text="Categorization (header, content, footer, sidebar)",
    )
    metadata = models.JSONField(null=True, blank=True, help_text="Tags, categorization")
    ui_config = models.JSONField(
        null=True,
        blank=True,
        help_text="UI rendering hints — component name, layout mode, CSS classes",
    )

    # Managers
    objects = SectionTemplateManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "cms_section_template"
        verbose_name = "Section Template"
        verbose_name_plural = "Section Templates"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["slug"],
                condition=models.Q(is_deleted=False),
                name="unique_section_template_slug_active",
            ),
        ]

    def __str__(self):
        return self.display_name


class BlockTemplate(UUIDModel, AuditModel):
    """
    Reusable schema definition for a content block. Defines field types,
    validation rules, and constraints via the schema JSONB.

    INVARIANT: Schema is immutable by admins. Only superusers modify via Django Admin.
    INVARIANT: schema_version auto-increments on every schema change.
    """

    # Identity
    name = models.CharField(max_length=255, help_text="Internal name (e.g., hero_text)")
    display_name = models.CharField(max_length=255, help_text="Human-readable name for admin UI")
    slug = models.SlugField(max_length=100, help_text="Globally unique identifier (among non-deleted)")
    description = models.TextField(blank=True, default="", help_text="Block purpose")

    # Type & schema
    block_type = models.CharField(
        max_length=50,
        help_text="Categorization (text, media, composite, repeater)",
    )
    schema = models.JSONField(help_text="Field definitions — types, validation, required flags")
    schema_version = models.PositiveIntegerField(
        default=1,
        help_text="Auto-incremented on every schema change",
    )
    default_content = models.JSONField(
        null=True,
        blank=True,
        help_text="Default values to pre-populate new placements",
    )

    # Config
    metadata = models.JSONField(null=True, blank=True, help_text="Tags, categorization")
    ui_config = models.JSONField(
        null=True,
        blank=True,
        help_text="Rendering hints — component name, CSS classes, layout rules",
    )

    # Managers
    objects = BlockTemplateManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "cms_block_template"
        verbose_name = "Block Template"
        verbose_name_plural = "Block Templates"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["slug"],
                condition=models.Q(is_deleted=False),
                name="unique_block_template_slug_active",
            ),
        ]

    def __str__(self):
        return f"{self.display_name} (v{self.schema_version})"


class PageSectionPlacement(UUIDModel, TimeStampedModel):
    """
    Attaches a SectionTemplate to a Page. One-to-many from Page.
    Carries ordering, visibility, and per-placement config.

    No user stamps (system-created). Cascade-deletes with page.
    No soft delete — hard-deletes when page structure changes.

    INVARIANT: Unique(page, order).
    INVARIANT: If is_required=True, cannot set is_visible=False.
    """

    page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        related_name="section_placements",
        help_text="The page this section is placed on",
    )
    template = models.ForeignKey(
        SectionTemplate,
        on_delete=models.PROTECT,
        related_name="placements",
        help_text="The section template being placed",
    )

    # Display
    label = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Optional admin-friendly label",
    )
    order = models.PositiveIntegerField(help_text="Position within the page")

    # Visibility & config
    is_required = models.BooleanField(
        default=False,
        help_text="If true, admin cannot hide this section",
    )
    is_visible = models.BooleanField(default=True)
    config_overrides = models.JSONField(
        null=True,
        blank=True,
        help_text="Per-placement overrides (background, spacing, etc.)",
    )

    class Meta:
        db_table = "cms_page_section_placement"
        verbose_name = "Page Section Placement"
        verbose_name_plural = "Page Section Placements"
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["page", "order"],
                name="unique_cms_section_order_per_page",
            ),
        ]

    def __str__(self):
        return self.label or f"{self.template.display_name} on {self.page.title}"


class SectionBlockPlacement(UUIDModel, UserStampedModel):
    """
    Core content-bearing entity. Attaches a BlockTemplate to a
    PageSectionPlacement and carries draft_content + published_content.

    INVARIANT: Content isolation guaranteed — each placement belongs to
               exactly one section placement on exactly one page.
    INVARIANT: Unique(section_placement, order).
    INVARIANT: If is_required=True, cannot set is_visible=False.
    """

    section_placement = models.ForeignKey(
        PageSectionPlacement,
        on_delete=models.CASCADE,
        related_name="block_placements",
        help_text="The section placement this block belongs to",
    )
    template = models.ForeignKey(
        BlockTemplate,
        on_delete=models.PROTECT,
        related_name="placements",
        help_text="The block template defining the schema",
    )

    # Display
    label = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Optional admin-friendly label",
    )
    order = models.PositiveIntegerField(help_text="Position within the section")

    # Visibility & config
    is_required = models.BooleanField(
        default=False,
        help_text="If true, admin cannot hide this block",
    )
    is_visible = models.BooleanField(default=True)
    config_overrides = models.JSONField(
        null=True,
        blank=True,
        help_text="Per-placement overrides",
    )

    # Schema tracking
    schema_version_validated = models.PositiveIntegerField(
        default=0,
        help_text="BlockTemplate.schema_version this was last validated against",
    )

    # Content — the dual-content model
    draft_content = models.JSONField(
        null=True,
        blank=True,
        help_text="Working copy — admin edits this. Pre-populated from default_content",
    )
    published_content = models.JSONField(
        null=True,
        blank=True,
        help_text="Frozen live copy — set only on page publish. Public API serves this",
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=BlockPlacementStatus.choices,
        default=BlockPlacementStatus.DRAFT,
        db_index=True,
    )

    class Meta:
        db_table = "cms_section_block_placement"
        verbose_name = "Section Block Placement"
        verbose_name_plural = "Section Block Placements"
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["section_placement", "order"],
                name="unique_cms_block_order_per_section",
            ),
        ]
        indexes = [
            models.Index(fields=["template"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return self.label or f"{self.template.display_name} #{self.order}"


class ContentVersion(UUIDModel):
    """
    Content history for rollback capability. Snapshot of draft_content
    at each save or publish point.

    Has its own created_at and created_by (not from base models).

    Retention: max 50 versions per block placement (oldest pruned).
    Throttling: max 1 version per 30 seconds per placement (update-in-place within window).
    """

    block_placement = models.ForeignKey(
        SectionBlockPlacement,
        on_delete=models.CASCADE,
        related_name="versions",
        help_text="The block placement this version belongs to",
    )
    content_snapshot = models.JSONField(
        help_text="Full copy of draft_content at this point",
    )
    version_number = models.PositiveIntegerField(
        help_text="Auto-incrementing per block placement",
    )
    action = models.CharField(
        max_length=20,
        choices=ContentVersionAction.choices,
        help_text="What triggered this version",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cms_content_versions",
        help_text="Who made this change",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, default="", help_text="Optional change description")

    class Meta:
        db_table = "cms_content_version"
        verbose_name = "Content Version"
        verbose_name_plural = "Content Versions"
        ordering = ["-version_number"]
        indexes = [
            models.Index(fields=["block_placement", "-version_number"]),
        ]

    def __str__(self):
        return f"v{self.version_number} ({self.action})"


class MediaFolder(UUIDModel, AuditModel):
    """
    Folder-based organization for media files.
    Uses owner_type/owner_id pattern (same as Site, FormTemplate).

    Max nesting depth: 5 levels (enforced at API level).
    """

    # Ownership
    owner_type = models.CharField(
        max_length=20,
        choices=OwnerType.choices,
        db_index=True,
        help_text="Which account type owns this folder",
    )
    owner_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID of owning account record",
    )

    # Identity
    name = models.CharField(max_length=255, help_text="Folder display name")
    slug = models.SlugField(max_length=100, help_text="URL-safe identifier")
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
        help_text="Parent folder for nesting. CASCADE applies to hard deletes. "
                  "For soft deletes, CMSMediaService.delete_folder must recursively "
                  "soft-delete children as defense-in-depth.",
    )
    path = models.CharField(
        max_length=1000,
        help_text="Full materialized path (e.g., /images/heroes/2026/)",
    )

    # Managers
    objects = MediaFolderManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "cms_media_folder"
        verbose_name = "Media Folder"
        verbose_name_plural = "Media Folders"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner_type", "owner_id", "parent", "slug"],
                name="unique_cms_folder_slug_per_parent",
            ),
        ]

    def __str__(self):
        return self.path or self.name


class MediaFile(UUIDModel, AuditModel):
    """
    Centralized media asset. Files are referenced by UUID in content JSONB.
    URLs are generated at read time from storage_key — never stored.

    Soft delete (from AuditModel) = record deleted.
    Tombstone = file marked for eventual removal but still accessible
                because published content references it.
    """

    # Ownership
    owner_type = models.CharField(
        max_length=20,
        choices=OwnerType.choices,
        db_index=True,
    )
    owner_id = models.UUIDField(null=True, blank=True, db_index=True)

    # Location
    folder = models.ForeignKey(
        MediaFolder,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="files",
        help_text="Containing folder (null = root)",
    )

    # File info
    storage_key = models.CharField(
        max_length=500,
        help_text="Storage path/key (e.g., platform/images/hero-banner.png)",
    )
    original_filename = models.CharField(max_length=255, help_text="Original upload filename")
    mime_type = models.CharField(max_length=100, help_text="MIME type")
    file_size = models.PositiveIntegerField(help_text="Size in bytes")

    # Dimensions (for images/video)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)

    # Metadata
    alt_text = models.CharField(max_length=255, blank=True, default="")
    title = models.CharField(max_length=255, blank=True, default="")
    metadata = models.JSONField(
        null=True, blank=True, help_text="EXIF data, custom tags, processing info"
    )

    # Tombstone state (separate from soft delete)
    is_tombstoned = models.BooleanField(
        default=False,
        help_text="Marked for removal but still accessible (published refs exist)",
    )

    # Managers
    objects = MediaFileManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "cms_media_file"
        verbose_name = "Media File"
        verbose_name_plural = "Media Files"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner_type", "owner_id", "folder"]),
            models.Index(fields=["mime_type"]),
            models.Index(fields=["is_tombstoned"]),
        ]

    def __str__(self):
        return self.original_filename


class MediaUsage(UUIDModel, TimeStampedModel):
    """
    Tracks where every media file is referenced. Enables safe deletion
    warnings and cascade cleanup.

    System-managed — created/updated automatically when block content is saved.
    Tracks both draft and published layer references separately.
    """

    media_file = models.ForeignKey(
        MediaFile,
        on_delete=models.CASCADE,
        related_name="usages",
        help_text="The referenced file",
    )
    block_placement = models.ForeignKey(
        SectionBlockPlacement,
        on_delete=models.CASCADE,
        related_name="media_usages",
        help_text="The block placement containing the reference",
    )
    field_key = models.CharField(
        max_length=100,
        help_text="Which field in the block's content references this file",
    )
    content_layer = models.CharField(
        max_length=20,
        choices=ContentLayer.choices,
        help_text="Which content JSONB holds this reference (draft or published)",
    )

    class Meta:
        db_table = "cms_media_usage"
        verbose_name = "Media Usage"
        verbose_name_plural = "Media Usages"
        indexes = [
            models.Index(fields=["media_file"]),
            models.Index(fields=["block_placement"]),
            models.Index(fields=["content_layer"]),
        ]

    def __str__(self):
        return f"{self.media_file} -> {self.block_placement} [{self.content_layer}]"


class CMSApiKey(UUIDModel, AuditModel):
    """
    API key for public CMS API access. Key is hashed at rest.
    Plaintext key returned ONCE at creation, never stored.

    Format: cmsk_{random_32_hex_chars}
    """

    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name="api_keys",
        help_text="The site this key grants access to",
    )

    # Key identity
    name = models.CharField(max_length=255, help_text="Descriptive label (e.g., Production Website)")
    key_prefix = models.CharField(
        max_length=16,
        help_text="First 8 chars of the key (for display/identification)",
    )
    key_hash = models.CharField(
        max_length=64,
        unique=True,
        help_text="SHA-256 hash of the key. Never store plaintext",
    )

    # Access control
    allowed_origins = models.JSONField(
        default=list,
        blank=True,
        help_text="Allowed Origin/Referer values. Empty = no origin restriction",
    )
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(
        null=True, blank=True, help_text="Optional expiration. Null = never expires"
    )
    last_used_at = models.DateTimeField(
        null=True, blank=True, help_text="Auto-updated on each use"
    )
    rate_limit = models.PositiveIntegerField(
        default=60,
        help_text="Max requests per minute",
    )

    # Managers
    objects = CMSApiKeyManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "cms_api_key"
        verbose_name = "CMS API Key"
        verbose_name_plural = "CMS API Keys"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["site"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.key_prefix}...)"

    @staticmethod
    def generate_key() -> tuple[str, str, str]:
        """
        Generate a new API key.

        Returns:
            (plaintext_key, key_prefix, key_hash)
        """
        random_hex = secrets.token_hex(32)
        plaintext = f"{API_KEY_PREFIX}{random_hex}"
        prefix = plaintext[:12]  # "cmsk_" + 7 hex chars
        key_hash = hashlib.sha256(plaintext.encode()).hexdigest()
        return plaintext, prefix, key_hash

    @staticmethod
    def hash_key(plaintext: str) -> str:
        """Hash a plaintext API key for lookup."""
        return hashlib.sha256(plaintext.encode()).hexdigest()
