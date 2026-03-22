# apps/core/visibility/resolver.py
"""
VisibilityResolver — computes viewer access and filters serialized data.

- `compute_viewer_access()`: 1-3 DB queries (short-circuits), called once per request.
- `filter_fields()`: Pure logic, 0 DB queries, called per serializer.
"""

from dataclasses import dataclass
from typing import Any, Dict, List
from uuid import UUID

from apps.core.visibility.enums import (
    BusinessVisibility,
    ContentTier,
    PlatformVisibility,
    UserVisibility,
)
from apps.core.visibility.registry import (
    FieldVisibilityConfig,
    get_account_type_for_registry,
    get_registry,
    get_t2_fields,
    get_visibility_choices,
)

T1 = ContentTier.ALWAYS_PUBLIC
T2 = ContentTier.CONDITIONAL
T3 = ContentTier.ALWAYS_PRIVATE


@dataclass(frozen=True)
class ViewerAccess:
    """Computed once per request — captures the viewer's relationship to an account."""

    level: int  # Relationship level (sentinel value, NOT strictly from enum)
    is_authenticated: bool  # Anonymous guard for T2
    is_member: bool  # Member of the account (bypass T2)
    is_owner_or_self: bool  # Owner/self bypass (sees everything)
    permissions: frozenset = frozenset()  # RBAC permission codes for T3

    # Sentinel for anonymous / unrelated viewers
    ANONYMOUS = None  # Constructed via ViewerAccess.for_anonymous()

    @classmethod
    def for_anonymous(cls) -> "ViewerAccess":
        """Create a ViewerAccess for anonymous (unauthenticated) viewers."""
        return cls(
            level=0,
            is_authenticated=False,
            is_member=False,
            is_owner_or_self=False,
            permissions=frozenset(),
        )


class VisibilityResolver:
    """Central resolver for field-level visibility checks."""

    @staticmethod
    def compute_viewer_access(
        *,
        viewer,
        account_type: str,
        account_id: UUID,
    ) -> ViewerAccess:
        """Compute the viewer's access level for a given account.

        Short-circuits: if member found, skips follower/connection checks.

        Args:
            viewer: Django User instance (may be AnonymousUser).
            account_type: "user", "business", or "platform".
            account_id: UUID of the account being viewed.

        Returns:
            ViewerAccess dataclass.
        """
        if not hasattr(viewer, "is_authenticated") or not viewer.is_authenticated:
            return ViewerAccess.for_anonymous()

        if account_type == "user":
            return VisibilityResolver._compute_user_access(viewer, account_id)
        elif account_type == "business":
            return VisibilityResolver._compute_business_access(viewer, account_id)
        elif account_type == "platform":
            return VisibilityResolver._compute_platform_access(viewer, account_id)

        # Unknown account type — treat as authenticated stranger
        return ViewerAccess(
            level=0,
            is_authenticated=True,
            is_member=False,
            is_owner_or_self=False,
        )

    @staticmethod
    def _compute_user_access(viewer, target_user_id: UUID) -> ViewerAccess:
        """Compute access for a viewer looking at a user profile."""
        # Self
        if viewer.id == target_user_id:
            return ViewerAccess(
                level=UserVisibility.WORLD + 1,
                is_authenticated=True,
                is_member=True,
                is_owner_or_self=True,
            )

        # Staff/superuser
        if viewer.is_staff or viewer.is_superuser:
            return ViewerAccess(
                level=UserVisibility.WORLD + 1,
                is_authenticated=True,
                is_member=True,
                is_owner_or_self=True,
            )

        # Check connection
        from apps.network.selectors import ConnectionSelector

        if ConnectionSelector.is_connected(
            user_a_id=viewer.id, user_b_id=target_user_id
        ):
            return ViewerAccess(
                level=UserVisibility.CONNECTIONS,
                is_authenticated=True,
                is_member=False,
                is_owner_or_self=False,
            )

        # Authenticated stranger
        return ViewerAccess(
            level=UserVisibility.WORLD,
            is_authenticated=True,
            is_member=False,
            is_owner_or_self=False,
        )

    @staticmethod
    def _compute_business_access(viewer, business_id: UUID) -> ViewerAccess:
        """Compute access for a viewer looking at a business profile."""
        from apps.core.constants import AccountType
        from apps.network.selectors import ConnectionSelector, FollowSelector
        from apps.rbac.selectors import MembershipSelector, PermissionSelector

        # Staff/superuser
        if viewer.is_staff or viewer.is_superuser:
            return ViewerAccess(
                level=BusinessVisibility.WORLD + 1,
                is_authenticated=True,
                is_member=True,
                is_owner_or_self=True,
            )

        # Check membership (short-circuit if found)
        membership = MembershipSelector.get_active_membership_for_user_account(
            user=viewer,
            account_type=AccountType.BUSINESS,
            account_id=business_id,
        )
        if membership:
            # Get RBAC permissions for this membership
            perm_tuples = PermissionSelector.get_permissions_for_membership(
                membership_id=membership.id,
            )
            perm_codes = frozenset(code for code, scope in perm_tuples)

            # Check if owner (role level 0)
            is_owner = membership.role is not None and membership.role.level == 0

            return ViewerAccess(
                level=BusinessVisibility.WORLD + 1,
                is_authenticated=True,
                is_member=True,
                is_owner_or_self=is_owner,
                permissions=perm_codes,
            )

        # Check follower
        if FollowSelector.is_following(
            follower_id=viewer.id,
            followee_type="business",
            followee_id=business_id,
        ):
            return ViewerAccess(
                level=BusinessVisibility.FOLLOWERS,
                is_authenticated=True,
                is_member=False,
                is_owner_or_self=False,
            )

        # Check B2B connection
        if ConnectionSelector.is_connected_account(
            a_type="business",
            a_id=business_id,
            b_type="business",
            b_id=business_id,  # placeholder — B2B not yet wired
        ):
            # Note: B2B connections require knowing the viewer's business.
            # For now, skip this — authenticated non-follower falls through.
            pass

        # Authenticated stranger
        return ViewerAccess(
            level=BusinessVisibility.WORLD,
            is_authenticated=True,
            is_member=False,
            is_owner_or_self=False,
        )

    @staticmethod
    def _compute_platform_access(viewer, platform_id: UUID) -> ViewerAccess:
        """Compute access for a viewer looking at the platform."""
        from apps.core.constants import AccountType
        from apps.rbac.selectors import MembershipSelector, PermissionSelector

        # Staff/superuser
        if viewer.is_staff or viewer.is_superuser:
            return ViewerAccess(
                level=PlatformVisibility.WORLD + 1,
                is_authenticated=True,
                is_member=True,
                is_owner_or_self=True,
            )

        # Check membership
        membership = MembershipSelector.get_active_membership_for_user_account(
            user=viewer,
            account_type=AccountType.PLATFORM,
            account_id=platform_id,
        )
        if membership:
            perm_tuples = PermissionSelector.get_permissions_for_membership(
                membership_id=membership.id,
            )
            perm_codes = frozenset(code for code, scope in perm_tuples)

            is_owner = membership.role is not None and membership.role.level == 0

            return ViewerAccess(
                level=PlatformVisibility.WORLD + 1,
                is_authenticated=True,
                is_member=True,
                is_owner_or_self=is_owner,
                permissions=perm_codes,
            )

        # Authenticated stranger
        return ViewerAccess(
            level=PlatformVisibility.WORLD,
            is_authenticated=True,
            is_member=False,
            is_owner_or_self=False,
        )

    @staticmethod
    def filter_fields(
        *,
        data: Dict[str, Any],
        registry_key: str,
        viewer_access: ViewerAccess,
        visibility_overrides: Dict[str, int] | None = None,
        is_public: bool = True,
    ) -> Dict[str, Any]:
        """Filter serialized data based on viewer access and field visibility config.

        Pure logic — 0 DB queries.

        Args:
            data: Serialized dict from DRF.
            registry_key: Which field registry to use (e.g., "business_profile").
            viewer_access: Precomputed ViewerAccess for this request.
            visibility_overrides: Owner's custom T2 overrides (from JSONField).
            is_public: Whether the profile is public (global T2 override).

        Returns:
            Filtered dict with invisible fields removed.
        """
        registry = get_registry(registry_key)
        if not registry:
            return data  # No registry → pass through everything

        overrides = visibility_overrides or {}
        filtered = {}

        for field_name, value in data.items():
            config = registry.get(field_name)

            # Unregistered fields pass through
            if config is None:
                filtered[field_name] = value
                continue

            if VisibilityResolver._can_see_field(
                config=config,
                viewer_access=viewer_access,
                is_public=is_public,
                override_level=overrides.get(field_name),
            ):
                filtered[field_name] = value

        return filtered

    @staticmethod
    def can_see_field(
        *,
        field_name: str,
        registry_key: str,
        viewer_access: ViewerAccess,
        visibility_overrides: Dict[str, int] | None = None,
        is_public: bool = True,
    ) -> bool:
        """Check if a viewer can see a specific field.

        Pure logic — 0 DB queries.
        """
        registry = get_registry(registry_key)
        config = registry.get(field_name)
        if config is None:
            return True  # Unregistered → visible

        overrides = visibility_overrides or {}
        return VisibilityResolver._can_see_field(
            config=config,
            viewer_access=viewer_access,
            is_public=is_public,
            override_level=overrides.get(field_name),
        )

    @staticmethod
    def _can_see_field(
        *,
        config: FieldVisibilityConfig,
        viewer_access: ViewerAccess,
        is_public: bool,
        override_level: int | None,
    ) -> bool:
        """Core visibility check for a single field."""
        tier = config.tier

        # T1: always visible
        if tier == T1:
            return True

        # T2: conditional
        if tier == T2:
            if viewer_access.is_owner_or_self:
                return True
            if viewer_access.is_member:
                return True  # Members bypass T2
            if is_public:
                return True  # Global override
            # Per-field level check (requires authentication)
            if not viewer_access.is_authenticated:
                return False
            required_level = (
                override_level if override_level is not None else config.default_level
            )
            if required_level is None:
                return False  # Misconfigured T2 → hide
            return viewer_access.level >= required_level

        # T3: always private (members with permission only)
        if tier == T3:
            if viewer_access.is_owner_or_self:
                return True
            if not viewer_access.is_member:
                return False
            # Member — check RBAC permission if required
            if config.required_permission:
                return config.required_permission in viewer_access.permissions
            return True  # Member, no specific permission required

        # Unknown tier → hide (safe default)
        return False

    @staticmethod
    def get_visibility_settings(
        *,
        registry_key: str,
        visibility_overrides: Dict[str, int] | None = None,
    ) -> List[Dict[str, Any]]:
        """Get T2 field settings for the owner's settings UI.

        Returns a list of dicts with field_name, current_level, default_level, and choices.
        """
        t2_fields = get_t2_fields(registry_key)
        if not t2_fields:
            return []

        account_type = get_account_type_for_registry(registry_key)
        choices = get_visibility_choices(account_type)
        overrides = visibility_overrides or {}

        settings = []
        for field_name, config in t2_fields.items():
            current = overrides.get(field_name, config.default_level)
            settings.append(
                {
                    "field_name": field_name,
                    "current_level": current,
                    "default_level": config.default_level,
                    "choices": [{"value": c.value, "label": c.label} for c in choices],
                }
            )

        return settings
