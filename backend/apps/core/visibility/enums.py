# apps/core/visibility/enums.py
"""
Visibility enums for the 3-tier content visibility system.

ContentTier classifies fields. Visibility enums define relationship-based
access levels per account type (higher value = broader audience).
"""

from django.db import models


class ContentTier(models.TextChoices):
    """Classification tier for a field's visibility behaviour."""

    ALWAYS_PUBLIC = "T1", "Always Public"
    CONDITIONAL = "T2", "Conditional"
    ALWAYS_PRIVATE = "T3", "Always Private"


class UserVisibility(models.IntegerChoices):
    """Visibility levels for User profile T2 fields."""

    CONNECTIONS = 0, "Connections"
    WORLD = 1, "All authenticated users"


class BusinessVisibility(models.IntegerChoices):
    """Visibility levels for Business T2 fields."""

    MEMBERS = 0, "Members"
    CONNECTIONS = 1, "Connected accounts"
    FOLLOWERS = 2, "Followers"
    WORLD = 3, "World (everyone)"


class PlatformVisibility(models.IntegerChoices):
    """Visibility levels for Platform T2 fields."""

    MEMBERS = 0, "Platform members"
    WORLD = 1, "World (everyone)"


# Mapping from account_type string to its visibility enum class
VISIBILITY_ENUMS = {
    "user": UserVisibility,
    "business": BusinessVisibility,
    "platform": PlatformVisibility,
}
