# backend/apps/core/constants.py
"""
Shared Enums and Constants
==========================
Central location for all shared enums used across the multi-tenant platform.

These enums are used by:
- Organization System (accounts, verification)
- RBAC System (permissions, memberships)
- Transaction System (context types)
- Form Builder System (scopes, owner types)
"""

from django.db import models


class AccountType(models.TextChoices):
    """Types of accounts in the system."""

    PLATFORM = "platform", "Platform"
    BUSINESS = "business", "Business"


class ContextType(models.TextChoices):
    """Context types for Transaction system integration."""

    PLATFORM = "platform", "Platform"
    BUSINESS = "business", "Business"
    USER = "user", "User"


class OwnerType(models.TextChoices):
    """Owner types for Form Builder integration."""

    SYSTEM = "system", "System"
    PLATFORM = "platform", "Platform"
    BUSINESS = "business", "Business"


class FormScope(models.TextChoices):
    """Scope for forms."""

    PLATFORM = "platform", "Platform"
    BUSINESS = "business", "Business"


class PermissionScope(models.TextChoices):
    """Permission scope for RBAC integration."""

    BUSINESS = "business", "Business Only"
    PLATFORM_ONLY = "platform_only", "Platform Only"
    GLOBAL_ONLY = "global_only", "Global Only"
    PLATFORM_AND_GLOBAL = "platform_and_global", "Platform and Global"


class MembershipStatus(models.TextChoices):
    """Membership status for RBAC integration."""

    ACTIVE = "active", "Active"
    PENDING_APPROVAL = "pending_approval", "Pending Approval"
    SUSPENDED = "suspended", "Suspended"
    LEFT = "left", "Left"
    REMOVED = "removed", "Removed"
    BANNED = "banned", "Banned"


# Business-specific enums
class BusinessType(models.TextChoices):
    """Types of business entities."""

    SOLE_PROPRIETORSHIP = "sole_proprietorship", "Sole Proprietorship"
    PARTNERSHIP = "partnership", "Partnership"
    LLC = "llc", "LLC"
    CORPORATION = "corporation", "Corporation"
    NONPROFIT = "nonprofit", "Nonprofit"
    COOPERATIVE = "cooperative", "Cooperative"
    OTHER = "other", "Other"


class BusinessStatus(models.TextChoices):
    """Business account status."""

    PENDING = "pending", "Pending"
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    ARCHIVED = "archived", "Archived"
    DELETED = "deleted", "Deleted"


class VerificationStatus(models.TextChoices):
    """Business verification status."""

    UNVERIFIED = "unverified", "Unverified"
    PENDING = "pending", "Pending"
    VERIFIED = "verified", "Verified"
    REJECTED = "rejected", "Rejected"
    EXPIRED = "expired", "Expired"


class CompanySize(models.TextChoices):
    """Company size ranges."""

    SIZE_1 = "1", "1 employee"
    SIZE_2_10 = "2-10", "2-10 employees"
    SIZE_11_50 = "11-50", "11-50 employees"
    SIZE_51_200 = "51-200", "51-200 employees"
    SIZE_201_500 = "201-500", "201-500 employees"
    SIZE_500_PLUS = "500+", "500+ employees"


# =============================================================================
# FORM BUILDER ENUMS
# =============================================================================

class FormStatus(models.TextChoices):
    """Form template lifecycle states."""

    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"
    DELETED = "deleted", "Deleted"


class ResponseStatus(models.TextChoices):
    """Form response lifecycle states."""

    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    PROCESSED = "processed", "Processed"
    VOID = "void", "Void"
    EXPIRED = "expired", "Expired"


class FieldType(models.TextChoices):
    """Form field types."""

    # Text types
    TEXT = "text", "Text"
    TEXTAREA = "textarea", "Text Area"
    EMAIL = "email", "Email"
    URL = "url", "URL"
    PHONE = "phone", "Phone"

    # Numeric types
    INTEGER = "integer", "Integer"
    DECIMAL = "decimal", "Decimal"
    CURRENCY = "currency", "Currency"
    RATING = "rating", "Rating"

    # Boolean
    BOOLEAN = "boolean", "Boolean"
    CHECKBOX = "checkbox", "Checkbox"

    # Date/Time
    DATE = "date", "Date"
    DATETIME = "datetime", "Date & Time"
    TIME = "time", "Time"

    # Selection
    SELECT = "select", "Select"
    RADIO = "radio", "Radio"
    MULTISELECT = "multiselect", "Multi-Select"
    CHECKBOX_GROUP = "checkbox_group", "Checkbox Group"

    # File types
    FILE = "file", "File"
    IMAGE = "image", "Image"

    # Complex types
    LOCATION = "location", "Location"
    REPEATABLE = "repeatable", "Repeatable Group"


class StorageType(models.TextChoices):
    """Internal storage type for field values."""

    TEXT = "text", "Text"
    INTEGER = "integer", "Integer"
    DECIMAL = "decimal", "Decimal"
    BOOLEAN = "boolean", "Boolean"
    DATE = "date", "Date"
    DATETIME = "datetime", "DateTime"
    JSON = "json", "JSON"
