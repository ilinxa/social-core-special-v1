# apps/organization/platform/models.py
"""
Platform Models - Singleton platform account and profile.

The platform account is a singleton enforced by a unique constraint on singleton_key=1.
This prevents race conditions and accidental duplicates under concurrency.
"""

import uuid

from django.db import models

from apps.core.models import AuditModel


class PlatformAccount(AuditModel):
    """
    Singleton model for platform governance.

    INVARIANT: Only one instance can exist - enforced by DB unique constraint on singleton_key.
    This prevents race conditions and accidental duplicates under concurrency.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # DB-level singleton enforcement - unique constraint guarantees only one row
    singleton_key = models.PositiveSmallIntegerField(
        default=1,
        unique=True,
        editable=False,
        help_text="Singleton enforcement - always 1",
    )

    is_configured = models.BooleanField(
        default=False, help_text="Whether initial setup is complete"
    )
    max_members = models.PositiveSmallIntegerField(
        default=5,
        help_text="Maximum number of members allowed. 0 = unlimited.",
    )
    open_member_request = models.BooleanField(
        default=False,
        help_text="Whether users can send membership requests to the platform.",
    )
    settings = models.JSONField(
        default=dict, blank=True, help_text="Platform-wide settings"
    )

    class Meta:
        db_table = "platform_account"
        verbose_name = "Platform Account"
        verbose_name_plural = "Platform Accounts"
        constraints = [
            models.CheckConstraint(
                check=models.Q(singleton_key=1), name="platform_account_singleton"
            )
        ]

    def __str__(self):
        return f"Platform Account ({self.id})"

    def save(self, *args, **kwargs):
        self.singleton_key = 1  # Always enforce
        super().save(*args, **kwargs)


class PlatformProfile(models.Model):
    """Platform branding and public-facing information."""

    platform = models.OneToOneField(
        PlatformAccount,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="profile",
    )
    name = models.CharField(max_length=255, help_text="Platform name")
    tagline = models.CharField(max_length=500, blank=True, default="")
    description = models.TextField(blank=True, default="")
    logo = models.ImageField(upload_to="platform/logo/", blank=True, null=True)
    favicon = models.ImageField(upload_to="platform/favicon/", blank=True, null=True)
    primary_color = models.CharField(max_length=7, default="#000000")
    secondary_color = models.CharField(max_length=7, default="#ffffff")
    contact_email = models.EmailField(blank=True, default="")
    contact_phone = models.CharField(max_length=20, blank=True, default="")
    address = models.TextField(blank=True, default="")
    social_links = models.JSONField(default=dict, blank=True)
    visibility_overrides = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-field visibility level overrides for T2 fields.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "platform_profile"
        verbose_name = "Platform Profile"
        verbose_name_plural = "Platform Profiles"

    def __str__(self):
        return f"Platform Profile: {self.name}"
