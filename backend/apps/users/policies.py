"""
User Policies
=============
Authorization rules for user-related operations.

Used by:
    - UserPublicDetailView: controls who can view a user's public profile
    - PermissionInjectMixin: provides _permissions dict for frontend UI gating
"""

from apps.users.models import User


class UserPolicy:
    """Authorization policy for user profiles."""

    @staticmethod
    def can_view_profile(*, viewer: User, target: User) -> bool:
        """
        Check if viewer can see the target user's full profile.

        Rules:
            - Always can view own profile
            - Staff/superuser can view any profile
            - Inactive users: always False
            - Public profiles: always visible
            - Private profiles: visible to connected users
        """
        if not viewer.is_authenticated:
            return False
        if viewer.id == target.id:
            return True
        if viewer.is_staff or viewer.is_superuser:
            return True
        if not target.is_active:
            return False
        profile = getattr(target, 'profile', None)
        if profile is None:
            return False
        if profile.is_public:
            return True
        # Private profile — check connection
        from apps.network.selectors import ConnectionSelector
        return ConnectionSelector.is_connected(
            user_a_id=viewer.id, user_b_id=target.id,
        )

    @staticmethod
    def get_viewer_permissions(*, viewer: User, target: User) -> dict[str, bool]:
        """
        Return permission booleans for frontend UI gating.

        Injected as _permissions in GET detail responses via PermissionInjectMixin.
        """
        from apps.network.policies import NetworkPolicy

        perms = {
            "is_own_profile": viewer.id == target.id,
            "can_edit_profile": viewer.id == target.id,
        }
        if viewer.id != target.id:
            perms.update(
                NetworkPolicy.get_connection_permissions_for_user(
                    viewer=viewer, target_user_id=target.id,
                )
            )
        else:
            perms["can_connect"] = False
            perms["can_disconnect"] = False
        return perms
