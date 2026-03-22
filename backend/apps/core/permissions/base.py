"""
Base Permissions
================
Reusable DRF permission classes.

Design Principles:
    - Permissions check WHO can access (authentication + basic authorization)
    - Policies check business rules (in domain layer)
    - Keep permissions thin - delegate complex logic to policies

Permission Types:
    1. Global permissions: Check in has_permission() - runs before view logic
    2. Object permissions: Check in has_object_permission() - runs per object

Usage:
    from apps.core.permissions import IsAuthenticated, IsOwner

    class ProductView(APIView):
        permission_classes = [IsAuthenticated, IsOwner]
"""

from rest_framework.permissions import BasePermission

# =============================================================================
# AUTHENTICATION PERMISSIONS
# =============================================================================


class IsAuthenticated(BasePermission):
    """
    Allows access only to authenticated users.

    Use as base permission for most protected endpoints.

    Note:
        This checks request.user.is_authenticated, which requires
        proper authentication middleware/backend setup.
    """

    message = "Authentication required"

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class IsAuthenticatedOrReadOnly(BasePermission):
    """
    Allows read access to anyone, write access only to authenticated users.

    Safe methods (GET, HEAD, OPTIONS) are always allowed.
    Other methods require authentication.

    Use for:
        - Public listings with authenticated creation
        - Resources viewable by anyone but editable by members
    """

    message = "Authentication required for this action"

    SAFE_METHODS = ("GET", "HEAD", "OPTIONS")

    def has_permission(self, request, view):
        if request.method in self.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)


# =============================================================================
# STAFF/ADMIN PERMISSIONS
# =============================================================================


class IsStaff(BasePermission):
    """
    Allows access only to staff users.

    Checks request.user.is_staff flag.

    Use for:
        - Admin endpoints
        - Internal tools
        - Support dashboards
    """

    message = "Staff access required"

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.is_staff
        )


class IsStaffOrReadOnly(BasePermission):
    """
    Allows read access to anyone, write access only to staff.

    Use for:
        - Public resources managed by admins
        - Reference data (categories, tags)
    """

    message = "Staff access required for this action"

    SAFE_METHODS = ("GET", "HEAD", "OPTIONS")

    def has_permission(self, request, view):
        if request.method in self.SAFE_METHODS:
            return True
        return bool(
            request.user and request.user.is_authenticated and request.user.is_staff
        )


class IsSuperuser(BasePermission):
    """
    Allows access only to superusers.

    Use sparingly for:
        - System configuration
        - User management
        - Dangerous operations
    """

    message = "Superuser access required"

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.is_superuser
        )


# =============================================================================
# OWNERSHIP PERMISSIONS
# =============================================================================


class IsOwner(BasePermission):
    """
    Allows access only to object owners.

    Object must have a user field (configurable via owner_field).

    Usage:
        class MyView(APIView):
            permission_classes = [IsAuthenticated, IsOwner]

            def get_object(self):
                return Product.objects.get(pk=self.kwargs["pk"])

    Customization:
        Override owner_field in subclass:
            class IsAuthor(IsOwner):
                owner_field = "author"
    """

    message = "You do not have permission to access this resource"

    # Field name on the object that references the owner
    owner_field = "user"

    def has_object_permission(self, request, view, obj):
        # Get the owner from the object
        owner = getattr(obj, self.owner_field, None)

        if owner is None:
            # No owner field - deny access to be safe
            return False

        return owner == request.user


class IsOwnerOrStaff(IsOwner):
    """
    Allows access to object owner OR staff users.

    Use when:
        - Users manage their own resources
        - Staff can assist/manage any resource
    """

    message = "You must be the owner or a staff member"

    def has_object_permission(self, request, view, obj):
        # Staff can access anything
        if request.user.is_staff:
            return True

        # Otherwise, check ownership
        return super().has_object_permission(request, view, obj)


class IsOwnerOrReadOnly(IsOwner):
    """
    Allows read access to anyone, write access only to owner.

    Use for:
        - Public profiles (viewable, editable only by owner)
        - Public resources with owner management
    """

    message = "You must be the owner to modify this resource"

    SAFE_METHODS = ("GET", "HEAD", "OPTIONS")

    def has_object_permission(self, request, view, obj):
        # Read access for anyone
        if request.method in self.SAFE_METHODS:
            return True

        # Write access only for owner
        return super().has_object_permission(request, view, obj)


# =============================================================================
# VERIFIED USER PERMISSIONS
# =============================================================================


class IsVerified(BasePermission):
    """
    Allows access only to users with verified email.

    Requires user model to have is_verified or email_verified field.

    Use for:
        - Features requiring confirmed identity
        - Anti-spam measures
    """

    message = "Email verification required"

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Check for is_verified or email_verified field
        is_verified = getattr(request.user, "is_verified", None)
        if is_verified is None:
            is_verified = getattr(request.user, "email_verified", None)

        return bool(is_verified)


# =============================================================================
# ACTION-BASED PERMISSIONS
# =============================================================================


class DenyAll(BasePermission):
    """
    Denies all access.

    Use for:
        - Temporarily disabling endpoints
        - Placeholder during development
        - Feature flags (combine with conditions)
    """

    message = "Access denied"

    def has_permission(self, request, view):
        return False


class AllowAny(BasePermission):
    """
    Allows any access.

    Use for:
        - Public endpoints (health check, public listings)
        - Login/registration endpoints

    Note:
        Be explicit about allowing any access.
        It's better to add AllowAny than to have no permissions.
    """

    def has_permission(self, request, view):
        return True
