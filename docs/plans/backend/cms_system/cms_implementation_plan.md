---

# CMS System Implementation Plan

## Multi-Tenant Platform — System 5

**Version:** 1.0
**Date:** February 26, 2026
**Status:** Ready for Implementation

> **V-notes**:
> - v1.0: Initial plan based on CMS_Project_Description_v3.1.md and coherence with Organization (v1.2), RBAC (v2.1), Transaction (v1.1), and Form Builder (v1.0) systems.

---

## Critical Invariants

> **These rules are non-negotiable and enforced at the database and service level.**

### 1. Placements ARE Instances — Content Isolation by Construction
The placement join tables (`PageSectionPlacement`, `SectionBlockPlacement`) carry the content. There are no separate "instance" models. Each placement belongs to exactly one parent (page or section placement). Content isolation is a structural guarantee — not a convention enforced by business logic.

### 2. Draft/Publish Separation is Absolute
`draft_content` and `published_content` are separate JSONB fields on `SectionBlockPlacement`. Admins edit `draft_content`; publish copies `draft_content` → `published_content` atomically. The public API ONLY serves `published_content`. These two fields are never conflated.

### 3. Schema Immutability for Admins
Block template schemas (`BlockTemplate.schema`) define the form structure. Admins cannot view, modify, create, or delete field schemas. Only superusers can modify schemas via Django Admin. Admins can only fill in content values within existing fields.

### 4. Publish is Atomic and Concurrency-Safe
Publishing a page validates ALL block placements, copies ALL `draft_content` → `published_content`, and creates ContentVersions — all within a single `@transaction.atomic` block with `select_for_update()` row-level locking.

### 5. Schema Validation: Permissive Draft, Strict Publish
Draft saves accept incomplete content with warnings. Publish rejects invalid content with structured error responses listing every failing field.

### 6. Rich Text is Always Sanitized
`richtext` field values are sanitized on every save (draft and publish). Unsanitized HTML is never stored in the database.

### 7. Media Files are Referenced by UUID, URLs Generated at Read Time
Content JSONB stores `media_id` references. The API generates signed URLs from `storage_key` at read time. URLs are never stored in the database.

### 8. Unique Order Constraints Require Atomic Reorder
`Unique(page, order)`, `Unique(page, order)`, `Unique(section_placement, order)` constraints mean reordering must use atomic bulk reassignment within `@transaction.atomic`.

---

## 1. Overview & Dependencies

### 1.1 System Purpose

The CMS System provides:
- Template-based headless content management with structural/content separation
- Hierarchical page structure: Site → Page → SectionPlacement → BlockPlacement
- JSONB-driven field flexibility via block template schemas
- Draft/publish workflow with content versioning and rollback
- Centralized media library with folder organization and usage tracking
- Public API with API key authentication and origin restriction
- Full integration with RBAC, audit/observability, and organization systems

### 1.2 Dependencies

| Dependency | System | Purpose |
|------------|--------|---------|
| `UUIDModel`, `AuditModel`, `TimeStampedModel`, `UserStampedModel` | Core | Base models |
| `ActorContext` | Core Types | Context capture and permission checks |
| `RBACService.build_actor_context()` | RBAC | Build ActorContext from membership |
| `MembershipPolicy.authorize_action()` | RBAC | Permission enforcement |
| `MembershipSelector.get_active_membership_for_user_account()` | RBAC | Resolve membership for RBAC context |
| `PlatformContextMixin` | RBAC Views | Build ActorContext in platform-scoped views |
| `AuditService`, `AuditLog` | Core Observability | Audit logging |
| `get_logger()` | Core Observability | Structured logging |
| `metrics` | Core Observability | Metrics (NoOp by default) |
| Exceptions | Core Exceptions | `NotFound`, `ValidationError`, `PermissionDenied`, `ConflictError`, `BusinessRuleViolation` |
| `OwnerType` | Core Constants | Ownership type enum (PLATFORM, BUSINESS, SYSTEM) |
| `StandardPagination` | Core Pagination | List endpoint pagination |
| `IsAuthenticated`, `IsSuperuser` | Core Permissions | DRF permission classes |

### 1.3 Files to Create

```
backend/apps/cms/
    __init__.py
    apps.py
    models.py                    # Site, Page, SectionTemplate, BlockTemplate,
                                 # PageSectionPlacement, SectionBlockPlacement,
                                 # ContentVersion, MediaFolder, MediaFile,
                                 # MediaUsage, CMSApiKey
    managers.py                  # Custom managers and querysets
    selectors.py                 # CMSSiteSelector, CMSPageSelector,
                                 # CMSTemplateSelector, CMSBlockPlacementSelector,
                                 # CMSMediaSelector, CMSContentVersionSelector,
                                 # CMSApiKeySelector
    services.py                  # CMSTemplateService, CMSPageService,
                                 # CMSContentService, CMSMediaService,
                                 # CMSApiKeyService
    policies.py                  # CMSPolicy (permission checks)
    validators.py                # SchemaValidator (draft permissive / publish strict)
    admin.py                     # Django Admin configuration
    middleware.py                # CMS API key authentication middleware
    # NOTE: No signals.py — CMS has no signal-driven side effects.
    # All state changes go through services.

    api/
        __init__.py
        serializers.py           # Input/Output serializers
        views.py                 # Admin + Public API views
        urls.py                  # Admin URL routing
        urls_public.py           # Public URL routing (API key auth)

    tests/
        __init__.py
        conftest.py              # Fixtures: site, page, templates, placements, RBAC
        factories.py             # All CMS factories
        test_models.py           # Model constraints, __str__, properties
        test_selectors.py        # Selector queries, depth control, filtering
        test_services.py         # Service methods, publish flow, rollback, media
        test_policies.py         # Permission checks per action
        test_validators.py       # SchemaValidator (draft permissive, publish strict)
        test_views.py            # API endpoints, request/response contracts
        test_admin.py            # Django Admin configuration (optional)
```

---

## 2. Enums & Constants

### 2.1 New Enums (Add to `apps/cms/constants.py`)

```python
# backend/apps/cms/constants.py
"""
CMS-specific constants and enums.

Note: CMS field types are SEPARATE from Form Builder's FieldType enum
because the two systems have different field needs.
"""

from django.db import models


class PageStatus(models.TextChoices):
    """Page lifecycle states."""
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    ARCHIVED = "archived", "Archived"


class BlockPlacementStatus(models.TextChoices):
    """Block placement content status."""
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"


class ContentVersionAction(models.TextChoices):
    """Content version action types."""
    DRAFT_SAVE = "draft_save", "Draft Save"
    PUBLISH = "publish", "Publish"
    ROLLBACK = "rollback", "Rollback"
    IMPORT = "import", "Import"


class ContentLayer(models.TextChoices):
    """Content layer for media usage tracking."""
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"


# CMS field types — separate from Form Builder's FieldType
CMS_FIELD_TYPES = frozenset([
    "text",
    "textarea",
    "richtext",
    "number",
    "boolean",
    "url",
    "email",
    "date",
    "datetime",
    "select",
    "multiselect",
    "media",
    "list",
    "repeater",
    "relation",
    "json",
    "color",
    "icon",
])

# Version throttling
VERSION_THROTTLE_SECONDS = 30

# Version retention
MAX_VERSIONS_PER_PLACEMENT = 50

# Media folder max nesting depth
MAX_FOLDER_DEPTH = 5

# API key prefix
API_KEY_PREFIX = "cmsk_"

# Default rate limit (requests per minute)
DEFAULT_RATE_LIMIT = 60
```

### 2.2 New AuditLog Actions

Add to `apps/core/observability/audit/models.py` — `AuditLog.Action` enum:

```python
# CMS - Sites
CMS_SITE_CREATED = "cms.site.created", "CMS Site Created"
CMS_SITE_UPDATED = "cms.site.updated", "CMS Site Updated"
CMS_SITE_DELETED = "cms.site.deleted", "CMS Site Deleted"

# CMS - Pages
CMS_PAGE_CREATED = "cms.page.created", "CMS Page Created"
CMS_PAGE_UPDATED = "cms.page.updated", "CMS Page Updated"
CMS_PAGE_DELETED = "cms.page.deleted", "CMS Page Deleted"
CMS_PAGE_PUBLISHED = "cms.page.published", "CMS Page Published"
CMS_PAGE_UNPUBLISHED = "cms.page.unpublished", "CMS Page Unpublished"
CMS_PAGE_ARCHIVED = "cms.page.archived", "CMS Page Archived"

# CMS - Templates
CMS_SECTION_TEMPLATE_CREATED = "cms.section_template.created", "Section Template Created"
CMS_SECTION_TEMPLATE_UPDATED = "cms.section_template.updated", "Section Template Updated"
CMS_SECTION_TEMPLATE_DELETED = "cms.section_template.deleted", "Section Template Deleted"
CMS_BLOCK_TEMPLATE_CREATED = "cms.block_template.created", "Block Template Created"
CMS_BLOCK_TEMPLATE_UPDATED = "cms.block_template.updated", "Block Template Updated"
CMS_BLOCK_TEMPLATE_DELETED = "cms.block_template.deleted", "Block Template Deleted"
CMS_BLOCK_SCHEMA_CHANGED = "cms.block_template.schema_changed", "Block Schema Changed"

# CMS - Content
CMS_CONTENT_DRAFT_SAVED = "cms.content.draft_saved", "CMS Content Draft Saved"
CMS_CONTENT_ROLLBACK = "cms.content.rollback", "CMS Content Rolled Back"
CMS_VISIBILITY_TOGGLED = "cms.placement.visibility_toggled", "CMS Visibility Toggled"

# CMS - Media
CMS_MEDIA_UPLOADED = "cms.media.uploaded", "CMS Media Uploaded"
CMS_MEDIA_DELETED = "cms.media.deleted", "CMS Media Deleted"
CMS_MEDIA_TOMBSTONED = "cms.media.tombstoned", "CMS Media Tombstoned"

# CMS - Import/Export
CMS_PAGE_EXPORTED = "cms.page.exported", "CMS Page Exported"
CMS_PAGE_IMPORTED = "cms.page.imported", "CMS Page Imported"

# CMS - API Keys
CMS_API_KEY_CREATED = "cms.api_key.created", "CMS API Key Created"
CMS_API_KEY_REVOKED = "cms.api_key.revoked", "CMS API Key Revoked"
CMS_API_KEY_UPDATED = "cms.api_key.updated", "CMS API Key Updated"
```

### 2.3 New RBAC Permissions

Add to `apps/rbac/permissions/registry.py` — 23 permissions total:

```python
# CMS - Structural (12 permissions, platform_only scope)
("can_create_cms_site", "Create CMS Site", "Create new Sites", "cms_structure", ["platform_only"]),
("can_edit_cms_site", "Edit CMS Site", "Edit existing Sites", "cms_structure", ["platform_only"]),
("can_delete_cms_site", "Delete CMS Site", "Delete Sites", "cms_structure", ["platform_only"]),
("can_create_cms_page", "Create CMS Page", "Create new Pages and attach structural placements", "cms_structure", ["platform_only"]),
("can_edit_cms_page", "Edit CMS Page", "Edit page metadata and structural placements", "cms_structure", ["platform_only"]),
("can_delete_cms_page", "Delete CMS Page", "Delete Pages", "cms_structure", ["platform_only"]),
("can_create_cms_template", "Create CMS Template", "Create SectionTemplates and BlockTemplates", "cms_structure", ["platform_only"]),
("can_edit_cms_template", "Edit CMS Template", "Edit templates and block schemas", "cms_structure", ["platform_only"]),
("can_delete_cms_template", "Delete CMS Template", "Delete templates", "cms_structure", ["platform_only"]),
("can_assign_cms_to_business", "Assign CMS to Business", "Assign sites/pages to business accounts", "cms_structure", ["platform_only", "global_only"]),
("can_create_cms_api_key", "Create CMS API Key", "Create API keys for public CMS access", "cms_structure", ["platform_only"]),
("can_revoke_cms_api_key", "Revoke CMS API Key", "Revoke API keys", "cms_structure", ["platform_only"]),

# CMS - Content (8 permissions)
("can_view_cms_content", "View CMS Content", "View pages, placements, and content", "cms_content", ["platform_only", "business", "global_only"]),
("can_edit_cms_content", "Edit CMS Content", "Edit draft_content values", "cms_content", ["platform_only", "business", "global_only"]),
("can_publish_cms_content", "Publish CMS Content", "Publish pages", "cms_content", ["platform_only", "business", "global_only"]),
("can_toggle_cms_visibility", "Toggle CMS Visibility", "Hide/show non-required placements", "cms_content", ["platform_only", "business"]),
("can_view_cms_history", "View CMS History", "View content version history", "cms_content", ["platform_only", "business"]),
("can_rollback_cms_content", "Rollback CMS Content", "Rollback draft_content to previous version", "cms_content", ["platform_only", "business"]),
("can_export_cms_content", "Export CMS Content", "Export page data as JSON", "cms_content", ["platform_only", "business"]),
("can_import_cms_content", "Import CMS Content", "Import page data from JSON", "cms_content", ["platform_only", "business"]),

# CMS - Media (3 permissions)
("can_upload_cms_media", "Upload CMS Media", "Upload media files", "cms_media", ["platform_only", "business", "global_only"]),
("can_edit_cms_media", "Edit CMS Media", "Edit media metadata, move, organize", "cms_media", ["platform_only", "business", "global_only"]),
("can_delete_cms_media", "Delete CMS Media", "Delete media files", "cms_media", ["platform_only", "business", "global_only"]),
```

---

## 3. Core Models

### 3.1 Site Model (`apps/cms/models.py`)

```python
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
```

### 3.2 Page Model

```python
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
```

### 3.3 SectionTemplate Model

```python
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
```

### 3.4 BlockTemplate Model

```python
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
```

### 3.5 PageSectionPlacement Model

```python
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
```

### 3.6 SectionBlockPlacement Model — The Content Container

```python
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
```

### 3.7 ContentVersion Model

```python
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
```

### 3.8 MediaFolder Model

```python
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
```

### 3.9 MediaFile Model

```python
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
```

### 3.10 MediaUsage Model

```python
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
        return f"{self.media_file} → {self.block_placement} [{self.content_layer}]"
```

### 3.11 CMSApiKey Model

```python
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
    objects = CMSApiKeyManager()  # SoftDeleteManager — filters out is_deleted=True by default
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
```

---

## 4. Managers & QuerySets

### 4.1 Managers (`apps/cms/managers.py`)

```python
"""
CMS Managers & QuerySets
=========================
Custom managers for CMS models. Follows the same pattern as Form Builder:
- QuerySet for chainable helpers
- Manager extends SoftDeleteManager (for models with soft delete) or models.Manager
"""

from django.db import models
from apps.core.models import SoftDeleteManager
from apps.cms.constants import PageStatus, BlockPlacementStatus


# ---------------------------------------------------------------------------
# Site
# ---------------------------------------------------------------------------

class SiteQuerySet(models.QuerySet):
    """Chainable query helpers for Site."""

    def active(self):
        return self.filter(is_active=True)

    def by_owner(self, *, owner_type: str, owner_id):
        return self.filter(owner_type=owner_type, owner_id=owner_id)


class SiteManager(SoftDeleteManager):
    """Manager for Site with soft-delete support."""

    def get_queryset(self):
        return SiteQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def active(self):
        return self.get_queryset().active()


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

class PageQuerySet(models.QuerySet):
    """Chainable query helpers for Page."""

    def by_site(self, *, site_id):
        return self.filter(site_id=site_id)

    def published(self):
        return self.filter(status=PageStatus.PUBLISHED)

    def draft(self):
        return self.filter(status=PageStatus.DRAFT)

    def visible(self):
        return self.filter(is_visible=True)

    def with_section_placements(self):
        return self.prefetch_related(
            "section_placements__template",
            "section_placements__block_placements__template",
        )


class PageManager(SoftDeleteManager):
    """Manager for Page with soft-delete support."""

    def get_queryset(self):
        return PageQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def published(self):
        return self.get_queryset().published()


# ---------------------------------------------------------------------------
# SectionTemplate
# ---------------------------------------------------------------------------

class SectionTemplateQuerySet(models.QuerySet):
    """Chainable query helpers for SectionTemplate."""

    def by_type(self, *, section_type: str):
        return self.filter(section_type=section_type)


class SectionTemplateManager(SoftDeleteManager):
    """Manager for SectionTemplate with soft-delete support."""

    def get_queryset(self):
        return SectionTemplateQuerySet(self.model, using=self._db).filter(is_deleted=False)


# ---------------------------------------------------------------------------
# BlockTemplate
# ---------------------------------------------------------------------------

class BlockTemplateQuerySet(models.QuerySet):
    """Chainable query helpers for BlockTemplate."""

    def by_type(self, *, block_type: str):
        return self.filter(block_type=block_type)


class BlockTemplateManager(SoftDeleteManager):
    """Manager for BlockTemplate with soft-delete support."""

    def get_queryset(self):
        return BlockTemplateQuerySet(self.model, using=self._db).filter(is_deleted=False)


# ---------------------------------------------------------------------------
# MediaFolder
# ---------------------------------------------------------------------------

class MediaFolderQuerySet(models.QuerySet):
    """Chainable query helpers for MediaFolder."""

    def by_owner(self, *, owner_type: str, owner_id):
        return self.filter(owner_type=owner_type, owner_id=owner_id)

    def root_folders(self):
        return self.filter(parent__isnull=True)


class MediaFolderManager(SoftDeleteManager):
    """Manager for MediaFolder with soft-delete support."""

    def get_queryset(self):
        return MediaFolderQuerySet(self.model, using=self._db).filter(is_deleted=False)


# ---------------------------------------------------------------------------
# MediaFile
# ---------------------------------------------------------------------------

class MediaFileQuerySet(models.QuerySet):
    """Chainable query helpers for MediaFile."""

    def by_owner(self, *, owner_type: str, owner_id):
        return self.filter(owner_type=owner_type, owner_id=owner_id)

    def by_folder(self, *, folder_id):
        return self.filter(folder_id=folder_id)

    def by_mime_type(self, *, mime_type: str):
        return self.filter(mime_type__startswith=mime_type)

    def tombstoned(self):
        return self.filter(is_tombstoned=True)

    def not_tombstoned(self):
        return self.filter(is_tombstoned=False)


class MediaFileManager(SoftDeleteManager):
    """Manager for MediaFile with soft-delete support."""

    def get_queryset(self):
        return MediaFileQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def tombstoned(self):
        return self.get_queryset().tombstoned()


# ---------------------------------------------------------------------------
# CMSApiKey
# ---------------------------------------------------------------------------

class CMSApiKeyQuerySet(models.QuerySet):
    """Chainable query helpers for CMSApiKey."""

    def by_site(self, *, site_id):
        return self.filter(site_id=site_id)

    def active(self):
        return self.filter(is_active=True)


class CMSApiKeyManager(SoftDeleteManager):
    """Manager for CMSApiKey with soft-delete support."""

    def get_queryset(self):
        return CMSApiKeyQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def active(self):
        return self.get_queryset().active()
```

---

## 5. Selectors (Read Operations)

### 5.1 CMSSiteSelector (`apps/cms/selectors.py`)

```python
"""
CMS Selectors
==============
Read-only queries for CMS models. All methods use keyword-only arguments.
"""

from typing import Optional
from uuid import UUID
from django.db.models import QuerySet, Count, Prefetch

from apps.core.exceptions import NotFound
from apps.cms.models import (
    Site, Page, SectionTemplate, BlockTemplate,
    PageSectionPlacement, SectionBlockPlacement,
    ContentVersion, MediaFolder, MediaFile, MediaUsage, CMSApiKey,
)
from apps.cms.constants import PageStatus, ContentLayer


class CMSSiteSelector:
    """Read-only queries for Site."""

    @staticmethod
    def get_by_slug(*, owner_type: str, owner_id: UUID, slug: str) -> Site:
        site = Site.objects.filter(
            owner_type=owner_type, owner_id=owner_id, slug=slug
        ).first()
        if not site:
            raise NotFound(resource="Site", resource_id=slug)
        return site

    @staticmethod
    def get_by_id(*, site_id: UUID) -> Site:
        site = Site.objects.filter(id=site_id).first()
        if not site:
            raise NotFound(resource="Site", resource_id=site_id)
        return site

    @staticmethod
    def list_for_owner(
        *, owner_type: str, owner_id: UUID, active_only: bool = False
    ) -> QuerySet[Site]:
        qs = Site.objects.filter(owner_type=owner_type, owner_id=owner_id)
        if active_only:
            qs = qs.filter(is_active=True)
        return qs
```

### 5.2 CMSPageSelector

```python
class CMSPageSelector:
    """Read-only queries for Page with depth control."""

    @staticmethod
    def get_by_slug(*, site_id: UUID, slug: str) -> Page:
        page = Page.objects.filter(site_id=site_id, slug=slug).first()
        if not page:
            raise NotFound(resource="Page", resource_id=slug)
        return page

    @staticmethod
    def get_by_id(*, page_id: UUID) -> Page:
        page = Page.objects.filter(id=page_id).first()
        if not page:
            raise NotFound(resource="Page", resource_id=page_id)
        return page

    @staticmethod
    def get_with_full_tree(*, page_id: UUID) -> Page:
        """
        Get page with full tree: sections → blocks → templates.
        Uses prefetch_related for efficient loading (3 joins deep).
        """
        page = (
            Page.objects
            .filter(id=page_id)
            .prefetch_related(
                Prefetch(
                    "section_placements",
                    queryset=PageSectionPlacement.objects.select_related("template").order_by("order"),
                ),
                Prefetch(
                    "section_placements__block_placements",
                    queryset=SectionBlockPlacement.objects.select_related("template").order_by("order"),
                ),
            )
            .first()
        )
        if not page:
            raise NotFound(resource="Page", resource_id=page_id)
        return page

    @staticmethod
    def list_by_site(
        *,
        site_id: UUID,
        status: Optional[str] = None,
        visible_only: bool = False,
    ) -> QuerySet[Page]:
        qs = Page.objects.filter(site_id=site_id)
        if status:
            qs = qs.filter(status=status)
        if visible_only:
            qs = qs.filter(is_visible=True)
        return qs.order_by("order")

    @staticmethod
    def list_published_for_site(*, site_id: UUID) -> QuerySet[Page]:
        """List published, visible pages for public API."""
        return (
            Page.objects
            .filter(site_id=site_id, status=PageStatus.PUBLISHED, is_visible=True)
            .order_by("order")
        )
```

### 5.3 CMSTemplateSelector

```python
class CMSTemplateSelector:
    """Read-only queries for SectionTemplate and BlockTemplate."""

    @staticmethod
    def get_section_template_by_slug(*, slug: str) -> SectionTemplate:
        template = SectionTemplate.objects.filter(slug=slug).first()
        if not template:
            raise NotFound(resource="SectionTemplate", resource_id=slug)
        return template

    @staticmethod
    def get_block_template_by_slug(*, slug: str) -> BlockTemplate:
        template = BlockTemplate.objects.filter(slug=slug).first()
        if not template:
            raise NotFound(resource="BlockTemplate", resource_id=slug)
        return template

    @staticmethod
    def get_block_template_by_id(*, template_id: UUID) -> BlockTemplate:
        template = BlockTemplate.objects.filter(id=template_id).first()
        if not template:
            raise NotFound(resource="BlockTemplate", resource_id=template_id)
        return template

    @staticmethod
    def list_section_templates(
        *, section_type: Optional[str] = None
    ) -> QuerySet[SectionTemplate]:
        qs = SectionTemplate.objects.all()
        if section_type:
            qs = qs.filter(section_type=section_type)
        return qs

    @staticmethod
    def list_block_templates(
        *, block_type: Optional[str] = None
    ) -> QuerySet[BlockTemplate]:
        qs = BlockTemplate.objects.all()
        if block_type:
            qs = qs.filter(block_type=block_type)
        return qs
```

### 5.4 CMSBlockPlacementSelector

```python
class CMSBlockPlacementSelector:
    """Read-only queries for SectionBlockPlacement."""

    @staticmethod
    def get_by_id(*, block_placement_id: UUID) -> SectionBlockPlacement:
        placement = (
            SectionBlockPlacement.objects
            .select_related("template", "section_placement__page")
            .filter(id=block_placement_id)
            .first()
        )
        if not placement:
            raise NotFound(resource="SectionBlockPlacement", resource_id=block_placement_id)
        return placement

    @staticmethod
    def list_for_section(*, section_placement_id: UUID) -> QuerySet[SectionBlockPlacement]:
        return (
            SectionBlockPlacement.objects
            .filter(section_placement_id=section_placement_id)
            .select_related("template")
            .order_by("order")
        )

    @staticmethod
    def list_for_page(*, page_id: UUID) -> QuerySet[SectionBlockPlacement]:
        """Get all block placements for a page (across all sections)."""
        return (
            SectionBlockPlacement.objects
            .filter(section_placement__page_id=page_id)
            .select_related("template", "section_placement")
            .order_by("section_placement__order", "order")
        )
```

### 5.5 CMSMediaSelector

```python
class CMSMediaSelector:
    """Read-only queries for MediaFolder and MediaFile."""

    @staticmethod
    def get_file_by_id(*, file_id: UUID) -> MediaFile:
        media = MediaFile.objects.filter(id=file_id).first()
        if not media:
            raise NotFound(resource="MediaFile", resource_id=file_id)
        return media

    @staticmethod
    def list_files(
        *,
        owner_type: str,
        owner_id: UUID,
        folder_id: Optional[UUID] = None,
        mime_type: Optional[str] = None,
    ) -> QuerySet[MediaFile]:
        qs = MediaFile.objects.filter(owner_type=owner_type, owner_id=owner_id)
        if folder_id:
            qs = qs.filter(folder_id=folder_id)
        elif folder_id is None:
            pass  # All folders
        if mime_type:
            qs = qs.filter(mime_type__startswith=mime_type)
        return qs

    @staticmethod
    def get_usage(*, file_id: UUID) -> QuerySet[MediaUsage]:
        return MediaUsage.objects.filter(media_file_id=file_id).select_related(
            "block_placement__section_placement__page"
        )

    @staticmethod
    def list_folders(
        *, owner_type: str, owner_id: UUID, parent_id: Optional[UUID] = None
    ) -> QuerySet[MediaFolder]:
        qs = MediaFolder.objects.filter(owner_type=owner_type, owner_id=owner_id)
        if parent_id:
            qs = qs.filter(parent_id=parent_id)
        else:
            qs = qs.filter(parent__isnull=True)
        return qs

    @staticmethod
    def get_folder_by_slug(
        *, owner_type: str, owner_id: UUID, slug: str
    ) -> MediaFolder:
        folder = MediaFolder.objects.filter(
            owner_type=owner_type, owner_id=owner_id, slug=slug
        ).first()
        if not folder:
            raise NotFound(resource="MediaFolder", resource_id=slug)
        return folder
```

### 5.6 CMSContentVersionSelector

```python
class CMSContentVersionSelector:
    """Read-only queries for ContentVersion."""

    @staticmethod
    def list_for_placement(*, block_placement_id: UUID) -> QuerySet[ContentVersion]:
        return (
            ContentVersion.objects
            .filter(block_placement_id=block_placement_id)
            .select_related("created_by")
            .order_by("-version_number")
        )

    @staticmethod
    def get_version(
        *, block_placement_id: UUID, version_number: int
    ) -> ContentVersion:
        version = ContentVersion.objects.filter(
            block_placement_id=block_placement_id,
            version_number=version_number,
        ).first()
        if not version:
            raise NotFound(
                resource="ContentVersion",
                resource_id=f"{block_placement_id}:v{version_number}",
            )
        return version

    @staticmethod
    def get_latest_version(*, block_placement_id: UUID) -> Optional[ContentVersion]:
        return (
            ContentVersion.objects
            .filter(block_placement_id=block_placement_id)
            .order_by("-version_number")
            .first()
        )
```

### 5.7 CMSApiKeySelector

```python
class CMSApiKeySelector:
    """Read-only queries for CMSApiKey."""

    @staticmethod
    def get_by_hash(*, key_hash: str) -> CMSApiKey:
        api_key = CMSApiKey.objects.filter(key_hash=key_hash, is_deleted=False).first()
        if not api_key:
            raise NotFound(resource="CMSApiKey", resource_id="(hashed)")
        return api_key

    @staticmethod
    def list_for_site(*, site_id: UUID) -> QuerySet[CMSApiKey]:
        return CMSApiKey.objects.filter(site_id=site_id, is_deleted=False)
```

---

## 6. Services (Write Operations)

### 6.0 Actor Resolution Helper

```python
# Module-level helper — same pattern as apps/rbac/services.py:44
# and apps/transaction/services.py:26

from apps.users.models import User
from apps.core.types import ActorContext


def _resolve_actor(actor_context: ActorContext):
    """Resolve User from ActorContext.user_id for audit logging."""
    try:
        return User.objects.get(id=actor_context.user_id)
    except User.DoesNotExist:
        return None
```

### 6.1 CMSSiteService (`apps/cms/services.py`)

```python
"""
CMS Services
==============
All write operations for the CMS app.
Pattern: @staticmethod, @transaction.atomic, keyword-only arguments.
"""

from typing import Optional
from uuid import UUID
from django.db import transaction
from django.http import HttpRequest

from apps.core.exceptions import (
    NotFound, ValidationError, PermissionDenied,
    ConflictError, BusinessRuleViolation,
)
from apps.core.types import ActorContext
from apps.core.observability import AuditService, AuditLog, get_logger
from apps.rbac.policies import MembershipPolicy
from apps.cms.models import (
    Site, Page, SectionTemplate, BlockTemplate,
    PageSectionPlacement, SectionBlockPlacement,
    ContentVersion, MediaFolder, MediaFile, MediaUsage, CMSApiKey,
)
from apps.cms.selectors import (
    CMSSiteSelector, CMSPageSelector, CMSTemplateSelector,
    CMSBlockPlacementSelector, CMSMediaSelector,
    CMSContentVersionSelector, CMSApiKeySelector,
)
from apps.cms.constants import (
    PageStatus, BlockPlacementStatus, ContentVersionAction,
    ContentLayer, VERSION_THROTTLE_SECONDS, MAX_VERSIONS_PER_PLACEMENT,
)

logger = get_logger(__name__)


class CMSSiteService:
    """Site lifecycle — create, update, soft-delete (platform-only, superuser)."""

    @staticmethod
    @transaction.atomic
    def create_site(
        *,
        actor_context: ActorContext,
        name: str,
        slug: str,
        domain: str = "",
        description: str = "",
        owner_type: str,
        owner_id=None,
        metadata: Optional[dict] = None,
        request: Optional[HttpRequest] = None,
    ) -> "Site":
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_create_cms_site",
        )

        # Check slug uniqueness
        if Site.objects.filter(slug=slug).exists():
            raise ConflictError(resource="Site", conflict_type="duplicate")

        actor = _resolve_actor(actor_context)
        site = Site.objects.create(
            name=name,
            slug=slug,
            domain=domain,
            description=description,
            owner_type=owner_type,
            owner_id=owner_id,
            metadata=metadata,
            created_by=actor,
            updated_by=actor,
        )

        logger.info("cms.site.created", site_id=str(site.id), slug=slug)
        AuditService.log(
            action=AuditLog.Action.CMS_SITE_CREATED,
            actor=actor,
            resource=site,
            request=request,
        )
        return site

    @staticmethod
    @transaction.atomic
    def update_site(
        *,
        actor_context: ActorContext,
        slug: str,
        request: Optional[HttpRequest] = None,
        **fields,
    ) -> "Site":
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_edit_cms_site",
        )

        site = CMSSiteSelector.get_by_slug(
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            slug=slug,
        )

        actor = _resolve_actor(actor_context)
        allowed_fields = {"name", "domain", "description", "metadata", "is_active"}
        for field, value in fields.items():
            if field in allowed_fields:
                setattr(site, field, value)
        site.updated_by = actor
        site.save()

        logger.info("cms.site.updated", site_id=str(site.id))
        AuditService.log(
            action=AuditLog.Action.CMS_SITE_UPDATED,
            actor=actor,
            resource=site,
            request=request,
        )
        return site

    @staticmethod
    @transaction.atomic
    def delete_site(
        *,
        actor_context: ActorContext,
        slug: str,
        request: Optional[HttpRequest] = None,
    ) -> None:
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_delete_cms_site",
        )

        site = CMSSiteSelector.get_by_slug(
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            slug=slug,
        )

        actor = _resolve_actor(actor_context)
        site.soft_delete(deleted_by=actor)

        logger.info("cms.site.deleted", site_id=str(site.id))
        AuditService.log(
            action=AuditLog.Action.CMS_SITE_DELETED,
            actor=actor,
            resource=site,
            request=request,
        )
```

### 6.2 CMSTemplateService

```python
class CMSTemplateService:
    """Create/update/delete templates, placement ordering (superuser)."""

    @staticmethod
    @transaction.atomic
    def create_section_template(
        *,
        actor_context: ActorContext,
        name: str,
        display_name: str,
        slug: str,
        section_type: str,
        description: str = "",
        metadata: Optional[dict] = None,
        ui_config: Optional[dict] = None,
        request: Optional[HttpRequest] = None,
    ) -> SectionTemplate:
        # Authorize
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_create_cms_template",
        )

        # Check slug uniqueness
        if SectionTemplate.objects.filter(slug=slug).exists():
            raise ConflictError(resource="SectionTemplate", conflict_type="duplicate")

        actor = _resolve_actor(actor_context)
        template = SectionTemplate.objects.create(
            name=name,
            display_name=display_name,
            slug=slug,
            section_type=section_type,
            description=description,
            metadata=metadata,
            ui_config=ui_config,
            created_by=actor,
            updated_by=actor,
        )

        logger.info("cms.section_template.created", template_id=str(template.id), slug=slug)
        AuditService.log(
            action=AuditLog.Action.CMS_SECTION_TEMPLATE_CREATED,
            actor=actor,
            resource=template,
            request=request,
        )
        return template

    @staticmethod
    @transaction.atomic
    def create_block_template(
        *,
        actor_context: ActorContext,
        name: str,
        display_name: str,
        slug: str,
        block_type: str,
        schema: dict,
        description: str = "",
        default_content: Optional[dict] = None,
        metadata: Optional[dict] = None,
        ui_config: Optional[dict] = None,
        request: Optional[HttpRequest] = None,
    ) -> BlockTemplate:
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_create_cms_template",
        )

        if BlockTemplate.objects.filter(slug=slug).exists():
            raise ConflictError(resource="BlockTemplate", conflict_type="duplicate")

        # Validate schema structure
        from apps.cms.validators import SchemaValidator
        SchemaValidator.validate_schema_structure(schema=schema)

        actor = _resolve_actor(actor_context)
        template = BlockTemplate.objects.create(
            name=name,
            display_name=display_name,
            slug=slug,
            block_type=block_type,
            schema=schema,
            schema_version=1,
            default_content=default_content,
            description=description,
            metadata=metadata,
            ui_config=ui_config,
            created_by=actor,
            updated_by=actor,
        )

        logger.info("cms.block_template.created", template_id=str(template.id), slug=slug)
        AuditService.log(
            action=AuditLog.Action.CMS_BLOCK_TEMPLATE_CREATED,
            actor=actor,
            resource=template,
            request=request,
        )
        return template

    @staticmethod
    @transaction.atomic
    def update_block_schema(
        *,
        actor_context: ActorContext,
        template_id: UUID,
        schema: dict,
        request: Optional[HttpRequest] = None,
    ) -> BlockTemplate:
        """Update block template schema. Increments schema_version."""
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_edit_cms_template",
        )

        template = CMSTemplateSelector.get_block_template_by_id(template_id=template_id)
        old_schema = template.schema

        from apps.cms.validators import SchemaValidator
        SchemaValidator.validate_schema_structure(schema=schema)

        actor = _resolve_actor(actor_context)
        template.schema = schema
        template.schema_version += 1
        template.updated_by = actor
        template.save(update_fields=["schema", "schema_version", "updated_by", "updated_at"])

        logger.info(
            "cms.block_template.schema_changed",
            template_id=str(template.id),
            new_version=template.schema_version,
        )
        AuditService.log_change(
            action=AuditLog.Action.CMS_BLOCK_SCHEMA_CHANGED,
            actor=actor,
            resource=template,
            before={"schema": old_schema},
            after={"schema": schema},
            request=request,
        )
        return template

    @staticmethod
    @transaction.atomic
    def reorder_section_placements(
        *,
        actor_context: ActorContext,
        page_id: UUID,
        ordered_placement_ids: list[UUID],
        request: Optional[HttpRequest] = None,
    ) -> None:
        """Atomic bulk reassignment of section placement order within a page."""
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_edit_cms_page",
        )

        # Validate all IDs belong to this page
        existing_ids = set(
            PageSectionPlacement.objects.filter(page_id=page_id)
            .values_list("id", flat=True)
        )
        provided_ids = set(ordered_placement_ids)
        if existing_ids != provided_ids:
            raise ValidationError(
                message="Provided IDs must match exactly the placements on this page",
            )

        # Two-pass update to avoid unique constraint violations on (page, order):
        # Pass 1: Set all orders to negative (temporary, guaranteed unique)
        for index, placement_id in enumerate(ordered_placement_ids):
            PageSectionPlacement.objects.filter(id=placement_id).update(order=-(index + 1))
        # Pass 2: Set final positive order values
        for index, placement_id in enumerate(ordered_placement_ids):
            PageSectionPlacement.objects.filter(id=placement_id).update(order=index)

        logger.info("cms.section_placements.reordered", page_id=str(page_id))

    @staticmethod
    @transaction.atomic
    def reorder_block_placements(
        *,
        actor_context: ActorContext,
        section_placement_id: UUID,
        ordered_placement_ids: list[UUID],
        request: Optional[HttpRequest] = None,
    ) -> None:
        """Atomic bulk reassignment of block placement order within a section."""
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_edit_cms_page",
        )

        existing_ids = set(
            SectionBlockPlacement.objects.filter(section_placement_id=section_placement_id)
            .values_list("id", flat=True)
        )
        provided_ids = set(ordered_placement_ids)
        if existing_ids != provided_ids:
            raise ValidationError(
                message="Provided IDs must match exactly the placements in this section",
            )

        # Two-pass update to avoid unique constraint violations on (section_placement, order):
        # Pass 1: Set all orders to negative (temporary, guaranteed unique)
        for index, placement_id in enumerate(ordered_placement_ids):
            SectionBlockPlacement.objects.filter(id=placement_id).update(order=-(index + 1))
        # Pass 2: Set final positive order values
        for index, placement_id in enumerate(ordered_placement_ids):
            SectionBlockPlacement.objects.filter(id=placement_id).update(order=index)

        logger.info(
            "cms.block_placements.reordered",
            section_placement_id=str(section_placement_id),
        )
```

### 6.3 CMSPageService

```python
class CMSPageService:
    """Page lifecycle, ordering, publish/unpublish, export/import."""

    @staticmethod
    @transaction.atomic
    def create_page(
        *,
        actor_context: ActorContext,
        site_id: UUID,
        title: str,
        slug: str,
        path: str,
        page_type: str,
        order: int,
        description: str = "",
        metadata: Optional[dict] = None,
        is_required: bool = False,
        request: Optional[HttpRequest] = None,
    ) -> Page:
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_create_cms_page",
        )

        site = CMSSiteSelector.get_by_id(site_id=site_id)

        # Check slug uniqueness within site
        if Page.objects.filter(site=site, slug=slug).exists():
            raise ConflictError(resource="Page", conflict_type="duplicate")

        actor = _resolve_actor(actor_context)
        page = Page.objects.create(
            site=site,
            title=title,
            slug=slug,
            path=path,
            page_type=page_type,
            order=order,
            description=description,
            metadata=metadata,
            is_required=is_required,
            status=PageStatus.DRAFT,
            created_by=actor,
            updated_by=actor,
        )

        logger.info("cms.page.created", page_id=str(page.id), slug=slug)
        AuditService.log(
            action=AuditLog.Action.CMS_PAGE_CREATED,
            actor=actor,
            resource=page,
            request=request,
        )
        return page

    @staticmethod
    @transaction.atomic
    def reorder_pages(
        *,
        actor_context: ActorContext,
        site_id: UUID,
        ordered_page_ids: list[UUID],
        request: Optional[HttpRequest] = None,
    ) -> None:
        """Atomic bulk reassignment of page order within a site."""
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_edit_cms_page",
        )

        existing_ids = set(
            Page.objects.filter(site_id=site_id).values_list("id", flat=True)
        )
        provided_ids = set(ordered_page_ids)
        if existing_ids != provided_ids:
            raise ValidationError(
                message="Provided IDs must match exactly the pages in this site",
            )

        # Two-pass update to avoid unique constraint violations on (site, order):
        # Pass 1: Set all orders to negative (temporary, guaranteed unique)
        for index, page_id in enumerate(ordered_page_ids):
            Page.objects.filter(id=page_id).update(order=-(index + 1))
        # Pass 2: Set final positive order values
        for index, page_id in enumerate(ordered_page_ids):
            Page.objects.filter(id=page_id).update(order=index)

        logger.info("cms.pages.reordered", site_id=str(site_id))

    @staticmethod
    @transaction.atomic
    def publish_page(
        *,
        actor_context: ActorContext,
        page_id: UUID,
        request: Optional[HttpRequest] = None,
    ) -> Page:
        """
        Atomic publish: validate all blocks, copy draft→published.

        Uses select_for_update() for concurrency safety.
        """
        from apps.cms.validators import SchemaValidator
        from django.utils import timezone

        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_publish_cms_content",
        )

        # STEP 1: Acquire locks
        page = Page.objects.select_for_update().filter(id=page_id).first()
        if not page:
            raise NotFound(resource="Page", resource_id=page_id)

        section_placements = list(
            PageSectionPlacement.objects.select_for_update()
            .filter(page=page)
            .order_by("order")
        )
        block_placements = list(
            SectionBlockPlacement.objects.select_for_update()
            .filter(section_placement__page=page)
            .select_related("template")
        )

        # STEP 2: Validate ALL (before any writes)
        publish_errors = []
        for bp in block_placements:
            # Skip hidden, non-required blocks
            if not bp.is_visible and not bp.is_required:
                continue

            errors = SchemaValidator.validate_content(
                schema=bp.template.schema,
                content=bp.draft_content or {},
                strict=True,
            )
            for error in errors:
                publish_errors.append({
                    "section_placement_id": str(bp.section_placement_id),
                    "block_placement_id": str(bp.id),
                    "block_template": bp.template.slug,
                    **error,
                })

        if publish_errors:
            raise ValidationError(
                message="Publish validation failed",
                details={"publish_errors": publish_errors},
            )

        # STEP 3: Write ALL
        actor = _resolve_actor(actor_context)
        for bp in block_placements:
            bp.published_content = bp.draft_content
            bp.status = BlockPlacementStatus.PUBLISHED
            bp.schema_version_validated = bp.template.schema_version
            bp.save(update_fields=[
                "published_content", "status", "schema_version_validated", "updated_at",
            ])

            # Create content version
            _create_content_version(
                block_placement=bp,
                content=bp.draft_content,
                action=ContentVersionAction.PUBLISH,
                actor=actor,
            )

            # Update media usage for published layer
            _sync_media_usage(
                block_placement=bp,
                content=bp.published_content,
                layer=ContentLayer.PUBLISHED,
            )

        page.status = PageStatus.PUBLISHED
        page.published_at = timezone.now()
        page.updated_by = actor
        page.save(update_fields=["status", "published_at", "updated_by", "updated_at"])

        logger.info(
            "cms.page.publish.success",
            page_id=str(page.id),
            block_count=len(block_placements),
        )

        # STEP 5: Audit (inside transaction for consistency)
        AuditService.log(
            action=AuditLog.Action.CMS_PAGE_PUBLISHED,
            actor=actor,
            resource=page,
            request=request,
            details={
                "block_count": len(block_placements),
                "site_slug": page.site.slug,
            },
        )
        return page

    @staticmethod
    @transaction.atomic
    def unpublish_page(
        *,
        actor_context: ActorContext,
        page_id: UUID,
        request: Optional[HttpRequest] = None,
    ) -> Page:
        """Revert page to draft. published_content is NOT cleared."""
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_publish_cms_content",
        )

        page = CMSPageSelector.get_by_id(page_id=page_id)
        if page.status != PageStatus.PUBLISHED:
            raise BusinessRuleViolation(
                message="Only published pages can be unpublished",
                rule="unpublish_from_published",
            )

        actor = _resolve_actor(actor_context)

        # Revert block placement statuses
        SectionBlockPlacement.objects.filter(
            section_placement__page=page
        ).update(status=BlockPlacementStatus.DRAFT)

        page.status = PageStatus.DRAFT
        page.updated_by = actor
        page.save(update_fields=["status", "updated_by", "updated_at"])

        logger.info("cms.page.unpublished", page_id=str(page.id))
        AuditService.log(
            action=AuditLog.Action.CMS_PAGE_UNPUBLISHED,
            actor=actor,
            resource=page,
            request=request,
        )
        return page

    @staticmethod
    def export_page(
        *,
        actor_context: ActorContext,
        page_id: UUID,
        request: Optional[HttpRequest] = None,
    ) -> dict:
        """Export page tree as JSON (see spec Section 10.1)."""
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_export_cms_content",
        )

        page = CMSPageSelector.get_with_full_tree(page_id=page_id)
        actor = _resolve_actor(actor_context)

        # Build export structure per spec Section 10.1
        export_data = {
            "export_version": "3.1",
            "exported_at": timezone.now().isoformat(),
            "exported_by": str(actor_context.user_id),
            "source_site": page.site.slug,
            "source_owner_type": page.site.owner_type,
            "source_owner_id": str(page.site.owner_id),
            "page": _serialize_page_for_export(page),
        }

        AuditService.log(
            action=AuditLog.Action.CMS_PAGE_EXPORTED,
            actor=actor,
            resource=page,
            request=request,
        )
        return export_data

    @staticmethod
    @transaction.atomic
    def import_page(
        *,
        actor_context: ActorContext,
        page_id: UUID,
        import_data: dict,
        request: Optional[HttpRequest] = None,
    ) -> Page:
        """Content-only import: match block placements by UUID, update draft_content."""
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_import_cms_content",
        )

        page = CMSPageSelector.get_by_id(page_id=page_id)
        actor = _resolve_actor(actor_context)

        # Match and update block placements by UUID
        imported_blocks = _extract_block_placements_from_import(import_data)
        for bp_data in imported_blocks:
            bp = SectionBlockPlacement.objects.filter(
                id=bp_data["id"],
                section_placement__page=page,
            ).select_related("template").first()
            if not bp:
                continue  # Skip non-matching UUIDs

            # Validate against existing schema
            from apps.cms.validators import SchemaValidator
            errors = SchemaValidator.validate_content(
                schema=bp.template.schema,
                content=bp_data.get("draft_content", {}),
                strict=False,
            )
            # Store regardless (permissive import)
            bp.draft_content = bp_data.get("draft_content", bp.draft_content)
            bp.updated_by = actor
            bp.save(update_fields=["draft_content", "updated_by", "updated_at"])

            _create_content_version(
                block_placement=bp,
                content=bp.draft_content,
                action=ContentVersionAction.IMPORT,
                actor=actor,
            )

        logger.info("cms.page.imported", page_id=str(page.id))
        AuditService.log(
            action=AuditLog.Action.CMS_PAGE_IMPORTED,
            actor=actor,
            resource=page,
            request=request,
        )
        return page
```

### 6.4 CMSContentService

```python
class CMSContentService:
    """Draft content editing, rollback, visibility toggling."""

    @staticmethod
    @transaction.atomic
    def update_draft_content(
        *,
        actor_context: ActorContext,
        block_placement_id: UUID,
        content: dict,
        request: Optional[HttpRequest] = None,
    ) -> SectionBlockPlacement:
        """
        Update draft_content on a block placement.
        Validates permissively (warnings, not errors).
        Creates ContentVersion with throttling.
        """
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_edit_cms_content",
        )

        placement = CMSBlockPlacementSelector.get_by_id(
            block_placement_id=block_placement_id
        )

        # Sanitize richtext fields, then validate permissively (warnings only)
        from apps.cms.validators import SchemaValidator
        content = SchemaValidator.sanitize_content(
            schema=placement.template.schema,
            content=content,
        )
        warnings = SchemaValidator.validate_content(
            schema=placement.template.schema,
            content=content,
            strict=False,
        )

        old_content = placement.draft_content
        actor = _resolve_actor(actor_context)

        placement.draft_content = content  # Sanitized content
        placement.updated_by = actor
        placement.save(update_fields=["draft_content", "updated_by", "updated_at"])

        # Create version with throttling
        _create_content_version_throttled(
            block_placement=placement,
            content=content,
            action=ContentVersionAction.DRAFT_SAVE,
            actor=actor,
        )

        # Update media usage for draft layer
        _sync_media_usage(
            block_placement=placement,
            content=content,
            layer=ContentLayer.DRAFT,
        )

        logger.info(
            "cms.content.draft_saved",
            placement_id=str(placement.id),
        )
        AuditService.log_change(
            action=AuditLog.Action.CMS_CONTENT_DRAFT_SAVED,
            actor=actor,
            resource=placement,
            before={"draft_content": old_content},
            after={"draft_content": content},
            request=request,
        )

        return placement

    @staticmethod
    @transaction.atomic
    def rollback_content(
        *,
        actor_context: ActorContext,
        block_placement_id: UUID,
        version_number: int,
        request: Optional[HttpRequest] = None,
    ) -> SectionBlockPlacement:
        """
        Rollback draft_content to a previous version.
        Does NOT update published_content — admin must re-publish.
        """
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_rollback_cms_content",
        )

        placement = CMSBlockPlacementSelector.get_by_id(
            block_placement_id=block_placement_id
        )
        version = CMSContentVersionSelector.get_version(
            block_placement_id=block_placement_id,
            version_number=version_number,
        )

        actor = _resolve_actor(actor_context)
        placement.draft_content = version.content_snapshot
        placement.updated_by = actor
        placement.save(update_fields=["draft_content", "updated_by", "updated_at"])

        _create_content_version(
            block_placement=placement,
            content=version.content_snapshot,
            action=ContentVersionAction.ROLLBACK,
            actor=actor,
            notes=f"Rolled back to version {version_number}",
        )

        logger.info(
            "cms.content.rollback",
            placement_id=str(placement.id),
            to_version=version_number,
        )
        AuditService.log(
            action=AuditLog.Action.CMS_CONTENT_ROLLBACK,
            actor=actor,
            resource=placement,
            request=request,
            details={"rolled_back_to_version": version_number},
        )
        return placement

    @staticmethod
    @transaction.atomic
    def toggle_visibility(
        *,
        actor_context: ActorContext,
        block_placement_id: UUID,
        is_visible: bool,
        request: Optional[HttpRequest] = None,
    ) -> SectionBlockPlacement:
        """Toggle visibility on a non-required block placement."""
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_toggle_cms_visibility",
        )

        placement = CMSBlockPlacementSelector.get_by_id(
            block_placement_id=block_placement_id
        )

        if placement.is_required and not is_visible:
            raise BusinessRuleViolation(
                message="Cannot hide a required block placement",
                rule="required_placement_visibility",
            )

        actor = _resolve_actor(actor_context)
        placement.is_visible = is_visible
        placement.updated_by = actor
        placement.save(update_fields=["is_visible", "updated_by", "updated_at"])

        logger.info(
            "cms.visibility.toggled",
            placement_id=str(placement.id),
            is_visible=is_visible,
        )
        AuditService.log(
            action=AuditLog.Action.CMS_VISIBILITY_TOGGLED,
            actor=actor,
            resource=placement,
            request=request,
            details={"is_visible": is_visible},
        )
        return placement
```

### 6.5 CMSMediaService

```python
class CMSMediaService:
    """File upload, delete, tombstone cleanup."""

    @staticmethod
    @transaction.atomic
    def upload_file(
        *,
        actor_context: ActorContext,
        owner_type: str,
        owner_id: UUID,
        file,  # Django UploadedFile
        folder_id: Optional[UUID] = None,
        alt_text: str = "",
        title: str = "",
        request: Optional[HttpRequest] = None,
    ) -> MediaFile:
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_upload_cms_media",
        )

        from django.core.files.storage import default_storage

        actor = _resolve_actor(actor_context)

        # Generate storage key
        import uuid as uuid_mod
        ext = file.name.rsplit(".", 1)[-1] if "." in file.name else ""
        storage_key = f"{owner_type}/{str(owner_id)}/media/{uuid_mod.uuid4().hex}.{ext}"

        # Save to storage
        saved_path = default_storage.save(storage_key, file)

        media = MediaFile.objects.create(
            owner_type=owner_type,
            owner_id=owner_id,
            folder_id=folder_id,
            storage_key=saved_path,
            original_filename=file.name,
            mime_type=file.content_type or "application/octet-stream",
            file_size=file.size,
            alt_text=alt_text,
            title=title,
            created_by=actor,
            updated_by=actor,
        )

        logger.info("cms.media.uploaded", file_id=str(media.id), filename=file.name)
        AuditService.log(
            action=AuditLog.Action.CMS_MEDIA_UPLOADED,
            actor=actor,
            resource=media,
            request=request,
        )
        return media

    @staticmethod
    @transaction.atomic
    def delete_file(
        *,
        actor_context: ActorContext,
        file_id: UUID,
        request: Optional[HttpRequest] = None,
    ) -> MediaFile:
        """
        Delete a media file. If published content references it,
        tombstone instead of deleting.
        """
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_delete_cms_media",
        )

        media = CMSMediaSelector.get_file_by_id(file_id=file_id)
        actor = _resolve_actor(actor_context)

        # Check for published references
        published_usage_count = MediaUsage.objects.filter(
            media_file=media,
            content_layer=ContentLayer.PUBLISHED,
        ).count()

        if published_usage_count > 0:
            # Tombstone — keep in storage, mark for eventual cleanup
            media.is_tombstoned = True
            media.updated_by = actor
            media.save(update_fields=["is_tombstoned", "updated_by", "updated_at"])

            # Null out draft references
            _null_draft_media_references(media_file=media)

            logger.info("cms.media.tombstoned", file_id=str(media.id))
            AuditService.log(
                action=AuditLog.Action.CMS_MEDIA_TOMBSTONED,
                actor=actor,
                resource=media,
                request=request,
                details={"published_refs": published_usage_count},
            )
        else:
            # No published refs — safe to soft-delete
            media.soft_delete(deleted_by=actor)

            logger.info("cms.media.deleted", file_id=str(media.id))
            AuditService.log(
                action=AuditLog.Action.CMS_MEDIA_DELETED,
                actor=actor,
                resource=media,
                request=request,
            )

        return media

    @staticmethod
    @transaction.atomic
    def delete_folder(
        *,
        actor_context: ActorContext,
        folder_id: UUID,
        request: Optional[HttpRequest] = None,
    ) -> None:
        """
        Soft-delete a folder and recursively soft-delete all children.

        Defense-in-depth: models.CASCADE only fires on hard delete.
        Soft delete requires explicit recursion to avoid orphaned children.
        """
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_delete_cms_media",
        )

        folder = CMSMediaSelector.get_folder_by_id(folder_id=folder_id)
        actor = _resolve_actor(actor_context)

        # Recursively soft-delete all descendants (depth-first)
        def _soft_delete_recursive(parent_folder):
            for child in parent_folder.children.filter(is_deleted=False):
                _soft_delete_recursive(child)
                child.soft_delete(deleted_by=actor)

        _soft_delete_recursive(folder)
        folder.soft_delete(deleted_by=actor)

        logger.info("cms.media_folder.deleted", folder_id=str(folder.id))

    @staticmethod
    def cleanup_tombstoned() -> int:
        """
        Celery task: Remove tombstoned files with zero published references.
        Returns count of files cleaned up.

        NOTE: No @transaction.atomic — each file is cleaned independently.
        A storage error on one file must not roll back successful deletions.
        """
        from django.core.files.storage import default_storage

        tombstoned = MediaFile.objects.filter(is_tombstoned=True)
        cleaned = 0

        for media in tombstoned:
            published_count = MediaUsage.objects.filter(
                media_file=media,
                content_layer=ContentLayer.PUBLISHED,
            ).count()

            if published_count == 0:
                # Remove from storage — errors are logged, not fatal
                try:
                    default_storage.delete(media.storage_key)
                except Exception:
                    logger.warning(
                        "cms.media.cleanup.storage_error",
                        file_id=str(media.id),
                        storage_key=media.storage_key,
                    )
                    continue  # Skip hard-delete if storage removal failed
                # Hard-delete the record (only if storage removal succeeded)
                media.delete()
                cleaned += 1

        logger.info("cms.media.cleanup.complete", cleaned_count=cleaned)
        return cleaned
```

### 6.6 CMSApiKeyService

```python
class CMSApiKeyService:
    """API key lifecycle for public API access."""

    @staticmethod
    @transaction.atomic
    def create_api_key(
        *,
        actor_context: ActorContext,
        site_id: UUID,
        name: str,
        allowed_origins: Optional[list[str]] = None,
        rate_limit: int = 60,
        expires_at=None,
        request: Optional[HttpRequest] = None,
    ) -> tuple[CMSApiKey, str]:
        """
        Create a new API key. Returns (api_key_record, plaintext_key).
        Plaintext is returned ONCE and never stored.
        """
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_create_cms_api_key",
        )

        site = CMSSiteSelector.get_by_id(site_id=site_id)
        actor = _resolve_actor(actor_context)

        plaintext, prefix, key_hash = CMSApiKey.generate_key()

        api_key = CMSApiKey.objects.create(
            site=site,
            name=name,
            key_prefix=prefix,
            key_hash=key_hash,
            allowed_origins=allowed_origins or [],
            rate_limit=rate_limit,
            expires_at=expires_at,
            is_active=True,
            created_by=actor,
            updated_by=actor,
        )

        logger.info("cms.api_key.created", key_id=str(api_key.id), site_id=str(site_id))
        AuditService.log(
            action=AuditLog.Action.CMS_API_KEY_CREATED,
            actor=actor,
            resource=api_key,
            request=request,
        )
        return api_key, plaintext

    @staticmethod
    @transaction.atomic
    def revoke_api_key(
        *,
        actor_context: ActorContext,
        api_key_id: UUID,
        request: Optional[HttpRequest] = None,
    ) -> CMSApiKey:
        """Revoke (soft-delete) an API key."""
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_revoke_cms_api_key",
        )

        api_key = CMSApiKey.objects.filter(id=api_key_id, is_deleted=False).first()
        if not api_key:
            raise NotFound(resource="CMSApiKey", resource_id=api_key_id)

        actor = _resolve_actor(actor_context)
        api_key.is_active = False
        api_key.save(update_fields=["is_active", "updated_at"])
        api_key.soft_delete(deleted_by=actor)

        logger.info("cms.api_key.revoked", key_id=str(api_key.id))
        AuditService.log(
            action=AuditLog.Action.CMS_API_KEY_REVOKED,
            actor=actor,
            resource=api_key,
            request=request,
        )
        return api_key

    @staticmethod
    def validate_api_key(*, plaintext_key: str) -> CMSApiKey:
        """
        Validate an API key from request header.
        Checks: exists, active, not expired.
        """
        from django.utils import timezone

        key_hash = CMSApiKey.hash_key(plaintext_key)
        api_key = CMSApiKey.objects.filter(
            key_hash=key_hash, is_deleted=False
        ).select_related("site").first()

        if not api_key:
            raise PermissionDenied(message="Invalid API key")

        if not api_key.is_active:
            raise PermissionDenied(message="API key is inactive")

        if api_key.expires_at and api_key.expires_at < timezone.now():
            raise PermissionDenied(message="API key has expired")

        # Update last_used_at
        CMSApiKey.objects.filter(id=api_key.id).update(last_used_at=timezone.now())

        return api_key
```

### 6.7 Internal Helpers

```python
# ---------------------------------------------------------------------------
# Internal helpers (module-level, not exposed)
# ---------------------------------------------------------------------------

def _create_content_version(
    *,
    block_placement: SectionBlockPlacement,
    content: dict,
    action: str,
    actor,
    notes: str = "",
) -> ContentVersion:
    """Create a content version snapshot."""
    latest = CMSContentVersionSelector.get_latest_version(
        block_placement_id=block_placement.id
    )
    next_number = (latest.version_number + 1) if latest else 1

    version = ContentVersion.objects.create(
        block_placement=block_placement,
        content_snapshot=content or {},
        version_number=next_number,
        action=action,
        created_by=actor,
        notes=notes,
    )

    # Prune old versions beyond retention limit
    _prune_old_versions(block_placement_id=block_placement.id)

    return version


def _create_content_version_throttled(
    *,
    block_placement: SectionBlockPlacement,
    content: dict,
    action: str,
    actor,
) -> Optional[ContentVersion]:
    """
    Create version with throttling: max 1 per 30 seconds.
    Within the window, updates the latest version in-place
    (only if same user, same action=draft_save).
    """
    from django.utils import timezone
    import datetime

    latest = CMSContentVersionSelector.get_latest_version(
        block_placement_id=block_placement.id
    )

    if (
        latest
        and latest.action == ContentVersionAction.DRAFT_SAVE
        and latest.created_by == actor
        and (timezone.now() - latest.created_at).total_seconds() < VERSION_THROTTLE_SECONDS
    ):
        # Update in-place
        latest.content_snapshot = content or {}
        latest.save(update_fields=["content_snapshot"])
        return latest

    return _create_content_version(
        block_placement=block_placement,
        content=content,
        action=action,
        actor=actor,
    )


def _prune_old_versions(*, block_placement_id: UUID) -> None:
    """Remove versions beyond MAX_VERSIONS_PER_PLACEMENT (oldest first)."""
    version_ids = list(
        ContentVersion.objects.filter(block_placement_id=block_placement_id)
        .order_by("-version_number")
        .values_list("id", flat=True)[MAX_VERSIONS_PER_PLACEMENT:]
    )
    if version_ids:
        ContentVersion.objects.filter(id__in=version_ids).delete()


def _sync_media_usage(
    *,
    block_placement: SectionBlockPlacement,
    content: Optional[dict],
    layer: str,
) -> None:
    """
    Scan content JSONB for media references and sync MediaUsage records.
    Deletes old usages for this layer, creates new ones.
    """
    # Delete existing usages for this layer
    MediaUsage.objects.filter(
        block_placement=block_placement,
        content_layer=layer,
    ).delete()

    if not content:
        return

    # Extract media_id references from content
    media_refs = _extract_media_references(content=content)

    for field_key, media_id in media_refs:
        MediaUsage.objects.create(
            media_file_id=media_id,
            block_placement=block_placement,
            field_key=field_key,
            content_layer=layer,
        )


def _extract_media_references(*, content: dict, prefix: str = "") -> list[tuple[str, UUID]]:
    """
    Recursively extract (field_key, media_id) pairs from content JSONB.
    Handles media fields {"media_id": "uuid", "alt": "..."} and repeaters.
    """
    refs = []
    for key, value in content.items():
        full_key = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict) and "media_id" in value:
            try:
                refs.append((full_key, UUID(value["media_id"])))
            except (ValueError, TypeError):
                pass
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    refs.extend(
                        _extract_media_references(
                            content=item,
                            prefix=f"{full_key}[{i}]",
                        )
                    )
    return refs


def _null_draft_media_references(*, media_file: MediaFile) -> None:
    """Null out all draft_content references to a deleted media file."""
    draft_usages = MediaUsage.objects.filter(
        media_file=media_file,
        content_layer=ContentLayer.DRAFT,
    ).select_related("block_placement")

    for usage in draft_usages:
        bp = usage.block_placement
        if bp.draft_content:
            _null_media_id_in_content(
                content=bp.draft_content,
                target_media_id=str(media_file.id),
            )
            bp.save(update_fields=["draft_content", "updated_at"])

    # Clean up draft usage records
    MediaUsage.objects.filter(
        media_file=media_file,
        content_layer=ContentLayer.DRAFT,
    ).delete()


def _null_media_id_in_content(*, content: dict, target_media_id: str) -> None:
    """Recursively null out media references matching target_media_id."""
    for key, value in content.items():
        if isinstance(value, dict) and value.get("media_id") == target_media_id:
            content[key] = None
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _null_media_id_in_content(content=item, target_media_id=target_media_id)


def _serialize_page_for_export(page: Page) -> dict:
    """Serialize a page with full tree for export."""
    return {
        "slug": page.slug,
        "title": page.title,
        "path": page.path,
        "page_type": page.page_type,
        "status": page.status,
        "metadata": page.metadata,
        "section_placements": [
            {
                "id": str(sp.id),
                "template_slug": sp.template.slug,
                "order": sp.order,
                "is_required": sp.is_required,
                "is_visible": sp.is_visible,
                "block_placements": [
                    {
                        "id": str(bp.id),
                        "template_slug": bp.template.slug,
                        "order": bp.order,
                        "is_required": bp.is_required,
                        "is_visible": bp.is_visible,
                        "schema": bp.template.schema,
                        "draft_content": bp.draft_content,
                        "published_content": bp.published_content,
                        "default_content": bp.template.default_content,
                    }
                    for bp in sp.block_placements.order_by("order")
                ],
            }
            for sp in page.section_placements.order_by("order")
        ],
    }


def _extract_block_placements_from_import(import_data: dict) -> list[dict]:
    """Extract block placement data from import JSON."""
    blocks = []
    page_data = import_data.get("page", {})
    for sp in page_data.get("section_placements", []):
        for bp in sp.get("block_placements", []):
            blocks.append(bp)
    return blocks
```

### 6.8 SchemaValidator (`apps/cms/validators.py`)

```python
"""
CMS Schema Validator
=====================
Validates content JSONB against BlockTemplate schema.
Two modes: permissive (draft save) and strict (publish).
"""

import re
from typing import Optional
from apps.cms.constants import CMS_FIELD_TYPES
from apps.core.observability import get_logger

logger = get_logger(__name__)


class SchemaValidator:
    """
    Validates content against a block template schema.

    Usage:
        errors = SchemaValidator.validate_content(
            schema=template.schema,
            content=placement.draft_content,
            strict=True,  # False for draft save
        )
    """

    @staticmethod
    def validate_schema_structure(*, schema: dict) -> None:
        """
        Validate the schema definition itself (not content).
        Called when creating/updating block templates.
        """
        from apps.core.exceptions import ValidationError

        if "fields" not in schema:
            raise ValidationError(message="Schema must contain a 'fields' array")

        if not isinstance(schema["fields"], list):
            raise ValidationError(message="Schema 'fields' must be an array")

        seen_keys = set()
        for field in schema["fields"]:
            if "key" not in field or "type" not in field:
                raise ValidationError(
                    message="Each field must have 'key' and 'type'",
                )
            if field["type"] not in CMS_FIELD_TYPES:
                raise ValidationError(
                    message=f"Unknown field type: {field['type']}",
                )
            if field["key"] in seen_keys:
                raise ValidationError(
                    message=f"Duplicate field key: {field['key']}",
                )
            seen_keys.add(field["key"])

            # Validate repeater sub-schema (no nesting)
            if field["type"] == "repeater":
                if "item_schema" not in field:
                    raise ValidationError(
                        message=f"Repeater field '{field['key']}' must have 'item_schema'",
                    )
                for sub_field in field["item_schema"].get("fields", []):
                    if sub_field.get("type") == "repeater":
                        raise ValidationError(
                            message="Nested repeaters are not allowed",
                        )

    @staticmethod
    def validate_content(
        *,
        schema: dict,
        content: dict,
        strict: bool = False,
    ) -> list[dict]:
        """
        Validate content JSONB against schema.

        Args:
            schema: BlockTemplate.schema
            content: The content JSONB to validate
            strict: If True (publish), returns errors. If False (draft), returns warnings.

        Returns:
            List of error/warning dicts: [{"field_key": ..., "error_type": ..., "message": ...}]
        """
        issues = []
        fields = schema.get("fields", [])

        for field_def in fields:
            key = field_def["key"]
            field_type = field_def["type"]
            required = field_def.get("required", False)
            value = content.get(key)

            # Required check
            if required and (value is None or value == "" or value == []):
                if strict:
                    issues.append({
                        "field_key": key,
                        "error_type": "required_field_empty",
                        "message": f"{field_def.get('label', key)} is required",
                    })
                continue

            # Skip validation if value is None/empty (non-required)
            if value is None or value == "":
                continue

            # Type-specific validation
            validation = field_def.get("validation", {})
            field_issues = SchemaValidator._validate_field_value(
                key=key,
                field_type=field_type,
                value=value,
                validation=validation,
                field_def=field_def,
                strict=strict,
            )
            issues.extend(field_issues)

        return issues

    @staticmethod
    def sanitize_content(*, schema: dict, content: dict) -> dict:
        """
        Sanitize richtext fields in content dict. Returns a new sanitized dict.

        Must be called BEFORE validate_content so validation operates on clean HTML.
        Services call this before saving draft_content:

            content = SchemaValidator.sanitize_content(schema=schema, content=content)
            warnings = SchemaValidator.validate_content(schema=schema, content=content, strict=False)
            placement.draft_content = content  # now sanitized
        """
        import nh3

        sanitized = dict(content)  # Shallow copy — mutate only richtext values
        fields = schema.get("fields", [])

        for field_def in fields:
            key = field_def["key"]
            field_type = field_def["type"]
            value = sanitized.get(key)

            if field_type == "richtext" and isinstance(value, str):
                allowed_tags = set(field_def.get("allowed_tags", [
                    "p", "br", "strong", "em", "u", "s", "a", "ul", "ol", "li",
                    "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "code", "pre",
                ]))
                sanitized[key] = nh3.clean(value, tags=allowed_tags)

            elif field_type == "repeater" and isinstance(value, list):
                # Recursively sanitize repeater items
                item_schema = field_def.get("item_schema", {})
                sanitized[key] = [
                    SchemaValidator.sanitize_content(schema=item_schema, content=item)
                    if isinstance(item, dict) else item
                    for item in value
                ]

        return sanitized

    @staticmethod
    def _validate_field_value(
        *,
        key: str,
        field_type: str,
        value,
        validation: dict,
        field_def: dict,
        strict: bool,
    ) -> list[dict]:
        """Validate a single field value against its type and validation rules."""
        issues = []

        if field_type in ("text", "textarea"):
            if not isinstance(value, str):
                issues.append({"field_key": key, "error_type": "type_error", "message": f"{key} must be a string"})
                return issues
            if "max_length" in validation and len(value) > validation["max_length"]:
                issues.append({"field_key": key, "error_type": "max_length", "message": f"{key} exceeds max length"})
            if "min_length" in validation and len(value) < validation["min_length"]:
                issues.append({"field_key": key, "error_type": "min_length", "message": f"{key} below min length"})
            if "pattern" in validation and not re.match(validation["pattern"], value):
                issues.append({"field_key": key, "error_type": "pattern_mismatch", "message": f"{key} does not match pattern"})

        elif field_type == "richtext":
            if not isinstance(value, str):
                issues.append({"field_key": key, "error_type": "type_error", "message": f"{key} must be a string"})
                return issues
            # NOTE: Sanitization is handled by sanitize_content() — called BEFORE validation.
            # This method only validates constraints (length, etc.) on already-sanitized values.
            # Length check on stripped text
            if "max_length" in validation:
                import html
                stripped = html.unescape(re.sub(r"<[^>]+>", "", value))
                if len(stripped) > validation["max_length"]:
                    issues.append({"field_key": key, "error_type": "max_length", "message": f"{key} text content exceeds max length"})

        elif field_type == "number":
            if not isinstance(value, (int, float)):
                issues.append({"field_key": key, "error_type": "type_error", "message": f"{key} must be a number"})
                return issues
            if "min" in validation and value < validation["min"]:
                issues.append({"field_key": key, "error_type": "min_value", "message": f"{key} below minimum"})
            if "max" in validation and value > validation["max"]:
                issues.append({"field_key": key, "error_type": "max_value", "message": f"{key} above maximum"})

        elif field_type == "boolean":
            if not isinstance(value, bool):
                issues.append({"field_key": key, "error_type": "type_error", "message": f"{key} must be boolean"})

        elif field_type in ("select",):
            choices = [c["value"] for c in validation.get("choices", [])]
            if choices and value not in choices:
                issues.append({"field_key": key, "error_type": "invalid_choice", "message": f"{key} value not in choices"})

        elif field_type == "multiselect":
            if not isinstance(value, list):
                issues.append({"field_key": key, "error_type": "type_error", "message": f"{key} must be a list"})
                return issues
            choices = [c["value"] for c in validation.get("choices", [])]
            if choices:
                for v in value:
                    if v not in choices:
                        issues.append({"field_key": key, "error_type": "invalid_choice", "message": f"{key} contains invalid choice: {v}"})
            if "min_selected" in validation and len(value) < validation["min_selected"]:
                issues.append({"field_key": key, "error_type": "min_selected", "message": f"{key} below minimum selections"})
            if "max_selected" in validation and len(value) > validation["max_selected"]:
                issues.append({"field_key": key, "error_type": "max_selected", "message": f"{key} above maximum selections"})

        elif field_type == "media":
            if not isinstance(value, dict) or "media_id" not in value:
                issues.append({"field_key": key, "error_type": "type_error", "message": f"{key} must be a media reference object"})
                return issues
            if strict:
                # Check that media exists and is not tombstoned
                from apps.cms.models import MediaFile
                media = MediaFile.objects.filter(id=value["media_id"], is_deleted=False).first()
                if not media:
                    issues.append({"field_key": key, "error_type": "media_not_found", "message": f"{key} references non-existent media"})
                elif media.is_tombstoned:
                    issues.append({"field_key": key, "error_type": "media_reference_tombstoned", "message": f"{key} references tombstoned media"})

        elif field_type == "repeater":
            if not isinstance(value, list):
                issues.append({"field_key": key, "error_type": "type_error", "message": f"{key} must be a list"})
                return issues
            if "min_items" in validation and len(value) < validation["min_items"]:
                issues.append({"field_key": key, "error_type": "min_items", "message": f"{key} below minimum items"})
            if "max_items" in validation and len(value) > validation["max_items"]:
                issues.append({"field_key": key, "error_type": "max_items", "message": f"{key} above maximum items"})
            # Validate each item against item_schema
            item_schema = field_def.get("item_schema", {})
            if item_schema:
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        sub_issues = SchemaValidator.validate_content(
                            schema=item_schema,
                            content=item,
                            strict=strict,
                        )
                        for issue in sub_issues:
                            issue["field_key"] = f"{key}[{i}].{issue['field_key']}"
                            issues.append(issue)

        # Additional types (url, email, date, datetime, list, relation, json, color, icon)
        # follow similar patterns — validate format, range, and reference integrity

        return issues
```

---

## 7. Policies

### 7.1 CMSPolicy (`apps/cms/policies.py`)

```python
"""
CMS Policies
==============
Authorization logic for CMS actions.

The CMS uses MembershipPolicy.authorize_action() directly in service methods
(same pattern as Form Builder). This module provides additional CMS-specific
policy checks that go beyond permission checks.
"""

from apps.core.exceptions import PermissionDenied, BusinessRuleViolation
from apps.cms.models import Page, PageSectionPlacement, SectionBlockPlacement


class CMSPolicy:
    """CMS-specific authorization checks beyond RBAC permissions."""

    @staticmethod
    def can_delete_page(*, page: Page) -> None:
        """Check if a page can be deleted."""
        if page.is_required:
            raise BusinessRuleViolation(
                message="Required pages cannot be deleted",
                rule="required_page_delete",
            )

    @staticmethod
    def can_hide_page(*, page: Page) -> None:
        """Check if a page can be hidden."""
        if page.is_required:
            raise BusinessRuleViolation(
                message="Required pages cannot be hidden",
                rule="required_page_hide",
            )

    @staticmethod
    def can_hide_section_placement(*, placement: PageSectionPlacement) -> None:
        """Check if a section placement can be hidden."""
        if placement.is_required:
            raise BusinessRuleViolation(
                message="Required section placements cannot be hidden",
                rule="required_section_hide",
            )

    @staticmethod
    def can_hide_block_placement(*, placement: SectionBlockPlacement) -> None:
        """Check if a block placement can be hidden."""
        if placement.is_required:
            raise BusinessRuleViolation(
                message="Required block placements cannot be hidden",
                rule="required_block_hide",
            )
```

---

## 8. ActorContext Usage Pattern

```python
# Reference: apps/rbac/views.py — PlatformContextMixin
#
# CMS views use PlatformContextMixin to build ActorContext
# because CMS is currently platform-only.
#
# Pattern in views:
#   class CMSAdminSiteView(PlatformContextMixin, APIView):
#       def post(self, request):
#           actor_context = self.get_actor_context(request)
#           site = CMSSiteService.create_site(
#               actor_context=actor_context,
#               ...
#           )
#
# PlatformContextMixin:
#   1. Resolves membership: MembershipSelector.get_active_membership_for_user_account(
#          user=request.user, account_type=AccountType.PLATFORM, account_id=platform_id)
#   2. Builds context: RBACService.build_actor_context(membership=membership, request=request)
#   3. Returns ActorContext with permissions snapshot
#
# Permission checking (in services via MembershipPolicy):
#   MembershipPolicy.authorize_action(
#       actor_context=actor_context,
#       target_membership=None,  # Resource-level action (no member target)
#       required_permission="can_edit_cms_content",
#   )
#
# When business CMS access is added:
#   Use BusinessContextMixin for business-scoped operations
```

---

## 9. API Views

### 9.1 Admin API Views (`apps/cms/api/views.py`)

```python
"""
CMS API Views
==============
Admin and Public API views.

Admin views use PlatformContextMixin (platform-only).
Public views use CMS API key authentication.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema

from apps.core.permissions import IsAuthenticated, IsSuperuser
from apps.core.pagination import StandardPagination
from apps.rbac.views import PlatformContextMixin
from apps.cms.services import (
    CMSTemplateService, CMSPageService, CMSContentService,
    CMSMediaService, CMSApiKeyService,
)
from apps.cms.selectors import (
    CMSSiteSelector, CMSPageSelector, CMSTemplateSelector,
    CMSBlockPlacementSelector, CMSMediaSelector,
    CMSContentVersionSelector, CMSApiKeySelector,
)
from apps.cms.api.serializers import (
    # Input serializers
    SiteCreateSerializer, SiteUpdateSerializer,
    PageCreateSerializer, PageUpdateSerializer,
    SectionTemplateCreateSerializer, BlockTemplateCreateSerializer,
    BlockSchemaUpdateSerializer,
    DraftContentUpdateSerializer,
    ReorderSerializer,
    MediaUploadSerializer, MediaUpdateSerializer,
    ApiKeyCreateSerializer, ApiKeyUpdateSerializer,
    PageImportSerializer,
    # Output serializers
    SiteOutputSerializer, PageOutputSerializer, PageDetailOutputSerializer,
    SectionTemplateOutputSerializer, BlockTemplateOutputSerializer,
    SectionPlacementOutputSerializer, BlockPlacementOutputSerializer,
    ContentVersionOutputSerializer,
    MediaFolderOutputSerializer, MediaFileOutputSerializer,
    MediaUsageOutputSerializer,
    ApiKeyOutputSerializer, ApiKeyCreatedOutputSerializer,
    PublishErrorOutputSerializer,
    PageExportOutputSerializer,
)


# ---------------------------------------------------------------------------
# Admin — Sites
# ---------------------------------------------------------------------------

class AdminSiteListCreateView(PlatformContextMixin, APIView):
    """
    GET  /api/v1/cms/admin/sites/  → List sites (platform-scoped)
    POST /api/v1/cms/admin/sites/  → Create site (superuser)
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=SiteOutputSerializer(many=True))
    def get(self, request):
        actor_context = self.get_actor_context(request)
        sites = CMSSiteSelector.list_for_owner(
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(sites, request)
        serializer = SiteOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(request=SiteCreateSerializer, responses=SiteOutputSerializer)
    def post(self, request):
        serializer = SiteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context(request)
        # Site creation is structural — delegate to service
        from apps.cms.services import CMSSiteService
        site = CMSSiteService.create_site(
            actor_context=actor_context,
            request=request,
            **serializer.validated_data,
        )
        return Response(SiteOutputSerializer(site).data, status=status.HTTP_201_CREATED)


class AdminSiteDetailView(PlatformContextMixin, APIView):
    """
    GET    /api/v1/cms/admin/sites/{slug}/  → Get site details
    PATCH  /api/v1/cms/admin/sites/{slug}/  → Update site
    DELETE /api/v1/cms/admin/sites/{slug}/  → Delete site (superuser)
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=SiteOutputSerializer)
    def get(self, request, slug):
        actor_context = self.get_actor_context(request)
        site = CMSSiteSelector.get_by_slug(
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            slug=slug,
        )
        return Response(SiteOutputSerializer(site).data)

    @extend_schema(request=SiteUpdateSerializer, responses=SiteOutputSerializer)
    def patch(self, request, slug):
        serializer = SiteUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context(request)
        from apps.cms.services import CMSSiteService
        site = CMSSiteService.update_site(
            actor_context=actor_context,
            slug=slug,
            request=request,
            **serializer.validated_data,
        )
        return Response(SiteOutputSerializer(site).data)

    def delete(self, request, slug):
        actor_context = self.get_actor_context(request)
        from apps.cms.services import CMSSiteService
        CMSSiteService.delete_site(
            actor_context=actor_context, slug=slug, request=request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Admin — Pages
# ---------------------------------------------------------------------------

class AdminPageListCreateView(PlatformContextMixin, APIView):
    """
    GET  /api/v1/cms/admin/pages/  → List pages (filterable by site, status)
    POST /api/v1/cms/admin/pages/  → Create page (superuser)
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=PageOutputSerializer(many=True))
    def get(self, request):
        site_slug = request.query_params.get("site")
        status_filter = request.query_params.get("status")
        actor_context = self.get_actor_context(request)

        if site_slug:
            site = CMSSiteSelector.get_by_slug(
                owner_type=actor_context.account_type,
                owner_id=actor_context.account_id,
                slug=site_slug,
            )
            pages = CMSPageSelector.list_by_site(
                site_id=site.id, status=status_filter,
            )
        else:
            # List all pages across sites for this owner
            pages = Page.objects.filter(
                site__owner_type=actor_context.account_type,
                site__owner_id=actor_context.account_id,
            )
            if status_filter:
                pages = pages.filter(status=status_filter)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(pages, request)
        serializer = PageOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(request=PageCreateSerializer, responses=PageOutputSerializer)
    def post(self, request):
        serializer = PageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context(request)
        page = CMSPageService.create_page(
            actor_context=actor_context,
            request=request,
            **serializer.validated_data,
        )
        return Response(PageOutputSerializer(page).data, status=status.HTTP_201_CREATED)


class AdminPageDetailView(PlatformContextMixin, APIView):
    """
    GET    /api/v1/cms/admin/pages/{slug}/  → Get page (with optional depth)
    PATCH  /api/v1/cms/admin/pages/{slug}/  → Update page metadata
    DELETE /api/v1/cms/admin/pages/{slug}/  → Delete page (superuser)
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=PageDetailOutputSerializer)
    def get(self, request, slug):
        actor_context = self.get_actor_context(request)
        depth = request.query_params.get("depth", None)
        site_slug = request.query_params.get("site")

        site = CMSSiteSelector.get_by_slug(
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            slug=site_slug,
        ) if site_slug else None

        if depth == "full" and site:
            page = CMSPageSelector.get_by_slug(site_id=site.id, slug=slug)
            page = CMSPageSelector.get_with_full_tree(page_id=page.id)
            return Response(PageDetailOutputSerializer(page).data)

        if site:
            page = CMSPageSelector.get_by_slug(site_id=site.id, slug=slug)
        else:
            page = Page.objects.filter(slug=slug).first()
            if not page:
                from apps.core.exceptions import NotFound
                raise NotFound(resource="Page", resource_id=slug)

        return Response(PageOutputSerializer(page).data)


class AdminPagePublishView(PlatformContextMixin, APIView):
    """POST /api/v1/cms/admin/pages/{slug}/publish/ → Validate & publish page."""
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        actor_context = self.get_actor_context(request)
        site_slug = request.query_params.get("site")
        site = CMSSiteSelector.get_by_slug(
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            slug=site_slug,
        )
        page = CMSPageSelector.get_by_slug(site_id=site.id, slug=slug)
        page = CMSPageService.publish_page(
            actor_context=actor_context, page_id=page.id, request=request,
        )
        return Response(PageOutputSerializer(page).data)


class AdminPageUnpublishView(PlatformContextMixin, APIView):
    """POST /api/v1/cms/admin/pages/{slug}/unpublish/ → Revert to draft."""
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        actor_context = self.get_actor_context(request)
        site_slug = request.query_params.get("site")
        site = CMSSiteSelector.get_by_slug(
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            slug=site_slug,
        )
        page = CMSPageSelector.get_by_slug(site_id=site.id, slug=slug)
        page = CMSPageService.unpublish_page(
            actor_context=actor_context, page_id=page.id, request=request,
        )
        return Response(PageOutputSerializer(page).data)


class AdminPageExportView(PlatformContextMixin, APIView):
    """POST /api/v1/cms/admin/pages/{slug}/export/ → Export page tree as JSON."""
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        actor_context = self.get_actor_context(request)
        site_slug = request.query_params.get("site")
        site = CMSSiteSelector.get_by_slug(
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            slug=site_slug,
        )
        page = CMSPageSelector.get_by_slug(site_id=site.id, slug=slug)
        export_data = CMSPageService.export_page(
            actor_context=actor_context, page_id=page.id, request=request,
        )
        return Response(export_data)


class AdminPageImportView(PlatformContextMixin, APIView):
    """POST /api/v1/cms/admin/pages/{slug}/import/ → Import page content."""
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        serializer = PageImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context(request)
        site_slug = request.query_params.get("site")
        site = CMSSiteSelector.get_by_slug(
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            slug=site_slug,
        )
        page = CMSPageSelector.get_by_slug(site_id=site.id, slug=slug)
        page = CMSPageService.import_page(
            actor_context=actor_context,
            page_id=page.id,
            import_data=serializer.validated_data,
            request=request,
        )
        return Response(PageOutputSerializer(page).data)


# ---------------------------------------------------------------------------
# Admin — Templates
# ---------------------------------------------------------------------------

class AdminSectionTemplateListCreateView(PlatformContextMixin, APIView):
    """
    GET  /api/v1/cms/admin/templates/sections/  → List section templates
    POST /api/v1/cms/admin/templates/sections/  → Create section template
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        section_type = request.query_params.get("section_type")
        templates = CMSTemplateSelector.list_section_templates(section_type=section_type)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(templates, request)
        serializer = SectionTemplateOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = SectionTemplateCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context(request)
        template = CMSTemplateService.create_section_template(
            actor_context=actor_context, request=request,
            **serializer.validated_data,
        )
        return Response(
            SectionTemplateOutputSerializer(template).data,
            status=status.HTTP_201_CREATED,
        )


class AdminBlockTemplateListCreateView(PlatformContextMixin, APIView):
    """
    GET  /api/v1/cms/admin/templates/blocks/  → List block templates
    POST /api/v1/cms/admin/templates/blocks/  → Create block template
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        block_type = request.query_params.get("block_type")
        templates = CMSTemplateSelector.list_block_templates(block_type=block_type)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(templates, request)
        serializer = BlockTemplateOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = BlockTemplateCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context(request)
        template = CMSTemplateService.create_block_template(
            actor_context=actor_context, request=request,
            **serializer.validated_data,
        )
        return Response(
            BlockTemplateOutputSerializer(template).data,
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Admin — Block Placements (content interaction)
# ---------------------------------------------------------------------------

class AdminBlockPlacementDetailView(PlatformContextMixin, APIView):
    """
    GET   /api/v1/cms/admin/block-placements/{uuid}/ → Get block placement
    PATCH /api/v1/cms/admin/block-placements/{uuid}/ → Update draft_content
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, uuid):
        placement = CMSBlockPlacementSelector.get_by_id(block_placement_id=uuid)
        return Response(BlockPlacementOutputSerializer(placement).data)

    def patch(self, request, uuid):
        serializer = DraftContentUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context(request)
        placement = CMSContentService.update_draft_content(
            actor_context=actor_context,
            block_placement_id=uuid,
            content=serializer.validated_data["draft_content"],
            request=request,
        )
        return Response(BlockPlacementOutputSerializer(placement).data)


class AdminBlockPlacementHistoryView(PlatformContextMixin, APIView):
    """GET /api/v1/cms/admin/block-placements/{uuid}/history/ → List versions."""
    permission_classes = [IsAuthenticated]

    def get(self, request, uuid):
        versions = CMSContentVersionSelector.list_for_placement(
            block_placement_id=uuid,
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(versions, request)
        serializer = ContentVersionOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminBlockPlacementRollbackView(PlatformContextMixin, APIView):
    """POST /api/v1/cms/admin/block-placements/{uuid}/rollback/{version}/ → Rollback."""
    permission_classes = [IsAuthenticated]

    def post(self, request, uuid, version):
        actor_context = self.get_actor_context(request)
        placement = CMSContentService.rollback_content(
            actor_context=actor_context,
            block_placement_id=uuid,
            version_number=int(version),
            request=request,
        )
        return Response(BlockPlacementOutputSerializer(placement).data)


# ---------------------------------------------------------------------------
# Admin — Media
# ---------------------------------------------------------------------------

class AdminMediaFileListCreateView(PlatformContextMixin, APIView):
    """
    GET  /api/v1/cms/admin/media/files/  → List files
    POST /api/v1/cms/admin/media/files/  → Upload file
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        actor_context = self.get_actor_context(request)
        folder_id = request.query_params.get("folder")
        mime_type = request.query_params.get("type")
        files = CMSMediaSelector.list_files(
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            folder_id=folder_id,
            mime_type=mime_type,
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(files, request)
        serializer = MediaFileOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = MediaUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context(request)
        media = CMSMediaService.upload_file(
            actor_context=actor_context,
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            request=request,
            **serializer.validated_data,
        )
        return Response(MediaFileOutputSerializer(media).data, status=status.HTTP_201_CREATED)


class AdminMediaFileDetailView(PlatformContextMixin, APIView):
    """
    GET    /api/v1/cms/admin/media/files/{uuid}/ → Get file details
    PATCH  /api/v1/cms/admin/media/files/{uuid}/ → Update metadata
    DELETE /api/v1/cms/admin/media/files/{uuid}/ → Delete file
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, uuid):
        media = CMSMediaSelector.get_file_by_id(file_id=uuid)
        return Response(MediaFileOutputSerializer(media).data)

    def patch(self, request, uuid):
        serializer = MediaUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Update metadata via service
        actor_context = self.get_actor_context(request)
        from apps.cms.services import CMSMediaService
        # STUB: CMSMediaService.update_file_metadata(...)
        media = CMSMediaSelector.get_file_by_id(file_id=uuid)
        return Response(MediaFileOutputSerializer(media).data)

    def delete(self, request, uuid):
        actor_context = self.get_actor_context(request)
        CMSMediaService.delete_file(
            actor_context=actor_context, file_id=uuid, request=request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Admin — API Keys
# ---------------------------------------------------------------------------

class AdminApiKeyListCreateView(PlatformContextMixin, APIView):
    """
    GET  /api/v1/cms/admin/api-keys/ → List API keys for a site
    POST /api/v1/cms/admin/api-keys/ → Create API key (returns full key ONCE)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        site_id = request.query_params.get("site")
        keys = CMSApiKeySelector.list_for_site(site_id=site_id)
        serializer = ApiKeyOutputSerializer(keys, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ApiKeyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context(request)
        api_key, plaintext = CMSApiKeyService.create_api_key(
            actor_context=actor_context, request=request,
            **serializer.validated_data,
        )
        output = ApiKeyCreatedOutputSerializer(api_key).data
        output["key"] = plaintext  # Returned ONCE
        return Response(output, status=status.HTTP_201_CREATED)


class AdminApiKeyDetailView(PlatformContextMixin, APIView):
    """
    PATCH  /api/v1/cms/admin/api-keys/{uuid}/ → Update key settings
    DELETE /api/v1/cms/admin/api-keys/{uuid}/ → Revoke key
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, uuid):
        actor_context = self.get_actor_context(request)
        CMSApiKeyService.revoke_api_key(
            actor_context=actor_context, api_key_id=uuid, request=request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class PublicSiteView(APIView):
    """GET /api/v1/cms/public/sites/{slug}/ → Get published site info."""
    permission_classes = []  # API key checked in middleware

    def get(self, request, slug):
        # API key validated by middleware, site set on request
        site = getattr(request, "cms_site", None)
        if not site or site.slug != slug:
            from apps.core.exceptions import NotFound
            raise NotFound(resource="Site", resource_id=slug)
        return Response(SiteOutputSerializer(site).data)


class PublicPageView(APIView):
    """
    GET /api/v1/cms/public/pages/{slug}/ → Get published page.
    Supports ?depth=full for full tree with published_content.
    """
    permission_classes = []

    def get(self, request, slug):
        site = getattr(request, "cms_site", None)
        if not site:
            from apps.core.exceptions import PermissionDenied
            raise PermissionDenied(message="Valid API key required")

        depth = request.query_params.get("depth")
        page = CMSPageSelector.get_by_slug(site_id=site.id, slug=slug)

        if page.status != PageStatus.PUBLISHED or not page.is_visible:
            from apps.core.exceptions import NotFound
            raise NotFound(resource="Page", resource_id=slug)

        if depth == "full":
            page = CMSPageSelector.get_with_full_tree(page_id=page.id)
            # Use public serializer that returns published_content only
            return Response(PageDetailOutputSerializer(page, context={"public": True}).data)

        return Response(PageOutputSerializer(page).data)
```

---

## 10. Serializers

### 10.1 Serializers (`apps/cms/api/serializers.py`)

```python
"""
CMS Serializers
================
Input (validation) and Output (response shaping) serializers.
Follows BaseInputSerializer/BaseOutputSerializer patterns from apps.core.
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
    default_locale = serializers.CharField(max_length=10, required=False, default="en")
    metadata = serializers.JSONField(required=False, default=None)


class SiteUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    domain = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False)
    default_locale = serializers.CharField(max_length=10, required=False)
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
    """Page with full tree: sections → blocks."""
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
```

---

## 11. URL Configuration

### 11.1 Admin URLs (`apps/cms/api/urls.py`)

```python
"""
CMS Admin URL Configuration
=============================
Admin API endpoints — requires authentication + RBAC permissions.

Include in project urls.py:
    path("api/v1/cms/admin/", include("apps.cms.api.urls", namespace="cms-admin")),
"""

from django.urls import path
from apps.cms.api import views

app_name = "cms"

urlpatterns = [
    # Sites
    path("sites/", views.AdminSiteListCreateView.as_view(), name="admin-site-list-create"),
    path("sites/<slug:slug>/", views.AdminSiteDetailView.as_view(), name="admin-site-detail"),

    # Pages
    path("pages/", views.AdminPageListCreateView.as_view(), name="admin-page-list-create"),
    path("pages/<slug:slug>/", views.AdminPageDetailView.as_view(), name="admin-page-detail"),
    path("pages/<slug:slug>/publish/", views.AdminPagePublishView.as_view(), name="admin-page-publish"),
    path("pages/<slug:slug>/unpublish/", views.AdminPageUnpublishView.as_view(), name="admin-page-unpublish"),
    path("pages/<slug:slug>/export/", views.AdminPageExportView.as_view(), name="admin-page-export"),
    path("pages/<slug:slug>/import/", views.AdminPageImportView.as_view(), name="admin-page-import"),

    # Templates — Sections
    path("templates/sections/", views.AdminSectionTemplateListCreateView.as_view(), name="admin-section-template-list-create"),
    # path("templates/sections/<slug:slug>/", ..., name="admin-section-template-detail"),

    # Templates — Blocks
    path("templates/blocks/", views.AdminBlockTemplateListCreateView.as_view(), name="admin-block-template-list-create"),
    # path("templates/blocks/<slug:slug>/", ..., name="admin-block-template-detail"),

    # Block Placements (content)
    path("block-placements/<uuid:uuid>/", views.AdminBlockPlacementDetailView.as_view(), name="admin-block-placement-detail"),
    path("block-placements/<uuid:uuid>/history/", views.AdminBlockPlacementHistoryView.as_view(), name="admin-block-placement-history"),
    path("block-placements/<uuid:uuid>/rollback/<int:version>/", views.AdminBlockPlacementRollbackView.as_view(), name="admin-block-placement-rollback"),

    # Media
    path("media/files/", views.AdminMediaFileListCreateView.as_view(), name="admin-media-file-list-create"),
    path("media/files/<uuid:uuid>/", views.AdminMediaFileDetailView.as_view(), name="admin-media-file-detail"),
    # path("media/folders/", ..., name="admin-media-folder-list-create"),

    # API Keys
    path("api-keys/", views.AdminApiKeyListCreateView.as_view(), name="admin-api-key-list-create"),
    path("api-keys/<uuid:uuid>/", views.AdminApiKeyDetailView.as_view(), name="admin-api-key-detail"),
]
```

### 11.2 Public URLs (`apps/cms/api/urls_public.py`)

```python
"""
CMS Public URL Configuration
==============================
Public read-only endpoints — authenticated via API key (CMSApiKeyMiddleware).

Include in project urls.py:
    path("api/v1/cms/public/", include("apps.cms.api.urls_public", namespace="cms-public")),
"""

from django.urls import path
from apps.cms.api import views

app_name = "cms-public"

urlpatterns = [
    path("sites/<slug:slug>/", views.PublicSiteView.as_view(), name="public-site"),
    path("pages/<slug:slug>/", views.PublicPageView.as_view(), name="public-page"),
]
```

---

## 12. Django Admin Configuration

### 12.1 Admin (`apps/cms/admin.py`)

```python
"""
CMS Django Admin Configuration
================================
Superuser-only interface for managing CMS structure.
"""

from django.contrib import admin
from apps.cms.models import (
    Site, Page, SectionTemplate, BlockTemplate,
    PageSectionPlacement, SectionBlockPlacement,
    ContentVersion, MediaFolder, MediaFile, CMSApiKey,
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
        ("Settings", {"fields": ["default_locale", "metadata", "is_active", "homepage"]}),
        ("Audit", {"fields": ["id", "created_at", "updated_at", "created_by", "updated_by"]}),
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
        ("Status", {"fields": ["status", "published_at", "order", "is_required", "is_visible"]}),
    ]
    actions = ["publish_pages", "archive_pages"]

    @admin.action(description="Publish selected pages")
    def publish_pages(self, request, queryset):
        # STUB: Call CMSPageService.publish_page for each
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
    list_display = ["block_placement", "version_number", "action", "created_by", "created_at"]
    list_filter = ["action"]
    readonly_fields = [
        "block_placement", "content_snapshot", "version_number",
        "action", "created_by", "created_at", "notes",
    ]


@admin.register(MediaFile)
class MediaFileAdmin(admin.ModelAdmin):
    list_display = ["original_filename", "mime_type", "file_size", "folder", "is_tombstoned"]
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
```

---

## 13. Celery Tasks

### 13.1 Tasks (`apps/cms/tasks.py`)

```python
"""
CMS Celery Tasks
=================
Background tasks using LoggedTask base.
"""

from celery import shared_task
from apps.core.observability import get_logger
# from apps.core.observability.tasks import LoggedTask  # Use if available

logger = get_logger(__name__)


@shared_task(name="cms.cleanup_tombstoned_media")
def cleanup_tombstoned_media():
    """
    Periodic task: Remove tombstoned media files with zero published references.
    Schedule: Daily or as configured in CELERY_BEAT_SCHEDULE.
    """
    from apps.cms.services import CMSMediaService
    cleaned = CMSMediaService.cleanup_tombstoned()
    logger.info("cms.task.cleanup_tombstoned.complete", cleaned_count=cleaned)
    return cleaned


@shared_task(name="cms.prune_content_versions")
def prune_content_versions():
    """
    Periodic task: Prune content versions beyond retention limit.
    Schedule: Weekly.
    """
    from apps.cms.models import SectionBlockPlacement
    from apps.cms.services import _prune_old_versions

    placements = SectionBlockPlacement.objects.all()
    pruned_total = 0
    for placement in placements.iterator():
        _prune_old_versions(block_placement_id=placement.id)
        pruned_total += 1

    logger.info("cms.task.prune_versions.complete", placements_checked=pruned_total)
```

---

## 14. CMS API Key Middleware

### 14.1 Middleware (`apps/cms/middleware.py`)

```python
"""
CMS API Key Authentication Middleware
======================================
Authenticates public CMS API requests via X-CMS-API-Key header.
Validates: key exists, is active, not expired, origin matches.
"""

from django.http import JsonResponse
from django.utils import timezone

from apps.cms.models import CMSApiKey
from apps.core.observability import get_logger

logger = get_logger(__name__)

CMS_PUBLIC_PREFIX = "/api/v1/cms/public/"
API_KEY_HEADER = "HTTP_X_CMS_API_KEY"


class CMSApiKeyMiddleware:
    """
    Middleware that authenticates public CMS API requests.
    Only active on /api/v1/cms/public/ prefix.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith(CMS_PUBLIC_PREFIX):
            return self.get_response(request)

        # Extract API key from header
        api_key_value = request.META.get(API_KEY_HEADER)
        if not api_key_value:
            return JsonResponse(
                {"error": "Missing X-CMS-API-Key header"},
                status=401,
            )

        # Validate key
        key_hash = CMSApiKey.hash_key(api_key_value)
        api_key = (
            CMSApiKey.objects
            .filter(key_hash=key_hash, is_deleted=False)
            .select_related("site")
            .first()
        )

        if not api_key:
            return JsonResponse({"error": "Invalid API key"}, status=401)

        if not api_key.is_active:
            return JsonResponse({"error": "API key is inactive"}, status=403)

        if api_key.expires_at and api_key.expires_at < timezone.now():
            return JsonResponse({"error": "API key has expired"}, status=403)

        # Origin validation
        if api_key.allowed_origins:
            origin = request.META.get("HTTP_ORIGIN", "")
            referer = request.META.get("HTTP_REFERER", "")
            allowed = False
            for allowed_origin in api_key.allowed_origins:
                normalized = allowed_origin.lower().rstrip("/")
                if origin.lower().rstrip("/") == normalized:
                    allowed = True
                    break
                if referer.lower().startswith(normalized):
                    allowed = True
                    break
            if not allowed:
                return JsonResponse({"error": "Origin not allowed"}, status=403)

        # Rate limiting (using Django cache)
        # STUB: Implement per-key rate limiting via cache

        # Set site on request for downstream views
        request.cms_site = api_key.site
        request.cms_api_key = api_key

        # Update last_used_at
        CMSApiKey.objects.filter(id=api_key.id).update(last_used_at=timezone.now())

        return self.get_response(request)
```

---

## 15. Testing Strategy

### 15.1 Test Structure

```
backend/apps/cms/tests/
    __init__.py
    conftest.py              # Fixtures: site, page, templates, placements, RBAC
    factories.py             # All CMS factories
    test_models.py           # Model constraints, __str__, properties
    test_selectors.py        # Selector queries, depth control, filtering
    test_services.py         # Service methods, publish flow, rollback, media
    test_policies.py         # Permission checks per action
    test_validators.py       # SchemaValidator (draft permissive, publish strict)
    test_views.py            # API endpoints, request/response contracts
    test_admin.py            # Django Admin configuration (optional)
```

### 15.2 Factories (`apps/cms/tests/factories.py`)

```python
import uuid
import factory
from apps.cms.models import (
    Site, Page, SectionTemplate, BlockTemplate,
    PageSectionPlacement, SectionBlockPlacement,
    ContentVersion, MediaFolder, MediaFile, CMSApiKey,
)
from apps.users.tests.factories import UserFactory  # Canonical source
from apps.core.constants import OwnerType
from apps.cms.constants import PageStatus, BlockPlacementStatus, ContentVersionAction


class SiteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Site

    owner_type = OwnerType.PLATFORM
    owner_id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"Test Site {n}")
    slug = factory.LazyAttribute(lambda obj: obj.name.lower().replace(" ", "-"))
    domain = ""
    description = ""
    default_locale = "en"
    is_active = True
    created_by = factory.SubFactory(UserFactory)
    updated_by = factory.LazyAttribute(lambda obj: obj.created_by)


class PageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Page

    site = factory.SubFactory(SiteFactory)
    title = factory.Sequence(lambda n: f"Test Page {n}")
    slug = factory.LazyAttribute(lambda obj: obj.title.lower().replace(" ", "-"))
    path = factory.LazyAttribute(lambda obj: f"/{obj.slug}")
    page_type = "content"
    status = PageStatus.DRAFT
    order = factory.Sequence(lambda n: n)
    is_required = False
    is_visible = True
    created_by = factory.SubFactory(UserFactory)
    updated_by = factory.LazyAttribute(lambda obj: obj.created_by)


class SectionTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SectionTemplate

    name = factory.Sequence(lambda n: f"section_template_{n}")
    display_name = factory.LazyAttribute(lambda obj: obj.name.replace("_", " ").title())
    slug = factory.LazyAttribute(lambda obj: obj.name)
    section_type = "content"
    description = ""
    created_by = factory.SubFactory(UserFactory)
    updated_by = factory.LazyAttribute(lambda obj: obj.created_by)


class BlockTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BlockTemplate

    name = factory.Sequence(lambda n: f"block_template_{n}")
    display_name = factory.LazyAttribute(lambda obj: obj.name.replace("_", " ").title())
    slug = factory.LazyAttribute(lambda obj: obj.name)
    block_type = "text"
    schema = factory.LazyFunction(lambda: {
        "fields": [
            {
                "key": "title",
                "type": "text",
                "label": "Title",
                "required": True,
                "validation": {"max_length": 200},
            },
            {
                "key": "body",
                "type": "textarea",
                "label": "Body",
                "required": False,
            },
        ]
    })
    schema_version = 1
    created_by = factory.SubFactory(UserFactory)
    updated_by = factory.LazyAttribute(lambda obj: obj.created_by)


class PageSectionPlacementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PageSectionPlacement

    page = factory.SubFactory(PageFactory)
    template = factory.SubFactory(SectionTemplateFactory)
    order = factory.Sequence(lambda n: n)
    is_required = False
    is_visible = True


class SectionBlockPlacementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SectionBlockPlacement

    section_placement = factory.SubFactory(PageSectionPlacementFactory)
    template = factory.SubFactory(BlockTemplateFactory)
    order = factory.Sequence(lambda n: n)
    is_required = False
    is_visible = True
    draft_content = factory.LazyFunction(lambda: {"title": "Default Title", "body": ""})
    status = BlockPlacementStatus.DRAFT
    created_by = factory.SubFactory(UserFactory)
    updated_by = factory.LazyAttribute(lambda obj: obj.created_by)


class ContentVersionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ContentVersion

    block_placement = factory.SubFactory(SectionBlockPlacementFactory)
    content_snapshot = factory.LazyFunction(lambda: {"title": "Snapshot"})
    version_number = factory.Sequence(lambda n: n + 1)
    action = ContentVersionAction.DRAFT_SAVE
    created_by = factory.SubFactory(UserFactory)


class MediaFolderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MediaFolder

    owner_type = OwnerType.PLATFORM
    owner_id = factory.LazyFunction(uuid.uuid4)
    name = factory.Sequence(lambda n: f"Folder {n}")
    slug = factory.LazyAttribute(lambda obj: obj.name.lower().replace(" ", "-"))
    path = factory.LazyAttribute(lambda obj: f"/{obj.slug}/")
    created_by = factory.SubFactory(UserFactory)
    updated_by = factory.LazyAttribute(lambda obj: obj.created_by)


class MediaFileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MediaFile

    owner_type = OwnerType.PLATFORM
    owner_id = factory.LazyFunction(uuid.uuid4)
    storage_key = factory.Sequence(lambda n: f"platform/test/file_{n}.png")
    original_filename = factory.Sequence(lambda n: f"file_{n}.png")
    mime_type = "image/png"
    file_size = 1024
    is_tombstoned = False
    created_by = factory.SubFactory(UserFactory)
    updated_by = factory.LazyAttribute(lambda obj: obj.created_by)


class CMSApiKeyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CMSApiKey

    site = factory.SubFactory(SiteFactory)
    name = factory.Sequence(lambda n: f"API Key {n}")
    key_prefix = "cmsk_test123"
    key_hash = factory.LazyFunction(lambda: CMSApiKey.generate_key()[2])
    allowed_origins = factory.LazyFunction(list)
    is_active = True
    rate_limit = 60
    created_by = factory.SubFactory(UserFactory)
    updated_by = factory.LazyAttribute(lambda obj: obj.created_by)
```

### 15.3 Conftest Pattern (`apps/cms/tests/conftest.py`)

```python
import pytest
from rest_framework.test import APIClient
from apps.cms.tests.factories import (
    SiteFactory, PageFactory, SectionTemplateFactory, BlockTemplateFactory,
    PageSectionPlacementFactory, SectionBlockPlacementFactory,
    MediaFolderFactory, MediaFileFactory,
)
from apps.users.tests.factories import UserFactory
from apps.organization.tests.factories import PlatformAccountFactory
from apps.core.constants import OwnerType, AccountType
from apps.rbac.services import RBACService
from apps.rbac.selectors import RoleSelector


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def platform_account(db):
    """Get or create the singleton PlatformAccount."""
    from apps.organization.platform.models import PlatformAccount
    platform = PlatformAccount.objects.first()
    if platform:
        return platform
    return PlatformAccountFactory()


@pytest.fixture
def platform_with_rbac(db, user, platform_account):
    """Platform account with RBAC initialized (roles + owner membership)."""
    RBACService.initialize_platform_account(platform_id=platform_account.id)
    owner_role = RoleSelector.get_owner_role(
        account_type=AccountType.PLATFORM,
        account_id=platform_account.id,
    )
    RBACService.create_membership(
        account_type=AccountType.PLATFORM,
        account_id=platform_account.id,
        user=user,
        role_id=owner_role.id,
        created_by=user,
    )
    return platform_account


@pytest.fixture
def actor_context(user, platform_with_rbac):
    """Build ActorContext for the platform owner user."""
    from apps.rbac.selectors import MembershipSelector
    membership = MembershipSelector.get_active_membership_for_user_account(
        user=user,
        account_type=AccountType.PLATFORM,
        account_id=platform_with_rbac.id,
    )
    return RBACService.build_actor_context(membership=membership)


@pytest.fixture
def site(db, user, platform_with_rbac):
    """Create a CMS site owned by the platform."""
    return SiteFactory(
        owner_type=OwnerType.PLATFORM,
        owner_id=platform_with_rbac.id,
        created_by=user,
        updated_by=user,
    )


@pytest.fixture
def page(db, site):
    """Create a draft page in the test site."""
    return PageFactory(site=site, created_by=site.created_by, updated_by=site.created_by)


@pytest.fixture
def section_template(db, user):
    return SectionTemplateFactory(created_by=user, updated_by=user)


@pytest.fixture
def block_template(db, user):
    return BlockTemplateFactory(created_by=user, updated_by=user)


@pytest.fixture
def section_placement(db, page, section_template):
    return PageSectionPlacementFactory(page=page, template=section_template)


@pytest.fixture
def block_placement(db, section_placement, block_template, user):
    return SectionBlockPlacementFactory(
        section_placement=section_placement,
        template=block_template,
        created_by=user,
        updated_by=user,
    )


@pytest.fixture
def published_page(db, site, section_template, block_template, user):
    """Create a fully published page with sections and blocks."""
    from apps.cms.constants import PageStatus, BlockPlacementStatus
    page = PageFactory(
        site=site,
        status=PageStatus.PUBLISHED,
        created_by=user,
        updated_by=user,
    )
    sp = PageSectionPlacementFactory(page=page, template=section_template)
    SectionBlockPlacementFactory(
        section_placement=sp,
        template=block_template,
        draft_content={"title": "Published Title"},
        published_content={"title": "Published Title"},
        status=BlockPlacementStatus.PUBLISHED,
        created_by=user,
        updated_by=user,
    )
    return page


@pytest.fixture
def media_file(db, user, platform_with_rbac):
    return MediaFileFactory(
        owner_type=OwnerType.PLATFORM,
        owner_id=platform_with_rbac.id,
        created_by=user,
        updated_by=user,
    )
```

### 15.4 Key Test Cases

```python
# test_models.py

@pytest.mark.django_db
class TestSiteModel:
    def test_site_str(self, site):
        assert str(site) == site.name

    def test_unique_slug_per_owner(self, site):
        """Duplicate slug within same owner raises IntegrityError."""
        with pytest.raises(IntegrityError):
            SiteFactory(
                owner_type=site.owner_type,
                owner_id=site.owner_id,
                slug=site.slug,
            )


@pytest.mark.django_db
class TestPageModel:
    def test_unique_order_per_site(self, page):
        """Duplicate order within same site raises IntegrityError."""
        with pytest.raises(IntegrityError):
            PageFactory(site=page.site, order=page.order)

    def test_unique_path_per_site(self, page):
        """Duplicate path within same site raises IntegrityError."""
        with pytest.raises(IntegrityError):
            PageFactory(site=page.site, path=page.path, order=999)


# test_services.py

@pytest.mark.django_db
class TestCMSPageService:
    def test_publish_page_validates_all_blocks(self, actor_context, page, block_placement):
        """Publish fails if required fields are empty."""
        block_placement.draft_content = {"title": ""}  # Required but empty
        block_placement.save()

        with pytest.raises(ValidationError) as exc:
            CMSPageService.publish_page(
                actor_context=actor_context, page_id=page.id,
            )
        assert "publish_errors" in str(exc.value) or "validation failed" in str(exc.value).lower()

    def test_publish_copies_draft_to_published(self, actor_context, page, block_placement):
        """Publish copies draft_content to published_content."""
        block_placement.draft_content = {"title": "Hello World", "body": "Content"}
        block_placement.save()

        result = CMSPageService.publish_page(
            actor_context=actor_context, page_id=page.id,
        )

        block_placement.refresh_from_db()
        assert block_placement.published_content == {"title": "Hello World", "body": "Content"}
        assert block_placement.status == BlockPlacementStatus.PUBLISHED
        assert result.status == PageStatus.PUBLISHED

    def test_unpublish_reverts_status(self, actor_context, published_page):
        """Unpublish reverts page to draft without clearing published_content."""
        page = CMSPageService.unpublish_page(
            actor_context=actor_context, page_id=published_page.id,
        )
        assert page.status == PageStatus.DRAFT


@pytest.mark.django_db
class TestCMSContentService:
    def test_update_draft_content(self, actor_context, block_placement):
        result = CMSContentService.update_draft_content(
            actor_context=actor_context,
            block_placement_id=block_placement.id,
            content={"title": "Updated", "body": "New content"},
        )
        assert result.draft_content == {"title": "Updated", "body": "New content"}

    def test_rollback_restores_from_version(self, actor_context, block_placement, user):
        """Rollback restores draft_content from a version snapshot."""
        ContentVersionFactory(
            block_placement=block_placement,
            content_snapshot={"title": "Version 1"},
            version_number=1,
            created_by=user,
        )

        result = CMSContentService.rollback_content(
            actor_context=actor_context,
            block_placement_id=block_placement.id,
            version_number=1,
        )
        assert result.draft_content == {"title": "Version 1"}

    def test_toggle_visibility_fails_for_required(self, actor_context, block_placement):
        """Cannot hide a required block placement."""
        block_placement.is_required = True
        block_placement.save()

        with pytest.raises(BusinessRuleViolation):
            CMSContentService.toggle_visibility(
                actor_context=actor_context,
                block_placement_id=block_placement.id,
                is_visible=False,
            )


# test_validators.py

@pytest.mark.django_db
class TestSchemaValidator:
    def test_permissive_draft_accepts_empty_required(self):
        """Draft mode accepts missing required fields."""
        schema = {"fields": [{"key": "title", "type": "text", "required": True}]}
        issues = SchemaValidator.validate_content(schema=schema, content={}, strict=False)
        assert len(issues) == 0  # Permissive — no errors

    def test_strict_publish_rejects_empty_required(self):
        """Publish mode rejects missing required fields."""
        schema = {"fields": [{"key": "title", "type": "text", "required": True}]}
        issues = SchemaValidator.validate_content(schema=schema, content={}, strict=True)
        assert len(issues) == 1
        assert issues[0]["error_type"] == "required_field_empty"

    def test_max_length_validation(self):
        schema = {
            "fields": [{
                "key": "title", "type": "text", "required": False,
                "validation": {"max_length": 10},
            }]
        }
        issues = SchemaValidator.validate_content(
            schema=schema, content={"title": "x" * 20}, strict=True,
        )
        assert any(i["error_type"] == "max_length" for i in issues)

    def test_repeater_validates_items(self):
        schema = {
            "fields": [{
                "key": "items", "type": "repeater", "required": True,
                "validation": {"min_items": 1, "max_items": 3},
                "item_schema": {
                    "fields": [{"key": "name", "type": "text", "required": True}]
                },
            }]
        }
        # Valid
        issues = SchemaValidator.validate_content(
            schema=schema,
            content={"items": [{"name": "Alice"}]},
            strict=True,
        )
        assert len(issues) == 0

        # Missing required sub-field
        issues = SchemaValidator.validate_content(
            schema=schema,
            content={"items": [{"name": ""}]},
            strict=True,
        )
        assert len(issues) > 0

    def test_validate_schema_structure_rejects_nested_repeaters(self):
        schema = {
            "fields": [{
                "key": "parent", "type": "repeater",
                "item_schema": {
                    "fields": [{"key": "child", "type": "repeater", "item_schema": {"fields": []}}]
                },
            }]
        }
        with pytest.raises(ValidationError):
            SchemaValidator.validate_schema_structure(schema=schema)


# test_policies.py

@pytest.mark.django_db
class TestCMSPolicy:
    def test_required_page_cannot_be_deleted(self, page):
        page.is_required = True
        page.save()
        with pytest.raises(BusinessRuleViolation):
            CMSPolicy.can_delete_page(page=page)

    def test_required_placement_cannot_be_hidden(self, block_placement):
        block_placement.is_required = True
        block_placement.save()
        with pytest.raises(BusinessRuleViolation):
            CMSPolicy.can_hide_block_placement(placement=block_placement)
```

### 15.5 Coverage Requirements

Following the project's 80% coverage threshold:

| Category | Focus Areas |
|----------|------------|
| **Models** | Constraint validation (unique slugs, unique order), `__str__`, properties |
| **Selectors** | `get_by_slug`/`get_by_id`, list queries, depth control (`get_with_full_tree`), not-found |
| **Services** | Authorization (denied + granted), publish flow (success + validation failure), rollback, media tombstone vs delete, API key lifecycle |
| **Policies** | `is_required` enforcement on pages, section placements, block placements |
| **Validators** | Each field type, permissive vs strict mode, repeater validation, nested field paths in errors |
| **Views** | Request/response contracts, status codes, depth parameter, public vs admin API separation |
| **Middleware** | API key validation, origin checking, missing header, expired key |

---

## 16. Implementation Phases

### Phase 1: Foundation (Models + Migrations)
1. Create `apps/cms/` app structure
2. Add CMS enums to `apps/cms/constants.py`
3. Add audit actions to `apps/core/observability/audit/models.py`
4. Add permissions to `apps/rbac/permissions/registry.py`
5. Create all 11 models in `apps/cms/models.py`
6. Create managers in `apps/cms/managers.py`
7. Run `makemigrations cms` and `migrate`
8. Create data migration to seed RBAC permissions

### Phase 2: Core Logic (Selectors + Services + Validators)
1. Implement `SchemaValidator` in `apps/cms/validators.py`
2. Implement all 7 selectors in `apps/cms/selectors.py`
3. Implement `CMSTemplateService` (create templates, reorder placements)
4. Implement `CMSPageService` (create, publish, unpublish)
5. Implement `CMSContentService` (update draft, rollback, toggle visibility)
6. Implement `CMSMediaService` (upload, delete, tombstone)
7. Implement `CMSApiKeyService` (create, revoke, validate)
8. Implement `CMSPolicy`

### Phase 3: API Layer (Views + Serializers + URLs)
1. Create all serializers (input + output)
2. Create admin API views (sites, pages, templates, placements, media, API keys)
3. Create public API views (sites, pages, media URLs)
4. Create URL configuration (admin + public prefixes)
5. Create `CMSApiKeyMiddleware`
6. Register middleware in settings
7. OpenAPI documentation with `@extend_schema()`

### Phase 4: Django Admin
1. Create admin classes for all models
2. Add inlines (section placements on pages, block placements on sections)
3. Add custom actions (publish, archive)
4. Fieldsets and readonly fields

### Phase 5: Background Tasks
1. Implement `cleanup_tombstoned_media` Celery task
2. Implement `prune_content_versions` Celery task
3. Add tasks to `CELERY_BEAT_SCHEDULE`

### Phase 6: Testing
1. Create factories for all 11 models
2. Create conftest with RBAC-initialized fixtures
3. Write model tests (constraints, properties)
4. Write selector tests (queries, depth, not-found)
5. Write service tests (publish flow, rollback, media lifecycle)
6. Write validator tests (all field types, permissive vs strict)
7. Write policy tests (is_required enforcement)
8. Write view tests (admin + public API)
9. Write middleware tests (API key validation)
10. Verify 80%+ coverage

---

## 17. Verification Checklist

After implementation, verify:

- [ ] All 11 models created with correct inheritance and constraints
- [ ] All 28 audit actions registered and logged
- [ ] All 23 RBAC permissions seeded
- [ ] Publish flow: atomic, validated, creates content versions
- [ ] Unpublish: reverts status, does NOT clear published_content
- [ ] Rollback: restores draft_content, does NOT update published_content
- [ ] Schema validation: permissive on draft, strict on publish
- [ ] Rich text sanitized on every save
- [ ] Media tombstoning when published refs exist
- [ ] API key: hashed at rest, plaintext returned once on creation
- [ ] Origin validation on public API requests
- [ ] Content version throttling (30s window)
- [ ] Content version retention (max 50)
- [ ] Reorder methods work atomically for pages, sections, blocks
- [ ] `is_required` enforcement: cannot hide or delete required items
- [ ] `_resolve_actor()` pattern matches rbac/services.py and transaction/services.py
- [ ] `owner_type`/`owner_id` pattern matches FormTemplate
- [ ] All service methods: `@staticmethod`, `@transaction.atomic`, keyword-only args
- [ ] All selectors: `@staticmethod`, keyword-only args, raise `NotFound`
- [ ] Public API returns only `published_content`, never `draft_content`
- [ ] Tests pass with 80%+ coverage

---

## Appendix: Migration Notes

### A.1 Migration Order

1. Add CMS enums to `apps/cms/constants.py` (no migration needed — Python-only)
2. Add audit actions to `apps/core/observability/audit/models.py` (requires migration)
3. Add permissions to `apps/rbac/permissions/registry.py` (requires data migration)
4. Create `apps/cms` app with all models
5. Run `python manage.py makemigrations cms`
6. Run `python manage.py migrate`
7. Create data migration to seed CMS permissions into RBAC

### A.2 Foreign Key Considerations

| FK | On Delete | Rationale |
|----|-----------|-----------|
| `Page.site` | CASCADE | Delete pages when site is deleted |
| `PageSectionPlacement.page` | CASCADE | Delete placements when page is deleted |
| `PageSectionPlacement.template` | PROTECT | Cannot delete template with active placements |
| `SectionBlockPlacement.section_placement` | CASCADE | Delete blocks when section is removed |
| `SectionBlockPlacement.template` | PROTECT | Cannot delete template with active placements |
| `ContentVersion.block_placement` | CASCADE | Delete versions when placement is deleted |
| `ContentVersion.created_by` | PROTECT | Preserve audit trail |
| `MediaFile.folder` | SET_NULL | File moves to root if folder deleted |
| `MediaFolder.parent` | CASCADE | Delete children when parent deleted |
| `MediaUsage.media_file` | CASCADE | Clean up usages when file deleted |
| `MediaUsage.block_placement` | CASCADE | Clean up usages when placement deleted |
| `CMSApiKey.site` | CASCADE | Delete keys when site deleted |
| `Site.homepage` | SET_NULL | Clear homepage ref if page deleted |

### A.3 Settings Configuration

```python
# Add to INSTALLED_APPS
INSTALLED_APPS = [
    ...
    "apps.cms",
]

# Add middleware (before or after authentication middleware)
MIDDLEWARE = [
    ...
    "apps.cms.middleware.CMSApiKeyMiddleware",
]

# Celery beat schedule
CELERY_BEAT_SCHEDULE = {
    ...
    "cms-cleanup-tombstoned-media": {
        "task": "cms.cleanup_tombstoned_media",
        "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
    },
    "cms-prune-content-versions": {
        "task": "cms.prune_content_versions",
        "schedule": crontab(hour=4, minute=0, day_of_week=0),  # Weekly Sunday 4 AM
    },
}
```

---

### Critical Files for Implementation

- `backend/apps/core/constants.py` — Reference for `OwnerType` enum
- `backend/apps/core/models/base.py` — Reference for UUIDModel, AuditModel, TimeStampedModel, UserStampedModel patterns
- `backend/apps/core/types.py` — Reference for ActorContext
- `backend/apps/core/exceptions.py` — NotFound, ValidationError, PermissionDenied, ConflictError, BusinessRuleViolation
- `backend/apps/core/observability/` — AuditService, AuditLog, get_logger, metrics
- `backend/apps/rbac/services.py` — RBACService.build_actor_context(), `_resolve_actor()` pattern (line 44)
- `backend/apps/rbac/policies.py` — MembershipPolicy.authorize_action()
- `backend/apps/rbac/views.py` — PlatformContextMixin
- `backend/apps/rbac/permissions/registry.py` — Permission registration format
- `backend/apps/forms/models.py` — Reference for `owner_type`/`owner_id` pattern
- `backend/apps/forms/managers.py` — Reference for SoftDeleteManager + custom QuerySet pattern

---

*End of Implementation Plan*
