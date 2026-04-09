# apps/organization/business/models.py
"""
Business Models - Multi-tenant business accounts.

Key invariants:
- BusinessAccount.slug is globally unique
- BusinessSlugHistory.old_slug is globally unique (slugs can NEVER be reused)
- Business owner is tracked via RBAC Membership.is_owner flag, not here
"""

import uuid

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.utils.text import slugify

from apps.core.constants import (
    BusinessStatus,
    BusinessType,
    CompanySize,
    VerificationStatus,
)
from apps.core.models import AuditModel, SoftDeleteManager


class BusinessAccountManager(SoftDeleteManager):
    """
    Manager for BusinessAccount with common query patterns.

    Inherits from SoftDeleteManager to automatically filter is_deleted=False.
    """

    def active(self):
        """Return active (non-deleted, active status) businesses."""
        return self.get_queryset().filter(status=BusinessStatus.ACTIVE)

    def verified(self):
        """Return active verified businesses."""
        return self.active().filter(verification_status=VerificationStatus.VERIFIED)

    def pending_verification(self):
        """Return active businesses with pending verification."""
        return self.active().filter(verification_status=VerificationStatus.PENDING)


class BusinessAccount(AuditModel):
    """
    Multi-tenant business account.

    INVARIANT: slug is globally unique and can never be reused.
    Old slugs are tracked in BusinessSlugHistory for redirects.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)

    # Legal information
    legal_name = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=100, blank=True, default="")
    tax_id = models.CharField(max_length=100, blank=True, default="")
    country = models.CharField(max_length=2, help_text="ISO 3166-1 alpha-2")
    city = models.CharField(
        max_length=100,
        blank=True,
        default="",
        db_index=True,
        help_text="City name (validated against predefined city list).",
    )
    legal_address = models.TextField(blank=True, default="")

    # Classification
    business_type = models.CharField(
        max_length=30, choices=BusinessType.choices, default=BusinessType.OTHER
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=BusinessStatus.choices,
        default=BusinessStatus.PENDING,
        db_index=True,
    )

    # Verification
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.UNVERIFIED,
        db_index=True,
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_businesses",
    )

    # Platform branch flag
    is_platform_branch = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this business is a platform-owned branch.",
    )

    # Membership quota
    max_members = models.PositiveSmallIntegerField(
        default=1,
        help_text="Maximum number of members allowed. 0 = unlimited.",
    )

    # Membership requests
    open_member_request = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether users can send membership requests to this business.",
    )

    # CMS access
    cms_enabled = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this business has CMS access enabled.",
    )

    # Settings
    settings = models.JSONField(default=dict, blank=True)

    objects = BusinessAccountManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "business_account"
        verbose_name = "Business Account"
        verbose_name_plural = "Business Accounts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["status", "is_deleted"]),
            models.Index(fields=["verification_status"]),
            models.Index(fields=["country"]),
        ]

    def __str__(self):
        return f"{self.legal_name} ({self.slug})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.legal_name)
        super().save(*args, **kwargs)


class BusinessProfile(models.Model):
    """Public-facing business profile."""

    business = models.OneToOneField(
        BusinessAccount,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="profile",
    )
    display_name = models.CharField(max_length=255)
    tagline = models.CharField(max_length=500, blank=True, default="")
    description = models.TextField(blank=True, default="")
    logo = models.ImageField(upload_to="business/logos/%Y/%m/", blank=True, null=True)
    cover_image = models.ImageField(
        upload_to="business/covers/%Y/%m/", blank=True, null=True
    )
    website = models.URLField(blank=True, default="")
    contact_email = models.EmailField(blank=True, default="")
    contact_phone = models.CharField(max_length=20, blank=True, default="")
    industry = models.CharField(max_length=100, blank=True, default="")
    company_size = models.CharField(
        max_length=20, choices=CompanySize.choices, blank=True, default=""
    )
    founded_year = models.PositiveIntegerField(null=True, blank=True)
    social_links = models.JSONField(default=dict, blank=True)
    custom_fields = models.JSONField(
        default=dict, blank=True, help_text="Form Builder extensions"
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Business tags for discovery (e.g., saas, fintech).",
    )
    is_public = models.BooleanField(default=True)
    visibility_overrides = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-field visibility level overrides for T2 fields.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "business_profile"
        verbose_name = "Business Profile"
        verbose_name_plural = "Business Profiles"
        indexes = [
            GinIndex(fields=["tags"], name="bizprofile_tags_gin"),
        ]

    def __str__(self):
        return f"Profile: {self.display_name}"


class BusinessSlugHistory(models.Model):
    """
    Tracks slug changes for URL redirects.

    INVARIANT: old_slug is globally unique - old slugs can NEVER be reused.
    This ensures permanent redirects work and prevents slug hijacking.
    """

    id = models.BigAutoField(primary_key=True)
    business = models.ForeignKey(
        BusinessAccount, on_delete=models.CASCADE, related_name="slug_history"
    )
    old_slug = models.SlugField(
        max_length=100, unique=True, db_index=True
    )  # UNIQUE - no reuse ever
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "business_slug_history"
        verbose_name = "Business Slug History"
        verbose_name_plural = "Business Slug Histories"
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.old_slug} -> {self.business.slug}"
