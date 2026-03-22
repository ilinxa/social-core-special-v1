# apps/core/tests/test_visibility_serializers.py
"""Tests for VisibilityAwareSerializerMixin + VisibilityOverrideInput."""

import pytest
from rest_framework import serializers as drf_serializers

from apps.core.visibility.enums import BusinessVisibility
from apps.core.visibility.resolver import ViewerAccess
from apps.core.visibility.serializers import (
    VisibilityAwareSerializerMixin,
    VisibilityOverrideInput,
)

# =============================================================================
# Test serializer using the mixin
# =============================================================================


class _FakeProfileSerializer(
    VisibilityAwareSerializerMixin, drf_serializers.Serializer
):
    """Fake serializer for testing the mixin."""

    visibility_registry = "business_profile"

    display_name = drf_serializers.CharField()
    tagline = drf_serializers.CharField()
    contact_email = drf_serializers.CharField()
    contact_phone = drf_serializers.CharField()


class _FakeAccountSerializer(
    VisibilityAwareSerializerMixin, drf_serializers.Serializer
):
    """Fake account serializer for testing T3."""

    visibility_registry = "business_account"

    id = drf_serializers.CharField()
    slug = drf_serializers.CharField()
    legal_name = drf_serializers.CharField()
    registration_number = drf_serializers.CharField()
    settings = drf_serializers.DictField()


class _NoRegistrySerializer(VisibilityAwareSerializerMixin, drf_serializers.Serializer):
    """Serializer with no visibility_registry set."""

    foo = drf_serializers.CharField()


# =============================================================================
# VisibilityAwareSerializerMixin tests
# =============================================================================


class TestVisibilityAwareSerializerMixin:
    def test_no_visibility_context_passes_all(self):
        """Backward compatible: no 'visibility' in context → all fields."""
        data = {
            "display_name": "Acme",
            "tagline": "Best",
            "contact_email": "hi@acme.com",
            "contact_phone": "+1",
        }
        serializer = _FakeProfileSerializer(data, context={})
        result = serializer.data
        assert "contact_email" in result
        assert "contact_phone" in result

    def test_no_registry_passes_all(self):
        """Serializer with no visibility_registry → all fields pass."""
        data = {"foo": "bar"}
        viewer = ViewerAccess.for_anonymous()
        serializer = _NoRegistrySerializer(
            data,
            context={"visibility": {"viewer_access": viewer, "is_public": False}},
        )
        result = serializer.data
        assert "foo" in result

    def test_t2_filtered_for_anonymous(self):
        """T2 fields hidden when private + anonymous."""
        data = {
            "display_name": "Acme",
            "tagline": "Best",
            "contact_email": "hi@acme.com",
            "contact_phone": "+1",
        }
        viewer = ViewerAccess.for_anonymous()
        serializer = _FakeProfileSerializer(
            data,
            context={"visibility": {"viewer_access": viewer, "is_public": False}},
        )
        result = serializer.data
        assert "display_name" in result
        assert "contact_email" not in result

    def test_t2_visible_when_public(self):
        data = {
            "display_name": "Acme",
            "tagline": "Best",
            "contact_email": "hi@acme.com",
            "contact_phone": "+1",
        }
        viewer = ViewerAccess.for_anonymous()
        serializer = _FakeProfileSerializer(
            data,
            context={"visibility": {"viewer_access": viewer, "is_public": True}},
        )
        result = serializer.data
        assert "contact_email" in result

    def test_t3_filtered_for_non_member(self):
        data = {
            "id": "abc",
            "slug": "acme",
            "legal_name": "Acme Inc",
            "registration_number": "REG123",
            "settings": {"key": "val"},
        }
        viewer = ViewerAccess(
            level=BusinessVisibility.WORLD,
            is_authenticated=True,
            is_member=False,
            is_owner_or_self=False,
        )
        serializer = _FakeAccountSerializer(
            data,
            context={"visibility": {"viewer_access": viewer, "is_public": True}},
        )
        result = serializer.data
        assert "id" in result
        assert "registration_number" not in result
        assert "settings" not in result

    def test_t3_visible_to_owner(self):
        data = {
            "id": "abc",
            "slug": "acme",
            "legal_name": "Acme Inc",
            "registration_number": "REG123",
            "settings": {"key": "val"},
        }
        viewer = ViewerAccess(
            level=BusinessVisibility.WORLD + 1,
            is_authenticated=True,
            is_member=True,
            is_owner_or_self=True,
        )
        serializer = _FakeAccountSerializer(
            data,
            context={"visibility": {"viewer_access": viewer, "is_public": True}},
        )
        result = serializer.data
        assert "registration_number" in result
        assert "settings" in result

    def test_overrides_applied(self):
        data = {
            "display_name": "Acme",
            "tagline": "Best",
            "contact_email": "hi@acme.com",
            "contact_phone": "+1",
        }
        viewer = ViewerAccess(
            level=BusinessVisibility.CONNECTIONS,
            is_authenticated=True,
            is_member=False,
            is_owner_or_self=False,
        )
        # Override contact_email to CONNECTIONS(1), viewer level=1 → visible
        serializer = _FakeProfileSerializer(
            data,
            context={
                "visibility": {
                    "viewer_access": viewer,
                    "is_public": False,
                    "visibility_overrides": {
                        "contact_email": BusinessVisibility.CONNECTIONS,
                    },
                }
            },
        )
        result = serializer.data
        assert "contact_email" in result
        # contact_phone still at default FOLLOWERS(2) > CONNECTIONS(1)
        assert "contact_phone" not in result


# =============================================================================
# VisibilityOverrideInput tests
# =============================================================================


class TestVisibilityOverrideInput:
    def test_valid_override(self):
        serializer = VisibilityOverrideInput(
            data={"overrides": {"contact_email": 3}},
            context={"registry_key": "business_profile"},
        )
        assert serializer.is_valid(), serializer.errors

    def test_invalid_field_name(self):
        serializer = VisibilityOverrideInput(
            data={"overrides": {"display_name": 3}},
            context={"registry_key": "business_profile"},
        )
        assert not serializer.is_valid()
        assert "display_name" in serializer.errors["overrides"]

    def test_invalid_level_value(self):
        serializer = VisibilityOverrideInput(
            data={"overrides": {"contact_email": 99}},
            context={"registry_key": "business_profile"},
        )
        assert not serializer.is_valid()
        assert "contact_email" in serializer.errors["overrides"]

    def test_t1_field_rejected(self):
        """T1 fields are not configurable."""
        serializer = VisibilityOverrideInput(
            data={"overrides": {"display_name": 1}},
            context={"registry_key": "business_profile"},
        )
        assert not serializer.is_valid()

    def test_t3_field_rejected(self):
        """T3 fields are not configurable."""
        serializer = VisibilityOverrideInput(
            data={"overrides": {"registration_number": 1}},
            context={"registry_key": "business_account"},
        )
        assert not serializer.is_valid()

    def test_missing_registry_key(self):
        serializer = VisibilityOverrideInput(
            data={"overrides": {"contact_email": 2}},
            context={},
        )
        assert not serializer.is_valid()

    def test_multiple_valid_overrides(self):
        serializer = VisibilityOverrideInput(
            data={"overrides": {"contact_email": 0, "contact_phone": 3}},
            context={"registry_key": "business_profile"},
        )
        assert serializer.is_valid(), serializer.errors

    def test_empty_overrides_valid(self):
        serializer = VisibilityOverrideInput(
            data={"overrides": {}},
            context={"registry_key": "business_profile"},
        )
        assert serializer.is_valid()
