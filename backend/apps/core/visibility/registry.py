# apps/core/visibility/registry.py
"""
Field visibility registries — maps field names to their tier + config.

Each registry is keyed by a `registry_key` string (NOT account_type) because
a single account type may have multiple serializers (e.g., BusinessAccountOutput
and BusinessProfileOutput) each needing their own field registry.

Fields NOT in the registry are passed through unchanged (default-include).
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from apps.core.visibility.enums import (
    BusinessVisibility,
    ContentTier,
    PlatformVisibility,
    UserVisibility,
    VISIBILITY_ENUMS,
)

T1 = ContentTier.ALWAYS_PUBLIC
T2 = ContentTier.CONDITIONAL
T3 = ContentTier.ALWAYS_PRIVATE


@dataclass(frozen=True)
class FieldVisibilityConfig:
    """Configuration for a single field's visibility behaviour."""

    tier: str  # ContentTier value ("T1", "T2", "T3")
    default_level: Optional[int] = None  # Only for T2 — default visibility level
    required_permission: Optional[str] = None  # Only for T3 — RBAC gate within members


# =============================================================================
# USER PROFILE FIELDS
# =============================================================================

USER_PROFILE_FIELDS: Dict[str, FieldVisibilityConfig] = {
    # T1 — always visible
    "first_name": FieldVisibilityConfig(tier=T1),
    "last_name": FieldVisibilityConfig(tier=T1),
    "full_name": FieldVisibilityConfig(tier=T1),
    "display_name": FieldVisibilityConfig(tier=T1),
    "avatar_url": FieldVisibilityConfig(tier=T1),
    "has_avatar": FieldVisibilityConfig(tier=T1),
    "cover_image_url": FieldVisibilityConfig(tier=T1),
    "has_cover_image": FieldVisibilityConfig(tier=T1),
    "bio": FieldVisibilityConfig(tier=T1),
    "country": FieldVisibilityConfig(tier=T1),
    "city": FieldVisibilityConfig(tier=T1),
    "tags": FieldVisibilityConfig(tier=T1),
    "is_public": FieldVisibilityConfig(tier=T1),
    # T3 — members-only (for user, means "self only" since users don't have members)
    "phone": FieldVisibilityConfig(tier=T3),
    "timezone": FieldVisibilityConfig(tier=T3),
    "language": FieldVisibilityConfig(tier=T3),
}


# =============================================================================
# BUSINESS ACCOUNT FIELDS
# =============================================================================

BUSINESS_ACCOUNT_FIELDS: Dict[str, FieldVisibilityConfig] = {
    # T1 — always visible
    "id": FieldVisibilityConfig(tier=T1),
    "slug": FieldVisibilityConfig(tier=T1),
    "legal_name": FieldVisibilityConfig(tier=T1),
    "country": FieldVisibilityConfig(tier=T1),
    "city": FieldVisibilityConfig(tier=T1),
    "business_type": FieldVisibilityConfig(tier=T1),
    "business_type_display": FieldVisibilityConfig(tier=T1),
    "status": FieldVisibilityConfig(tier=T1),
    "status_display": FieldVisibilityConfig(tier=T1),
    "verification_status": FieldVisibilityConfig(tier=T1),
    "verification_status_display": FieldVisibilityConfig(tier=T1),
    "verified_at": FieldVisibilityConfig(tier=T1),
    "is_platform_branch": FieldVisibilityConfig(tier=T1),
    "open_member_request": FieldVisibilityConfig(tier=T1),
    "created_at": FieldVisibilityConfig(tier=T1),
    "updated_at": FieldVisibilityConfig(tier=T1),
    # T3 — members-only with RBAC gate
    "registration_number": FieldVisibilityConfig(
        tier=T3, required_permission="can_view_legal_info"
    ),
    "tax_id": FieldVisibilityConfig(
        tier=T3, required_permission="can_view_legal_info"
    ),
    "legal_address": FieldVisibilityConfig(
        tier=T3, required_permission="can_view_legal_info"
    ),
    "settings": FieldVisibilityConfig(
        tier=T3, required_permission="can_edit_business"
    ),
    "max_members": FieldVisibilityConfig(
        tier=T3, required_permission="can_view_members"
    ),
}


# =============================================================================
# BUSINESS PROFILE FIELDS
# =============================================================================

BUSINESS_PROFILE_FIELDS: Dict[str, FieldVisibilityConfig] = {
    # T1 — always visible
    "display_name": FieldVisibilityConfig(tier=T1),
    "tagline": FieldVisibilityConfig(tier=T1),
    "description": FieldVisibilityConfig(tier=T1),
    "logo": FieldVisibilityConfig(tier=T1),
    "cover_image": FieldVisibilityConfig(tier=T1),
    "website": FieldVisibilityConfig(tier=T1),
    "industry": FieldVisibilityConfig(tier=T1),
    "company_size": FieldVisibilityConfig(tier=T1),
    "founded_year": FieldVisibilityConfig(tier=T1),
    "social_links": FieldVisibilityConfig(tier=T1),
    "tags": FieldVisibilityConfig(tier=T1),
    "is_public": FieldVisibilityConfig(tier=T1),
    "created_at": FieldVisibilityConfig(tier=T1),
    "updated_at": FieldVisibilityConfig(tier=T1),
    # T2 — configurable visibility
    "contact_email": FieldVisibilityConfig(
        tier=T2, default_level=BusinessVisibility.FOLLOWERS
    ),
    "contact_phone": FieldVisibilityConfig(
        tier=T2, default_level=BusinessVisibility.FOLLOWERS
    ),
}


# =============================================================================
# PLATFORM PROFILE FIELDS (all T1 currently)
# =============================================================================

PLATFORM_PROFILE_FIELDS: Dict[str, FieldVisibilityConfig] = {
    # Platform is fully public — no T2 or T3 fields
}


# =============================================================================
# Registry lookup
# =============================================================================

_REGISTRIES: Dict[str, Dict[str, FieldVisibilityConfig]] = {
    "user_profile": USER_PROFILE_FIELDS,
    "business_account": BUSINESS_ACCOUNT_FIELDS,
    "business_profile": BUSINESS_PROFILE_FIELDS,
    "platform_profile": PLATFORM_PROFILE_FIELDS,
}

# Maps registry_key to account_type for enum resolution
_REGISTRY_TO_ACCOUNT_TYPE: Dict[str, str] = {
    "user_profile": "user",
    "business_account": "business",
    "business_profile": "business",
    "platform_profile": "platform",
}


def get_registry(registry_key: str) -> Dict[str, FieldVisibilityConfig]:
    """Get the field registry for a given registry key.

    Returns an empty dict for unknown keys (safe default — all fields pass through).
    """
    return _REGISTRIES.get(registry_key, {})


def get_t2_fields(registry_key: str) -> Dict[str, FieldVisibilityConfig]:
    """Get only T2 (CONDITIONAL) fields from a registry."""
    registry = get_registry(registry_key)
    return {
        name: config
        for name, config in registry.items()
        if config.tier == T2
    }


def get_visibility_choices(account_type: str) -> List:
    """Get the visibility enum choices for an account type.

    Returns the IntegerChoices class (e.g., BusinessVisibility).
    """
    enum_class = VISIBILITY_ENUMS.get(account_type)
    if enum_class is None:
        return []
    return list(enum_class)


def get_account_type_for_registry(registry_key: str) -> Optional[str]:
    """Get the account_type string for a registry key."""
    return _REGISTRY_TO_ACCOUNT_TYPE.get(registry_key)
