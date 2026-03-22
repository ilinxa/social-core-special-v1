"""
Network Models
==============
Follow (one-way: User → Business/Platform) and
Connection (two-way: User ↔ User, Account ↔ Account).

Both use explicit status fields for lifecycle management rather than
soft delete — status transitions are the domain-specific way to manage
these records.
"""

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel, UUIDModel

# =============================================================================
# ENUMS
# =============================================================================


class FolloweeType(models.TextChoices):
    BUSINESS = "business", "Business"
    PLATFORM = "platform", "Platform"


class FollowStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    REMOVED = "removed", "Removed"


class ConnectionType(models.TextChoices):
    USER_USER = "user_user", "User ↔ User"
    ACCOUNT_ACCOUNT = "account_account", "Account ↔ Account"


class ConnectionStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    DISCONNECTED = "disconnected", "Disconnected"


# =============================================================================
# FOLLOW MODEL
# =============================================================================


class Follow(UUIDModel, TimeStampedModel):
    """
    One-way follow: User → Business or Platform.

    Users can follow businesses or the platform. Public businesses
    auto-approve follows; private businesses require account authority
    approval via the transaction system.
    """

    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="follows",
    )
    followee_type = models.CharField(
        max_length=20,
        choices=FolloweeType.choices,
        db_index=True,
    )
    followee_id = models.UUIDField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=FollowStatus.choices,
        default=FollowStatus.ACTIVE,
        db_index=True,
    )
    removed_at = models.DateTimeField(null=True, blank=True)
    removed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="removed_follows",
    )

    class Meta:
        db_table = "network_follow"
        verbose_name = "follow"
        verbose_name_plural = "follows"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["follower", "followee_type", "followee_id"],
                condition=models.Q(status="active"),
                name="unique_active_follow",
            ),
        ]
        indexes = [
            models.Index(
                fields=["follower", "followee_type", "followee_id"],
            ),
            models.Index(
                fields=["followee_type", "followee_id", "status"],
            ),
            models.Index(
                fields=["follower", "status"],
            ),
        ]

    def __str__(self):
        return f"{self.follower_id} → {self.followee_type}:{self.followee_id} ({self.status})"


# =============================================================================
# CONNECTION MODEL
# =============================================================================


class Connection(UUIDModel, TimeStampedModel):
    """
    Bidirectional connection: User ↔ User or Account ↔ Account.

    User-User connections are like LinkedIn connections — always require
    acceptance. Account-Account connections represent business partnerships
    and require account authority approval.

    Canonical ordering:
      - User connections: str(user_a.id) < str(user_b.id)
      - Account connections: (a_type, str(a_id)) < (b_type, str(b_id))
    Enforced in the service layer, not at DB level.
    """

    connection_type = models.CharField(
        max_length=20,
        choices=ConnectionType.choices,
        db_index=True,
    )

    # User-User fields (null for account connections)
    user_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="connections_as_a",
    )
    user_b = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="connections_as_b",
    )

    # Account-Account fields (null for user connections)
    account_a_type = models.CharField(max_length=20, blank=True, default="")
    account_a_id = models.UUIDField(null=True, blank=True)
    account_b_type = models.CharField(max_length=20, blank=True, default="")
    account_b_id = models.UUIDField(null=True, blank=True)

    # Shared fields
    status = models.CharField(
        max_length=20,
        choices=ConnectionStatus.choices,
        default=ConnectionStatus.ACTIVE,
        db_index=True,
    )
    note = models.TextField(blank=True, default="")
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="initiated_connections",
    )
    connected_at = models.DateTimeField(null=True, blank=True)
    disconnected_at = models.DateTimeField(null=True, blank=True)
    disconnected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="disconnected_connections",
    )

    class Meta:
        db_table = "network_connection"
        verbose_name = "connection"
        verbose_name_plural = "connections"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user_a", "user_b"],
                condition=models.Q(
                    status="active",
                    connection_type="user_user",
                ),
                name="unique_active_user_connection",
            ),
            models.UniqueConstraint(
                fields=[
                    "account_a_type",
                    "account_a_id",
                    "account_b_type",
                    "account_b_id",
                ],
                condition=models.Q(
                    status="active",
                    connection_type="account_account",
                ),
                name="unique_active_account_connection",
            ),
            models.CheckConstraint(
                check=(
                    ~models.Q(connection_type="user_user")
                    | (models.Q(user_a__isnull=False) & models.Q(user_b__isnull=False))
                ),
                name="user_connection_requires_users",
            ),
            models.CheckConstraint(
                check=(
                    ~models.Q(connection_type="account_account")
                    | (
                        models.Q(account_a_id__isnull=False)
                        & models.Q(account_b_id__isnull=False)
                    )
                ),
                name="account_connection_requires_accounts",
            ),
        ]
        indexes = [
            models.Index(fields=["user_a", "user_b", "status"]),
            models.Index(fields=["account_a_type", "account_a_id", "status"]),
            models.Index(fields=["account_b_type", "account_b_id", "status"]),
        ]

    def __str__(self):
        if self.connection_type == ConnectionType.USER_USER:
            return f"{self.user_a_id} ↔ {self.user_b_id} ({self.status})"
        return (
            f"{self.account_a_type}:{self.account_a_id} ↔ "
            f"{self.account_b_type}:{self.account_b_id} ({self.status})"
        )
