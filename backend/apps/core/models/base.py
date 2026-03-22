"""
Core Base Models
================
Abstract base models providing common functionality across all apps.

These models are designed to be inherited, not instantiated directly.
Each model adds specific fields and behaviors that can be composed together.

Usage:
    from apps.core.models import TimeStampedModel, SoftDeleteModel

    class Product(TimeStampedModel, SoftDeleteModel):
        name = models.CharField(max_length=255)

Available Models:
    - TimeStampedModel: Adds created_at, updated_at
    - SoftDeleteModel: Adds soft delete capability with manager
    - UserStampedModel: Adds created_by, updated_by (extends TimeStamped)
    - UUIDModel: Uses UUID as primary key instead of auto-increment
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

# =============================================================================
# TIMESTAMPED MODEL
# =============================================================================


class TimeStampedModel(models.Model):
    """
    Abstract model with automatic timestamp tracking.

    Fields:
        created_at: Set once when record is created (indexed for sorting)
        updated_at: Updated automatically on every save

    Note:
        - created_at uses auto_now_add (set only on creation)
        - updated_at uses auto_now (updated on every save)
        - Both are non-editable to maintain data integrity
    """

    created_at = models.DateTimeField(
        auto_now_add=True, db_index=True, help_text="Timestamp when record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Timestamp when record was last updated"
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]  # Most recent first by default


# =============================================================================
# SOFT DELETE MODEL
# =============================================================================


class SoftDeleteManager(models.Manager):
    """
    Manager that excludes soft-deleted records by default.

    This manager is attached as `objects` to SoftDeleteModel, ensuring
    that normal queries automatically exclude deleted records.

    Use `all_objects` manager to include deleted records when needed.
    """

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class SoftDeleteModel(models.Model):
    """
    Abstract model with soft delete support.

    Instead of permanently deleting records, this model marks them
    as deleted while preserving the data for audit trails and recovery.

    Fields:
        is_deleted: Boolean flag indicating soft-deleted state
        deleted_at: Timestamp when record was soft-deleted
        deleted_by: Reference to user who performed the deletion

    Managers:
        objects: Returns only non-deleted records (default)
        all_objects: Returns all records including deleted ones

    Methods:
        soft_delete(user=None): Mark as deleted with optional user
        restore(): Restore a soft-deleted record

    Usage:
        # Normal queries exclude deleted
        Product.objects.all()  # Only active products

        # Include deleted records
        Product.all_objects.all()  # All products

        # Soft delete
        product.soft_delete(user=request.user)

        # Restore
        product.restore()
    """

    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Flag indicating if record is soft-deleted",
    )
    deleted_at = models.DateTimeField(
        null=True, blank=True, help_text="Timestamp when record was soft-deleted"
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_deleted",
        help_text="User who soft-deleted this record",
    )

    # Custom managers
    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def soft_delete(self, user=None):
        """
        Mark this record as soft-deleted.

        Args:
            user: Optional user performing the deletion (for audit trail)
        """
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

    def restore(self):
        """
        Restore a soft-deleted record to active state.

        Clears all deletion-related fields.
        """
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])


# =============================================================================
# USER STAMPED MODEL
# =============================================================================


class UserStampedModel(TimeStampedModel):
    """
    Abstract model tracking which user created/modified records.

    Extends TimeStampedModel to add user attribution. Useful for audit
    trails and ownership tracking.

    Fields:
        created_at: (inherited) Timestamp of creation
        updated_at: (inherited) Timestamp of last update
        created_by: User who created the record
        updated_by: User who last updated the record

    Note:
        - created_by should be set once at creation
        - updated_by should be updated on each modification
        - Both allow null for system-generated records
    """

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_created",
        help_text="User who created this record",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_updated",
        help_text="User who last updated this record",
    )

    class Meta:
        abstract = True


# =============================================================================
# UUID MODEL
# =============================================================================


class UUIDModel(models.Model):
    """
    Abstract model using UUID as primary key.

    Use this instead of auto-incrementing integers when:
    - IDs will be exposed in URLs (prevents enumeration attacks)
    - Records may be created across distributed systems
    - You need globally unique identifiers

    Fields:
        id: UUID primary key (auto-generated, non-editable)

    Trade-offs:
        + Secure (non-guessable)
        + Globally unique
        - Larger storage (16 bytes vs 8 bytes for BigInt)
        - Slightly slower indexing
        - Less human-readable

    Usage:
        class Order(UUIDModel, TimeStampedModel):
            total = models.DecimalField(...)

        # Access
        order.id  # UUID object
        str(order.id)  # "550e8400-e29b-41d4-a716-446655440000"
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier (UUID v4)",
    )

    class Meta:
        abstract = True


# =============================================================================
# COMBINED BASE MODELS (Common Patterns)
# =============================================================================


class BaseModel(TimeStampedModel, SoftDeleteModel):
    """
    Standard base model combining timestamps and soft delete.

    This is the recommended base for most domain models that need:
    - Creation/update timestamps
    - Soft delete capability

    Usage:
        class Product(BaseModel):
            name = models.CharField(max_length=255)
    """

    class Meta:
        abstract = True


class AuditModel(UserStampedModel, SoftDeleteModel):
    """
    Full audit trail model with user tracking and soft delete.

    Use this for models requiring complete audit trails:
    - Who created/modified the record
    - When it was created/modified
    - Soft delete with user attribution

    Usage:
        class Contract(AuditModel):
            title = models.CharField(max_length=255)
    """

    class Meta:
        abstract = True
