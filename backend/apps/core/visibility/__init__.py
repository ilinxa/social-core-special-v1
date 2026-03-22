# apps/core/visibility/__init__.py
"""
Content Visibility System — 3-Tier Profile Privacy.

Provides field-level visibility control for profile data:
- T1 (ALWAYS_PUBLIC): System-enforced, always visible.
- T2 (CONDITIONAL): Owner-configurable per field with relationship-based levels.
- T3 (ALWAYS_PRIVATE): Members-only, further gated by RBAC permissions.

Usage:
    from apps.core.visibility import (
        ContentTier, BusinessVisibility, UserVisibility, PlatformVisibility,
        FieldVisibilityConfig, get_registry, get_t2_fields, get_visibility_choices,
        ViewerAccess, VisibilityResolver,
        VisibilityAwareSerializerMixin, VisibilityOverrideInput,
    )
"""

from apps.core.visibility.enums import (
    BusinessVisibility,
    ContentTier,
    PlatformVisibility,
    UserVisibility,
)
from apps.core.visibility.registry import (
    FieldVisibilityConfig,
    get_registry,
    get_t2_fields,
    get_visibility_choices,
)
from apps.core.visibility.resolver import ViewerAccess, VisibilityResolver
from apps.core.visibility.serializers import (
    VisibilityAwareSerializerMixin,
    VisibilityOverrideInput,
)

__all__ = [
    "ContentTier",
    "BusinessVisibility",
    "PlatformVisibility",
    "UserVisibility",
    "FieldVisibilityConfig",
    "get_registry",
    "get_t2_fields",
    "get_visibility_choices",
    "ViewerAccess",
    "VisibilityResolver",
    "VisibilityAwareSerializerMixin",
    "VisibilityOverrideInput",
]
