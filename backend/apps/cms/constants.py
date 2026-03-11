# apps/cms/constants.py
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
