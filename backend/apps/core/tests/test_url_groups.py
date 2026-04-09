"""
Tests for SG System Gates — URL group decision logic and group file content.

Phase 2 of the Feature Gate System. Tests the coordinator's decision layer
(get_enabled_groups) and verifies each URL group file exports the expected
route patterns.
"""

import pytest

from apps.core.feature_config import FeatureConfig
from backend_core.urls import GATED_GROUPS, get_enabled_groups

# =============================================================================
# TestGetEnabledGroups — Decision logic (pure function, no Django URLs)
# =============================================================================


class TestGetEnabledGroups:
    """Test the get_enabled_groups() decision function."""

    def test_full_mode_all_systems_on(self, feature_config_override):
        """Full deployment: all 9 groups enabled."""
        feature_config_override(
            {
                "org_mode": "full",
                "systems": {
                    "transaction": True,
                    "forms": True,
                    "network": True,
                    "chat": True,
                    "cms": True,
                    "explore": True,
                    "notifications": True,
                    "governance": True,
                },
            }
        )
        enabled = get_enabled_groups()
        assert enabled == {
            "organization",
            "transaction",
            "forms",
            "cms",
            "explore",
            "network",
            "chat",
            "notifications",
            "governance",
        }

    def test_empty_config_returns_empty_set(self):
        """No config → minimal deployment → nothing enabled."""
        fc = FeatureConfig()
        fc._config = {}
        fc._loaded = True
        enabled = get_enabled_groups(fc)
        assert enabled == set()

    def test_user_only_no_organization(self, feature_config_override):
        """user_only mode: no organization group."""
        feature_config_override(
            {
                "org_mode": "user_only",
                "systems": {"transaction": True, "network": True},
            }
        )
        enabled = get_enabled_groups()
        assert "organization" not in enabled
        assert "transaction" in enabled
        assert "network" in enabled

    def test_user_and_platform_has_organization(self, feature_config_override):
        """user_and_platform mode: organization group present (platform only)."""
        feature_config_override({"org_mode": "user_and_platform"})
        enabled = get_enabled_groups()
        assert "organization" in enabled

    def test_full_mode_has_organization(self, feature_config_override):
        """full mode: organization group present (both biz + platform)."""
        feature_config_override({"org_mode": "full"})
        enabled = get_enabled_groups()
        assert "organization" in enabled

    def test_selective_systems(self, feature_config_override):
        """Chat off, network on — selective enabling."""
        feature_config_override({"systems": {"chat": False, "network": True}})
        enabled = get_enabled_groups()
        assert "chat" not in enabled
        assert "network" in enabled

    def test_single_system_chat(self, feature_config_override):
        """Only chat system enabled."""
        feature_config_override(
            {
                "org_mode": "user_only",
                "systems": {
                    "chat": True,
                    "transaction": False,
                    "forms": False,
                    "network": False,
                    "cms": False,
                    "explore": False,
                    "notifications": False,
                    "governance": False,
                },
            }
        )
        enabled = get_enabled_groups()
        assert enabled == {"chat"}

    def test_single_system_cms(self, feature_config_override):
        """Only CMS system enabled."""
        feature_config_override(
            {
                "org_mode": "user_only",
                "systems": {
                    "cms": True,
                    "transaction": False,
                    "forms": False,
                    "network": False,
                    "chat": False,
                    "explore": False,
                    "notifications": False,
                    "governance": False,
                },
            }
        )
        enabled = get_enabled_groups()
        assert enabled == {"cms"}

    def test_all_systems_off_explicitly(self, feature_config_override):
        """All systems explicitly off → empty set (org_mode user_only)."""
        feature_config_override(
            {
                "org_mode": "user_only",
                "systems": {
                    "transaction": False,
                    "forms": False,
                    "network": False,
                    "chat": False,
                    "cms": False,
                    "explore": False,
                    "notifications": False,
                    "governance": False,
                },
            }
        )
        enabled = get_enabled_groups()
        assert enabled == set()

    def test_org_mode_without_systems_key(self, feature_config_override):
        """org_mode=full but no systems key → only organization."""
        feature_config_override(
            {
                "org_mode": "full",
                "systems": {
                    "transaction": False,
                    "forms": False,
                    "network": False,
                    "chat": False,
                    "cms": False,
                    "explore": False,
                    "notifications": False,
                    "governance": False,
                },
            }
        )
        enabled = get_enabled_groups()
        assert enabled == {"organization"}

    def test_each_system_independently(self, feature_config_override):
        """Each system independently enables exactly its own group."""
        system_names = [
            "transaction",
            "forms",
            "cms",
            "explore",
            "network",
            "chat",
            "notifications",
            "governance",
        ]
        for name in system_names:
            fc = FeatureConfig()
            fc._config = {"org_mode": "user_only", "systems": {name: True}}
            fc._loaded = True
            enabled = get_enabled_groups(fc)
            assert name in enabled, f"{name} should be enabled"
            assert len(enabled) == 1, f"Only {name} should be enabled, got {enabled}"

    def test_gated_groups_has_exactly_9_keys(self):
        """GATED_GROUPS dict has exactly 9 entries (the 9 URL groups)."""
        assert len(GATED_GROUPS) == 9
        assert set(GATED_GROUPS.keys()) == {
            "organization",
            "transaction",
            "forms",
            "cms",
            "explore",
            "network",
            "chat",
            "notifications",
            "governance",
        }

    def test_default_parameter_uses_singleton(self):
        """Calling with no argument uses the module-level singleton (full config in tests)."""
        enabled = get_enabled_groups()
        # Session fixture sets all features on
        assert "organization" in enabled
        assert "chat" in enabled

    def test_missing_systems_key_defaults_all_off(self):
        """Config with no 'systems' key → all systems default off."""
        fc = FeatureConfig()
        fc._config = {"org_mode": "user_only"}
        fc._loaded = True
        enabled = get_enabled_groups(fc)
        assert "transaction" not in enabled
        assert "chat" not in enabled


# =============================================================================
# TestUrlGroupFiles — Verify each group file has correct route patterns
# =============================================================================


class TestUrlGroupFiles:
    """Test that each URL group file exports the expected patterns."""

    def test_base_has_always_on_namespaces(self):
        """base.py has auth, users, email, rbac namespaces (not notifications)."""
        from backend_core.urls.base import urlpatterns

        namespaces = {
            p.namespace for p in urlpatterns if hasattr(p, "namespace") and p.namespace
        }
        expected = {"authentication", "users", "email", "rbac"}
        assert expected <= namespaces
        # Notifications moved to gated group (systems.notifications)
        assert "notifications" not in namespaces

    def test_base_has_health_routes(self):
        """base.py has health-check and readiness-check named routes."""
        from backend_core.urls.base import urlpatterns

        names = {p.name for p in urlpatterns if hasattr(p, "name") and p.name}
        assert "health-check" in names
        assert "readiness-check" in names

    def test_transaction_group(self):
        """transaction.py has transaction namespace."""
        from backend_core.urls.transaction import urlpatterns

        namespaces = {
            p.namespace for p in urlpatterns if hasattr(p, "namespace") and p.namespace
        }
        assert "transaction" in namespaces

    def test_forms_group(self):
        """forms.py has forms namespace."""
        from backend_core.urls.forms import urlpatterns

        namespaces = {
            p.namespace for p in urlpatterns if hasattr(p, "namespace") and p.namespace
        }
        assert "forms" in namespaces

    def test_cms_group(self):
        """cms.py has cms and cms-public namespaces."""
        from backend_core.urls.cms import urlpatterns

        namespaces = {
            p.namespace for p in urlpatterns if hasattr(p, "namespace") and p.namespace
        }
        assert "cms" in namespaces
        assert "cms-public" in namespaces

    def test_explore_group(self):
        """explore.py has explore namespace."""
        from backend_core.urls.explore import urlpatterns

        namespaces = {
            p.namespace for p in urlpatterns if hasattr(p, "namespace") and p.namespace
        }
        assert "explore" in namespaces

    def test_network_group(self):
        """network.py has network namespace."""
        from backend_core.urls.network import urlpatterns

        namespaces = {
            p.namespace for p in urlpatterns if hasattr(p, "namespace") and p.namespace
        }
        assert "network" in namespaces

    def test_chat_group(self):
        """chat.py has chat namespace."""
        from backend_core.urls.chat import urlpatterns

        namespaces = {
            p.namespace for p in urlpatterns if hasattr(p, "namespace") and p.namespace
        }
        assert "chat" in namespaces

    def test_organization_group(self):
        """organization.py has platform and business namespaces (with all-on baseline)."""
        from backend_core.urls.organization import urlpatterns

        namespaces = {
            p.namespace for p in urlpatterns if hasattr(p, "namespace") and p.namespace
        }
        # Session fixture has org_mode=full → both present
        assert "platform" in namespaces
        assert "business" in namespaces

    @pytest.mark.skipif(
        not __import__("django").conf.settings.DEBUG,
        reason="Dev routes only available in DEBUG mode",
    )
    def test_dev_group(self):
        """dev.py has schema, swagger-ui, redoc route names."""
        from backend_core.urls.dev import urlpatterns

        names = set()
        for p in urlpatterns:
            if hasattr(p, "name") and p.name:
                names.add(p.name)
        assert "schema" in names
        assert "swagger-ui" in names
        assert "redoc" in names
