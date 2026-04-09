# apps/cms/constants.py
"""
CMS-specific constants and enums.

Note: CMS field types are SEPARATE from Form Builder's FieldType enum
because the two systems have different field needs.
"""

from django.db import models


class TemplateOrgType(models.TextChoices):
    """Which organization types can activate and use a template."""

    SYSTEM = "system", "System"  # Internal only, not activatable
    PLATFORM = "platform", "Platform"  # Platform orgs only
    BUSINESS = "business", "Business"  # Business orgs only
    ALL = "all", "All"  # Both platform and business


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
CMS_FIELD_TYPES = frozenset(
    [
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
    ]
)

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

# File upload security — allowed MIME types and extensions
ALLOWED_MEDIA_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/svg+xml",
        "application/pdf",
        "video/mp4",
        "video/webm",
        "audio/mpeg",
        "audio/ogg",
    }
)

# Template eligibility: given an org's OwnerType, which TemplateOrgTypes are visible?
# Uses string values (matching OwnerType.PLATFORM/BUSINESS) as keys for dict lookup.
TEMPLATE_ELIGIBILITY = {
    "platform": frozenset({TemplateOrgType.PLATFORM, TemplateOrgType.ALL}),
    "business": frozenset({TemplateOrgType.BUSINESS, TemplateOrgType.ALL}),
}


ALLOWED_MEDIA_EXTENSIONS = frozenset(
    {
        "jpg",
        "jpeg",
        "png",
        "gif",
        "webp",
        "svg",
        "pdf",
        "mp4",
        "webm",
        "mp3",
        "ogg",
    }
)
