# apps/core/tests/test_views.py
"""
Tests for PermissionInjectMixin.

Uses a minimal test view to verify mixin behavior in isolation.
"""

import pytest
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from apps.core.views import PermissionInjectMixin


# =============================================================================
# TEST POLICY + VIEW (minimal fakes)
# =============================================================================


class FakePolicy:
    """Fake policy for testing mixin behavior."""

    @staticmethod
    def get_viewer_permissions(**kwargs):
        return {"can_edit": True, "can_delete": False}


class MixinView(PermissionInjectMixin, APIView):
    """View with mixin enabled."""

    policy_class = FakePolicy
    authentication_classes = []
    permission_classes = []

    def _build_policy_kwargs(self):
        return {}

    def get(self, request):
        self._inject_permissions = True
        return Response({"id": "123", "name": "test"})

    def post(self, request):
        self._inject_permissions = True
        return Response({"id": "123"}, status=status.HTTP_201_CREATED)

    def patch(self, request):
        self._inject_permissions = True
        return Response({"id": "123", "name": "updated"})


class NoFlagView(PermissionInjectMixin, APIView):
    """View with mixin but NO opt-in flag."""

    policy_class = FakePolicy
    authentication_classes = []
    permission_classes = []

    def _build_policy_kwargs(self):
        return {}

    def get(self, request):
        # No self._inject_permissions = True
        return Response({"id": "123", "name": "test"})


class NoPolicyView(PermissionInjectMixin, APIView):
    """View with mixin but no policy_class."""

    authentication_classes = []
    permission_classes = []

    def _build_policy_kwargs(self):
        return {}

    def get(self, request):
        self._inject_permissions = True
        return Response({"id": "123"})


# =============================================================================
# TESTS
# =============================================================================


class TestPermissionInjectMixin:
    """Tests for PermissionInjectMixin."""

    def setup_method(self):
        self.factory = APIRequestFactory()

    def test_get_with_flag_injects_permissions(self):
        """GET with _inject_permissions=True adds _permissions to response."""
        request = self.factory.get("/test/")
        view = MixinView.as_view()
        response = view(request)

        assert response.status_code == 200
        assert "_permissions" in response.data
        assert response.data["_permissions"] == {"can_edit": True, "can_delete": False}
        assert response.data["id"] == "123"

    def test_get_without_flag_no_injection(self):
        """GET without _inject_permissions flag does NOT inject."""
        request = self.factory.get("/test/")
        view = NoFlagView.as_view()
        response = view(request)

        assert response.status_code == 200
        assert "_permissions" not in response.data
        assert response.data["name"] == "test"

    def test_post_with_flag_no_injection(self):
        """POST with flag does NOT inject (GET only)."""
        request = self.factory.post("/test/", {}, format="json")
        view = MixinView.as_view()
        response = view(request)

        assert response.status_code == 201
        assert "_permissions" not in response.data

    def test_patch_with_flag_no_injection(self):
        """PATCH with flag does NOT inject (GET only)."""
        request = self.factory.patch("/test/", {}, format="json")
        view = MixinView.as_view()
        response = view(request)

        assert response.status_code == 200
        assert "_permissions" not in response.data

    def test_no_policy_class_no_injection(self):
        """GET with flag but no policy_class does NOT inject."""
        request = self.factory.get("/test/")
        view = NoPolicyView.as_view()
        response = view(request)

        assert response.status_code == 200
        assert "_permissions" not in response.data

    def test_original_data_preserved(self):
        """Mixin preserves all original response data."""
        request = self.factory.get("/test/")
        view = MixinView.as_view()
        response = view(request)

        assert response.data["id"] == "123"
        assert response.data["name"] == "test"
        assert "_permissions" in response.data
