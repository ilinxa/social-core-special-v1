"""
SG System Gate integration tests.

Verifies that URL routing works correctly with the coordinator pattern:
- Always-on routes always resolve
- Gated routes resolve when enabled (test baseline)
- Decision function returns empty set for empty config
"""

import pytest
from django.urls import get_resolver, resolve, reverse

from apps.core.feature_config import FeatureConfig
from backend_core.urls import get_enabled_groups


@pytest.mark.django_db
class TestSGIntegration:
    """Integration tests for SG gate URL routing."""

    def test_always_on_routes_resolve(self):
        """Always-on routes (auth, health, users) resolve regardless of config."""
        # Health probe
        match = resolve("/health/")
        assert match.url_name == "health-check"

        # Readiness probe
        match = resolve("/ready/")
        assert match.url_name == "readiness-check"

        # Auth login (reverse by namespace)
        url = reverse("authentication:login")
        assert "/api/v1/auth/" in url

    def test_gated_routes_resolve_when_enabled(self):
        """Gated routes resolve with all-on test baseline."""
        # Chat (gated by systems.chat)
        url = reverse("chat:conversation-list-create")
        assert "/api/v1/chat/" in url

        # Network (gated by systems.network)
        url = reverse("network:follow-create")
        assert "/api/v1/network/" in url

        # Transaction (gated by systems.transaction)
        url = reverse("transaction:list")
        assert "/api/v1/transactions/" in url

        # Forms — namespace check (template-list requires URL args)
        resolver = get_resolver()
        assert "forms" in resolver.namespace_dict

        # CMS (gated by systems.cms)
        url = reverse("cms:admin-site-list-create")
        assert "/api/v1/cms/admin/" in url

        # Explore (gated by systems.explore)
        url = reverse("explore:businesses")
        assert "/api/v1/explore/" in url

        # Organization — business + platform (gated by org_mode=full)
        url = reverse("business:list-create")
        assert "/api/v1/business/" in url

        url = reverse("platform:account")
        assert "/api/v1/platform/" in url

        # Notifications (gated by systems.notifications)
        url = reverse("notifications:history")
        assert "/api/v1/notifications/" in url

        url = reverse("notifications:preferences")
        assert "/api/v1/notifications/" in url

        url = reverse("notifications:scopes")
        assert "/api/v1/notifications/" in url

    def test_empty_config_returns_no_groups(self):
        """Empty config → get_enabled_groups returns empty set."""
        fc = FeatureConfig()
        fc._config = {}
        fc._loaded = True
        enabled = get_enabled_groups(fc)
        assert enabled == set()
