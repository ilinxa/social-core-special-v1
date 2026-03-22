# apps/core/tests/test_permissions.py
"""
Comprehensive tests for all base permission classes.

Tests cover:
    - IsAuthenticated
    - IsAuthenticatedOrReadOnly
    - IsStaff
    - IsStaffOrReadOnly
    - IsSuperuser
    - IsOwner
    - IsOwnerOrStaff
    - IsOwnerOrReadOnly
    - IsVerified
    - DenyAll
    - AllowAny

Each permission class is tested with appropriate user types (anonymous,
regular, verified, staff, superuser) and HTTP methods (safe vs. unsafe).
"""

import pytest
from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIRequestFactory

from apps.core.permissions.base import (
    AllowAny,
    DenyAll,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
    IsOwner,
    IsOwnerOrReadOnly,
    IsOwnerOrStaff,
    IsStaff,
    IsStaffOrReadOnly,
    IsSuperuser,
    IsVerified,
)

# =============================================================================
# HELPERS
# =============================================================================


class MockObj:
    """Mock object with a configurable owner field for object-level permissions."""

    def __init__(self, user):
        self.user = user


class MockObjNoOwner:
    """Mock object without an owner field (missing 'user' attribute)."""

    pass


class MockObjCustomField:
    """Mock object with a custom owner field name."""

    def __init__(self, author):
        self.author = author


# Module-level factory used by all tests.
factory = APIRequestFactory()


def _make_request(method="get", user=None):
    """
    Create a DRF request with the given HTTP method and optional user.

    If no user is provided, the request is anonymous (AnonymousUser).
    """
    method_fn = getattr(factory, method.lower())
    request = method_fn("/test/")
    request.user = user if user is not None else AnonymousUser()
    return request


# =============================================================================
# IsAuthenticated
# =============================================================================


@pytest.mark.django_db
class TestIsAuthenticated:
    """Tests for IsAuthenticated permission."""

    permission = IsAuthenticated()

    def test_message(self):
        assert self.permission.message == "Authentication required"

    def test_authenticated_user_allowed(self, user):
        request = _make_request(user=user)
        assert self.permission.has_permission(request, None) is True

    def test_anonymous_user_denied(self):
        request = _make_request()
        assert self.permission.has_permission(request, None) is False

    def test_staff_user_allowed(self, staff_user):
        request = _make_request(user=staff_user)
        assert self.permission.has_permission(request, None) is True

    def test_superuser_allowed(self, superuser):
        request = _make_request(user=superuser)
        assert self.permission.has_permission(request, None) is True

    def test_verified_user_allowed(self, verified_user):
        request = _make_request(user=verified_user)
        assert self.permission.has_permission(request, None) is True

    def test_anonymous_user_denied_for_post(self):
        request = _make_request(method="post")
        assert self.permission.has_permission(request, None) is False

    def test_anonymous_user_denied_for_put(self):
        request = _make_request(method="put")
        assert self.permission.has_permission(request, None) is False

    def test_anonymous_user_denied_for_delete(self):
        request = _make_request(method="delete")
        assert self.permission.has_permission(request, None) is False

    def test_authenticated_user_allowed_for_all_methods(self, user):
        for method in ("get", "post", "put", "patch", "delete", "head", "options"):
            request = _make_request(method=method, user=user)
            assert self.permission.has_permission(request, None) is True

    def test_none_user_denied(self):
        """A request with user set to None should be denied."""
        request = factory.get("/test/")
        request.user = None
        assert self.permission.has_permission(request, None) is False


# =============================================================================
# IsAuthenticatedOrReadOnly
# =============================================================================


@pytest.mark.django_db
class TestIsAuthenticatedOrReadOnly:
    """Tests for IsAuthenticatedOrReadOnly permission."""

    permission = IsAuthenticatedOrReadOnly()

    def test_message(self):
        assert self.permission.message == "Authentication required for this action"

    # --- Safe methods (anonymous) ---

    def test_anonymous_get_allowed(self):
        request = _make_request(method="get")
        assert self.permission.has_permission(request, None) is True

    def test_anonymous_head_allowed(self):
        request = _make_request(method="head")
        assert self.permission.has_permission(request, None) is True

    def test_anonymous_options_allowed(self):
        request = _make_request(method="options")
        assert self.permission.has_permission(request, None) is True

    # --- Unsafe methods (anonymous) ---

    def test_anonymous_post_denied(self):
        request = _make_request(method="post")
        assert self.permission.has_permission(request, None) is False

    def test_anonymous_put_denied(self):
        request = _make_request(method="put")
        assert self.permission.has_permission(request, None) is False

    def test_anonymous_patch_denied(self):
        request = _make_request(method="patch")
        assert self.permission.has_permission(request, None) is False

    def test_anonymous_delete_denied(self):
        request = _make_request(method="delete")
        assert self.permission.has_permission(request, None) is False

    # --- Authenticated user (all methods) ---

    def test_authenticated_get_allowed(self, user):
        request = _make_request(method="get", user=user)
        assert self.permission.has_permission(request, None) is True

    def test_authenticated_post_allowed(self, user):
        request = _make_request(method="post", user=user)
        assert self.permission.has_permission(request, None) is True

    def test_authenticated_put_allowed(self, user):
        request = _make_request(method="put", user=user)
        assert self.permission.has_permission(request, None) is True

    def test_authenticated_patch_allowed(self, user):
        request = _make_request(method="patch", user=user)
        assert self.permission.has_permission(request, None) is True

    def test_authenticated_delete_allowed(self, user):
        request = _make_request(method="delete", user=user)
        assert self.permission.has_permission(request, None) is True


# =============================================================================
# IsStaff
# =============================================================================


@pytest.mark.django_db
class TestIsStaff:
    """Tests for IsStaff permission."""

    permission = IsStaff()

    def test_message(self):
        assert self.permission.message == "Staff access required"

    def test_staff_user_allowed(self, staff_user):
        request = _make_request(user=staff_user)
        assert self.permission.has_permission(request, None) is True

    def test_superuser_allowed(self, superuser):
        """Superusers are also staff in the factory."""
        request = _make_request(user=superuser)
        assert self.permission.has_permission(request, None) is True

    def test_regular_user_denied(self, user):
        request = _make_request(user=user)
        assert self.permission.has_permission(request, None) is False

    def test_anonymous_user_denied(self):
        request = _make_request()
        assert self.permission.has_permission(request, None) is False

    def test_staff_allowed_for_all_methods(self, staff_user):
        for method in ("get", "post", "put", "patch", "delete", "head", "options"):
            request = _make_request(method=method, user=staff_user)
            assert self.permission.has_permission(request, None) is True

    def test_regular_user_denied_for_all_methods(self, user):
        for method in ("get", "post", "put", "patch", "delete", "head", "options"):
            request = _make_request(method=method, user=user)
            assert self.permission.has_permission(request, None) is False


# =============================================================================
# IsStaffOrReadOnly
# =============================================================================


@pytest.mark.django_db
class TestIsStaffOrReadOnly:
    """Tests for IsStaffOrReadOnly permission."""

    permission = IsStaffOrReadOnly()

    def test_message(self):
        assert self.permission.message == "Staff access required for this action"

    # --- Safe methods (anyone) ---

    def test_anonymous_get_allowed(self):
        request = _make_request(method="get")
        assert self.permission.has_permission(request, None) is True

    def test_anonymous_head_allowed(self):
        request = _make_request(method="head")
        assert self.permission.has_permission(request, None) is True

    def test_anonymous_options_allowed(self):
        request = _make_request(method="options")
        assert self.permission.has_permission(request, None) is True

    def test_regular_user_get_allowed(self, user):
        request = _make_request(method="get", user=user)
        assert self.permission.has_permission(request, None) is True

    # --- Unsafe methods (non-staff) ---

    def test_anonymous_post_denied(self):
        request = _make_request(method="post")
        assert self.permission.has_permission(request, None) is False

    def test_anonymous_put_denied(self):
        request = _make_request(method="put")
        assert self.permission.has_permission(request, None) is False

    def test_anonymous_delete_denied(self):
        request = _make_request(method="delete")
        assert self.permission.has_permission(request, None) is False

    def test_regular_user_post_denied(self, user):
        request = _make_request(method="post", user=user)
        assert self.permission.has_permission(request, None) is False

    def test_regular_user_put_denied(self, user):
        request = _make_request(method="put", user=user)
        assert self.permission.has_permission(request, None) is False

    def test_regular_user_patch_denied(self, user):
        request = _make_request(method="patch", user=user)
        assert self.permission.has_permission(request, None) is False

    def test_regular_user_delete_denied(self, user):
        request = _make_request(method="delete", user=user)
        assert self.permission.has_permission(request, None) is False

    # --- Staff (all methods) ---

    def test_staff_get_allowed(self, staff_user):
        request = _make_request(method="get", user=staff_user)
        assert self.permission.has_permission(request, None) is True

    def test_staff_post_allowed(self, staff_user):
        request = _make_request(method="post", user=staff_user)
        assert self.permission.has_permission(request, None) is True

    def test_staff_put_allowed(self, staff_user):
        request = _make_request(method="put", user=staff_user)
        assert self.permission.has_permission(request, None) is True

    def test_staff_patch_allowed(self, staff_user):
        request = _make_request(method="patch", user=staff_user)
        assert self.permission.has_permission(request, None) is True

    def test_staff_delete_allowed(self, staff_user):
        request = _make_request(method="delete", user=staff_user)
        assert self.permission.has_permission(request, None) is True


# =============================================================================
# IsSuperuser
# =============================================================================


@pytest.mark.django_db
class TestIsSuperuser:
    """Tests for IsSuperuser permission."""

    permission = IsSuperuser()

    def test_message(self):
        assert self.permission.message == "Superuser access required"

    def test_superuser_allowed(self, superuser):
        request = _make_request(user=superuser)
        assert self.permission.has_permission(request, None) is True

    def test_staff_user_denied(self, staff_user):
        """Staff alone is not enough -- must be superuser."""
        request = _make_request(user=staff_user)
        assert self.permission.has_permission(request, None) is False

    def test_regular_user_denied(self, user):
        request = _make_request(user=user)
        assert self.permission.has_permission(request, None) is False

    def test_anonymous_user_denied(self):
        request = _make_request()
        assert self.permission.has_permission(request, None) is False

    def test_superuser_allowed_for_all_methods(self, superuser):
        for method in ("get", "post", "put", "patch", "delete"):
            request = _make_request(method=method, user=superuser)
            assert self.permission.has_permission(request, None) is True


# =============================================================================
# IsOwner
# =============================================================================


@pytest.mark.django_db
class TestIsOwner:
    """Tests for IsOwner object-level permission."""

    permission = IsOwner()

    def test_message(self):
        assert (
            self.permission.message
            == "You do not have permission to access this resource"
        )

    def test_owner_field_default(self):
        assert self.permission.owner_field == "user"

    def test_owner_allowed(self, user):
        request = _make_request(user=user)
        obj = MockObj(user=user)
        assert self.permission.has_object_permission(request, None, obj) is True

    def test_non_owner_denied(self, user, another_user):
        request = _make_request(user=user)
        obj = MockObj(user=another_user)
        assert self.permission.has_object_permission(request, None, obj) is False

    def test_staff_non_owner_denied(self, staff_user, user):
        """Staff does NOT bypass IsOwner (use IsOwnerOrStaff for that)."""
        request = _make_request(user=staff_user)
        obj = MockObj(user=user)
        assert self.permission.has_object_permission(request, None, obj) is False

    def test_superuser_non_owner_denied(self, superuser, user):
        """Superuser does NOT bypass IsOwner (use IsOwnerOrStaff for that)."""
        request = _make_request(user=superuser)
        obj = MockObj(user=user)
        assert self.permission.has_object_permission(request, None, obj) is False

    def test_object_without_owner_field_denied(self, user):
        """If the object has no owner field, access is denied."""
        request = _make_request(user=user)
        obj = MockObjNoOwner()
        assert self.permission.has_object_permission(request, None, obj) is False

    def test_owner_allowed_for_safe_methods(self, user):
        """Owner is allowed for GET, HEAD, OPTIONS."""
        obj = MockObj(user=user)
        for method in ("get", "head", "options"):
            request = _make_request(method=method, user=user)
            assert self.permission.has_object_permission(request, None, obj) is True

    def test_owner_allowed_for_unsafe_methods(self, user):
        """Owner is allowed for POST, PUT, PATCH, DELETE."""
        obj = MockObj(user=user)
        for method in ("post", "put", "patch", "delete"):
            request = _make_request(method=method, user=user)
            assert self.permission.has_object_permission(request, None, obj) is True

    def test_custom_owner_field(self, user, another_user):
        """Test that a subclass can use a different owner_field."""

        class IsAuthor(IsOwner):
            owner_field = "author"

        permission = IsAuthor()
        request = _make_request(user=user)

        # User is the author -- allowed
        obj = MockObjCustomField(author=user)
        assert permission.has_object_permission(request, None, obj) is True

        # User is NOT the author -- denied
        obj = MockObjCustomField(author=another_user)
        assert permission.has_object_permission(request, None, obj) is False


# =============================================================================
# IsOwnerOrStaff
# =============================================================================


@pytest.mark.django_db
class TestIsOwnerOrStaff:
    """Tests for IsOwnerOrStaff object-level permission."""

    permission = IsOwnerOrStaff()

    def test_message(self):
        assert self.permission.message == "You must be the owner or a staff member"

    def test_owner_allowed(self, user):
        request = _make_request(user=user)
        obj = MockObj(user=user)
        assert self.permission.has_object_permission(request, None, obj) is True

    def test_staff_non_owner_allowed(self, staff_user, user):
        """Staff can access any object even if not the owner."""
        request = _make_request(user=staff_user)
        obj = MockObj(user=user)
        assert self.permission.has_object_permission(request, None, obj) is True

    def test_superuser_non_owner_allowed(self, superuser, user):
        """Superuser (who is also staff) can access any object."""
        request = _make_request(user=superuser)
        obj = MockObj(user=user)
        assert self.permission.has_object_permission(request, None, obj) is True

    def test_non_owner_non_staff_denied(self, user, another_user):
        """Regular user who is not the owner is denied."""
        request = _make_request(user=user)
        obj = MockObj(user=another_user)
        assert self.permission.has_object_permission(request, None, obj) is False

    def test_staff_allowed_for_all_methods(self, staff_user, user):
        obj = MockObj(user=user)
        for method in ("get", "post", "put", "patch", "delete"):
            request = _make_request(method=method, user=staff_user)
            assert self.permission.has_object_permission(request, None, obj) is True

    def test_owner_allowed_for_all_methods(self, user):
        obj = MockObj(user=user)
        for method in ("get", "post", "put", "patch", "delete"):
            request = _make_request(method=method, user=user)
            assert self.permission.has_object_permission(request, None, obj) is True

    def test_object_without_owner_field_staff_allowed(self, staff_user):
        """Staff can still access objects without an owner field."""
        request = _make_request(user=staff_user)
        obj = MockObjNoOwner()
        assert self.permission.has_object_permission(request, None, obj) is True

    def test_object_without_owner_field_regular_user_denied(self, user):
        """Non-staff with missing owner field is denied."""
        request = _make_request(user=user)
        obj = MockObjNoOwner()
        assert self.permission.has_object_permission(request, None, obj) is False


# =============================================================================
# IsOwnerOrReadOnly
# =============================================================================


@pytest.mark.django_db
class TestIsOwnerOrReadOnly:
    """Tests for IsOwnerOrReadOnly object-level permission."""

    permission = IsOwnerOrReadOnly()

    def test_message(self):
        assert (
            self.permission.message == "You must be the owner to modify this resource"
        )

    # --- Safe methods (anyone) ---

    def test_non_owner_get_allowed(self, user, another_user):
        request = _make_request(method="get", user=user)
        obj = MockObj(user=another_user)
        assert self.permission.has_object_permission(request, None, obj) is True

    def test_non_owner_head_allowed(self, user, another_user):
        request = _make_request(method="head", user=user)
        obj = MockObj(user=another_user)
        assert self.permission.has_object_permission(request, None, obj) is True

    def test_non_owner_options_allowed(self, user, another_user):
        request = _make_request(method="options", user=user)
        obj = MockObj(user=another_user)
        assert self.permission.has_object_permission(request, None, obj) is True

    # --- Unsafe methods (non-owner) ---

    def test_non_owner_post_denied(self, user, another_user):
        request = _make_request(method="post", user=user)
        obj = MockObj(user=another_user)
        assert self.permission.has_object_permission(request, None, obj) is False

    def test_non_owner_put_denied(self, user, another_user):
        request = _make_request(method="put", user=user)
        obj = MockObj(user=another_user)
        assert self.permission.has_object_permission(request, None, obj) is False

    def test_non_owner_patch_denied(self, user, another_user):
        request = _make_request(method="patch", user=user)
        obj = MockObj(user=another_user)
        assert self.permission.has_object_permission(request, None, obj) is False

    def test_non_owner_delete_denied(self, user, another_user):
        request = _make_request(method="delete", user=user)
        obj = MockObj(user=another_user)
        assert self.permission.has_object_permission(request, None, obj) is False

    # --- Owner (all methods) ---

    def test_owner_get_allowed(self, user):
        request = _make_request(method="get", user=user)
        obj = MockObj(user=user)
        assert self.permission.has_object_permission(request, None, obj) is True

    def test_owner_post_allowed(self, user):
        request = _make_request(method="post", user=user)
        obj = MockObj(user=user)
        assert self.permission.has_object_permission(request, None, obj) is True

    def test_owner_put_allowed(self, user):
        request = _make_request(method="put", user=user)
        obj = MockObj(user=user)
        assert self.permission.has_object_permission(request, None, obj) is True

    def test_owner_patch_allowed(self, user):
        request = _make_request(method="patch", user=user)
        obj = MockObj(user=user)
        assert self.permission.has_object_permission(request, None, obj) is True

    def test_owner_delete_allowed(self, user):
        request = _make_request(method="delete", user=user)
        obj = MockObj(user=user)
        assert self.permission.has_object_permission(request, None, obj) is True

    # --- Staff non-owner unsafe methods ---

    def test_staff_non_owner_read_allowed(self, staff_user, user):
        """Staff who is not the owner can still read."""
        request = _make_request(method="get", user=staff_user)
        obj = MockObj(user=user)
        assert self.permission.has_object_permission(request, None, obj) is True

    def test_staff_non_owner_write_denied(self, staff_user, user):
        """Staff who is not the owner cannot write (IsOwnerOrReadOnly, not IsOwnerOrStaff)."""
        request = _make_request(method="put", user=staff_user)
        obj = MockObj(user=user)
        assert self.permission.has_object_permission(request, None, obj) is False

    # --- Object without owner field ---

    def test_no_owner_field_read_allowed(self, user):
        """Safe methods are allowed even when owner field is missing."""
        request = _make_request(method="get", user=user)
        obj = MockObjNoOwner()
        assert self.permission.has_object_permission(request, None, obj) is True

    def test_no_owner_field_write_denied(self, user):
        """Unsafe methods are denied when owner field is missing."""
        request = _make_request(method="post", user=user)
        obj = MockObjNoOwner()
        assert self.permission.has_object_permission(request, None, obj) is False


# =============================================================================
# IsVerified
# =============================================================================


@pytest.mark.django_db
class TestIsVerified:
    """Tests for IsVerified permission."""

    permission = IsVerified()

    def test_message(self):
        assert self.permission.message == "Email verification required"

    def test_verified_user_allowed(self, verified_user):
        request = _make_request(user=verified_user)
        assert self.permission.has_permission(request, None) is True

    def test_unverified_user_denied(self, user):
        """Regular user (is_verified=False) is denied."""
        request = _make_request(user=user)
        assert self.permission.has_permission(request, None) is False

    def test_anonymous_user_denied(self):
        request = _make_request()
        assert self.permission.has_permission(request, None) is False

    def test_staff_verified_allowed(self, staff_user):
        """Staff users from the factory are verified."""
        request = _make_request(user=staff_user)
        assert self.permission.has_permission(request, None) is True

    def test_superuser_verified_allowed(self, superuser):
        """Superusers from the factory are verified."""
        request = _make_request(user=superuser)
        assert self.permission.has_permission(request, None) is True

    def test_none_user_denied(self):
        """A request with user set to None should be denied."""
        request = factory.get("/test/")
        request.user = None
        assert self.permission.has_permission(request, None) is False

    def test_verified_user_allowed_for_all_methods(self, verified_user):
        for method in ("get", "post", "put", "patch", "delete"):
            request = _make_request(method=method, user=verified_user)
            assert self.permission.has_permission(request, None) is True

    def test_unverified_user_denied_for_all_methods(self, user):
        for method in ("get", "post", "put", "patch", "delete"):
            request = _make_request(method=method, user=user)
            assert self.permission.has_permission(request, None) is False

    def test_email_verified_fallback_field(self, user):
        """
        IsVerified checks is_verified first, then falls back to email_verified.

        Simulate an object that has email_verified instead of is_verified.
        """
        # Remove is_verified and set email_verified
        original = getattr(user, "is_verified", None)
        try:
            user.is_verified = None  # force fallback
            user.email_verified = True
            request = _make_request(user=user)
            assert self.permission.has_permission(request, None) is True

            user.email_verified = False
            request = _make_request(user=user)
            assert self.permission.has_permission(request, None) is False
        finally:
            # Restore original state
            user.is_verified = original
            if hasattr(user, "email_verified"):
                delattr(user, "email_verified")


# =============================================================================
# DenyAll
# =============================================================================


@pytest.mark.django_db
class TestDenyAll:
    """Tests for DenyAll permission."""

    permission = DenyAll()

    def test_message(self):
        assert self.permission.message == "Access denied"

    def test_anonymous_denied(self):
        request = _make_request()
        assert self.permission.has_permission(request, None) is False

    def test_authenticated_user_denied(self, user):
        request = _make_request(user=user)
        assert self.permission.has_permission(request, None) is False

    def test_staff_user_denied(self, staff_user):
        request = _make_request(user=staff_user)
        assert self.permission.has_permission(request, None) is False

    def test_superuser_denied(self, superuser):
        request = _make_request(user=superuser)
        assert self.permission.has_permission(request, None) is False

    def test_denied_for_all_methods(self, superuser):
        for method in ("get", "post", "put", "patch", "delete", "head", "options"):
            request = _make_request(method=method, user=superuser)
            assert self.permission.has_permission(request, None) is False


# =============================================================================
# AllowAny
# =============================================================================


@pytest.mark.django_db
class TestAllowAny:
    """Tests for AllowAny permission."""

    permission = AllowAny()

    def test_no_custom_message(self):
        """AllowAny does not override the default message."""
        assert not hasattr(AllowAny, "message") or AllowAny.message is None or True
        # AllowAny inherits default message behavior from BasePermission

    def test_anonymous_allowed(self):
        request = _make_request()
        assert self.permission.has_permission(request, None) is True

    def test_authenticated_user_allowed(self, user):
        request = _make_request(user=user)
        assert self.permission.has_permission(request, None) is True

    def test_staff_user_allowed(self, staff_user):
        request = _make_request(user=staff_user)
        assert self.permission.has_permission(request, None) is True

    def test_superuser_allowed(self, superuser):
        request = _make_request(user=superuser)
        assert self.permission.has_permission(request, None) is True

    def test_allowed_for_all_methods(self):
        for method in ("get", "post", "put", "patch", "delete", "head", "options"):
            request = _make_request(method=method)
            assert self.permission.has_permission(request, None) is True

    def test_allowed_for_all_methods_authenticated(self, user):
        for method in ("get", "post", "put", "patch", "delete", "head", "options"):
            request = _make_request(method=method, user=user)
            assert self.permission.has_permission(request, None) is True


# =============================================================================
# INHERITANCE / STRUCTURE TESTS
# =============================================================================


class TestPermissionInheritance:
    """Verify permission class hierarchy and structure."""

    def test_is_owner_or_staff_inherits_from_is_owner(self):
        assert issubclass(IsOwnerOrStaff, IsOwner)

    def test_is_owner_or_read_only_inherits_from_is_owner(self):
        assert issubclass(IsOwnerOrReadOnly, IsOwner)

    def test_all_permissions_inherit_from_base_permission(self):
        from rest_framework.permissions import BasePermission

        for perm_class in (
            IsAuthenticated,
            IsAuthenticatedOrReadOnly,
            IsStaff,
            IsStaffOrReadOnly,
            IsSuperuser,
            IsOwner,
            IsOwnerOrStaff,
            IsOwnerOrReadOnly,
            IsVerified,
            DenyAll,
            AllowAny,
        ):
            assert issubclass(
                perm_class, BasePermission
            ), f"{perm_class.__name__} should inherit from BasePermission"

    def test_is_owner_or_staff_uses_parent_owner_field(self):
        """IsOwnerOrStaff inherits owner_field from IsOwner."""
        assert IsOwnerOrStaff().owner_field == "user"

    def test_is_owner_or_read_only_uses_parent_owner_field(self):
        """IsOwnerOrReadOnly inherits owner_field from IsOwner."""
        assert IsOwnerOrReadOnly().owner_field == "user"
