"""
Tests for Feature Configuration System
=======================================
Comprehensive tests for the feature gate foundation:
- FeatureConfig loader (config loading, dot-notation access, system/feature/value gates)
- FeatureDisabled exception (domain exception for disabled features)
- FeatureRequired permission (DRF permission class factory)
- effective_limit() (dual limit resolution)
- Test fixtures (session-scoped baseline, per-test override)
"""

import json
import os
from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIRequestFactory

from apps.core.exceptions import FeatureDisabled
from apps.core.exceptions.domain import DomainException
from apps.core.exceptions.handler import STATUS_CODE_MAP, get_status_code
from apps.core.feature_config import FeatureConfig
from apps.core.permissions.base import FeatureRequired

# Module-level factory used by permission tests.
factory = APIRequestFactory()


# =============================================================================
# FeatureConfig — Loading
# =============================================================================


class TestFeatureConfigLoadConfig:
    """Tests for config file loading behavior."""

    def test_missing_file_returns_empty_dict(self, tmp_path):
        """Missing config file results in empty config (minimal deployment)."""
        result = FeatureConfig._load_config(str(tmp_path / "nonexistent.json"))

        assert result == {}

    def test_valid_json_file_loaded(self, tmp_path):
        """Valid JSON file is loaded and returned as dict."""
        config_file = tmp_path / "config.json"
        config_file.write_text(
            json.dumps({"org_mode": "full", "systems": {"chat": True}})
        )

        result = FeatureConfig._load_config(str(config_file))

        assert result == {"org_mode": "full", "systems": {"chat": True}}

    def test_invalid_json_returns_empty_dict(self, tmp_path):
        """Invalid JSON file results in empty config."""
        config_file = tmp_path / "bad.json"
        config_file.write_text("not valid json {{{")

        result = FeatureConfig._load_config(str(config_file))

        assert result == {}

    def test_non_dict_json_returns_empty_dict(self, tmp_path):
        """JSON file containing non-dict (e.g., list) results in empty config."""
        config_file = tmp_path / "list.json"
        config_file.write_text(json.dumps([1, 2, 3]))

        result = FeatureConfig._load_config(str(config_file))

        assert result == {}

    def test_empty_json_object_returns_empty_dict(self, tmp_path):
        """Empty JSON object returns empty dict."""
        config_file = tmp_path / "empty.json"
        config_file.write_text("{}")

        result = FeatureConfig._load_config(str(config_file))

        assert result == {}

    def test_file_read_error_returns_empty_dict(self, tmp_path):
        """OSError during file read results in empty config."""
        with patch("builtins.open", side_effect=OSError("permission denied")):
            config_file = tmp_path / "exists.json"
            config_file.write_text("{}")

            result = FeatureConfig._load_config(str(config_file))

        assert result == {}

    def test_reload_rereads_file(self, tmp_path):
        """reload() clears loaded state and re-reads from file."""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"org_mode": "full"}))

        fc = FeatureConfig()
        with patch.object(type(fc), "_ensure_loaded", wraps=fc._ensure_loaded):
            fc._config = {"org_mode": "full"}
            fc._loaded = True

            assert fc.get_org_mode() == "full"

            # Modify file content
            config_file.write_text(json.dumps({"org_mode": "user_only"}))

            # Reload should re-read
            with patch("django.conf.settings") as mock_settings:
                mock_settings.DEPLOYMENT_CONFIG_PATH = str(config_file)
                fc._loaded = False
                fc._ensure_loaded()

            assert fc._config == {"org_mode": "user_only"}

    def test_lazy_loading_on_first_access(self):
        """Config is not loaded until first access via get()."""
        fc = FeatureConfig()

        assert fc._loaded is False
        assert fc._config == {}

        # Trigger lazy loading
        fc._config = {"test": True}
        fc._loaded = True
        assert fc.get("test") is True


# =============================================================================
# FeatureConfig — get() Dot-Notation
# =============================================================================


class TestFeatureConfigGet:
    """Tests for dot-notation key traversal."""

    def test_top_level_key(self):
        """Access a top-level key."""
        fc = FeatureConfig()
        fc._config = {"org_mode": "full"}
        fc._loaded = True

        assert fc.get("org_mode") == "full"

    def test_nested_dot_notation(self):
        """Access a nested key via dot notation."""
        fc = FeatureConfig()
        fc._config = {"systems": {"chat": True}}
        fc._loaded = True

        assert fc.get("systems.chat") is True

    def test_deeply_nested_key(self):
        """Access a deeply nested key."""
        fc = FeatureConfig()
        fc._config = {"business": {"network": {"enabled": True}}}
        fc._loaded = True

        assert fc.get("business.network.enabled") is True

    def test_missing_key_returns_default(self):
        """Missing key returns the specified default."""
        fc = FeatureConfig()
        fc._config = {"systems": {"chat": True}}
        fc._loaded = True

        assert fc.get("systems.forms", False) is False

    def test_missing_intermediate_key_returns_default(self):
        """Missing intermediate key returns default."""
        fc = FeatureConfig()
        fc._config = {"systems": {"chat": True}}
        fc._loaded = True

        assert fc.get("nonexistent.deeply.nested", "fallback") == "fallback"

    def test_non_dict_intermediate_returns_default(self):
        """Non-dict intermediate value returns default."""
        fc = FeatureConfig()
        fc._config = {"systems": True}
        fc._loaded = True

        assert fc.get("systems.chat", False) is False

    def test_default_none_when_not_specified(self):
        """Default is None when not specified."""
        fc = FeatureConfig()
        fc._config = {}
        fc._loaded = True

        assert fc.get("missing") is None

    def test_empty_config_returns_default(self):
        """Empty config always returns default."""
        fc = FeatureConfig()
        fc._config = {}
        fc._loaded = True

        assert fc.get("anything.at.all", "default_val") == "default_val"


# =============================================================================
# FeatureConfig — System Gates (SG)
# =============================================================================


class TestFeatureConfigSystemGates:
    """Tests for SG-level system gate checks."""

    def test_enabled_system(self):
        """System marked True is enabled."""
        fc = FeatureConfig()
        fc._config = {"systems": {"chat": True}}
        fc._loaded = True

        assert fc.is_system_enabled("chat") is True

    def test_disabled_system(self):
        """System marked False is disabled."""
        fc = FeatureConfig()
        fc._config = {"systems": {"chat": False}}
        fc._loaded = True

        assert fc.is_system_enabled("chat") is False

    def test_missing_system_defaults_false(self):
        """Missing system key defaults to False."""
        fc = FeatureConfig()
        fc._config = {"systems": {"chat": True}}
        fc._loaded = True

        assert fc.is_system_enabled("forms") is False

    def test_empty_config_all_systems_off(self):
        """Empty config means all systems off."""
        fc = FeatureConfig()
        fc._config = {}
        fc._loaded = True

        for system in ("transaction", "forms", "network", "chat", "cms", "explore"):
            assert fc.is_system_enabled(system) is False

    def test_org_mode_full(self):
        """org_mode 'full' returned correctly."""
        fc = FeatureConfig()
        fc._config = {"org_mode": "full"}
        fc._loaded = True

        assert fc.get_org_mode() == "full"

    def test_org_mode_user_and_platform(self):
        """org_mode 'user_and_platform' returned correctly."""
        fc = FeatureConfig()
        fc._config = {"org_mode": "user_and_platform"}
        fc._loaded = True

        assert fc.get_org_mode() == "user_and_platform"

    def test_org_mode_user_only(self):
        """org_mode 'user_only' returned correctly."""
        fc = FeatureConfig()
        fc._config = {"org_mode": "user_only"}
        fc._loaded = True

        assert fc.get_org_mode() == "user_only"

    def test_org_mode_missing_defaults_user_only(self):
        """Missing org_mode defaults to 'user_only' (minimal)."""
        fc = FeatureConfig()
        fc._config = {}
        fc._loaded = True

        assert fc.get_org_mode() == "user_only"

    def test_has_business_true_when_full(self):
        """has_business() is True when org_mode is 'full'."""
        fc = FeatureConfig()
        fc._config = {"org_mode": "full"}
        fc._loaded = True

        assert fc.has_business() is True

    def test_has_business_false_when_user_and_platform(self):
        """has_business() is False when org_mode is 'user_and_platform'."""
        fc = FeatureConfig()
        fc._config = {"org_mode": "user_and_platform"}
        fc._loaded = True

        assert fc.has_business() is False

    def test_has_business_false_when_user_only(self):
        """has_business() is False when org_mode is 'user_only'."""
        fc = FeatureConfig()
        fc._config = {"org_mode": "user_only"}
        fc._loaded = True

        assert fc.has_business() is False

    def test_has_platform_true_when_full(self):
        """has_platform() is True when org_mode is 'full'."""
        fc = FeatureConfig()
        fc._config = {"org_mode": "full"}
        fc._loaded = True

        assert fc.has_platform() is True

    def test_has_platform_true_when_user_and_platform(self):
        """has_platform() is True when org_mode is 'user_and_platform'."""
        fc = FeatureConfig()
        fc._config = {"org_mode": "user_and_platform"}
        fc._loaded = True

        assert fc.has_platform() is True

    def test_has_platform_false_when_user_only(self):
        """has_platform() is False when org_mode is 'user_only'."""
        fc = FeatureConfig()
        fc._config = {"org_mode": "user_only"}
        fc._loaded = True

        assert fc.has_platform() is False


# =============================================================================
# FeatureConfig — Feature Gates (FG)
# =============================================================================


class TestFeatureConfigFeatureGates:
    """Tests for FG-level feature gate checks."""

    def test_simple_bool_enabled(self):
        """Simple bool feature returns True when set."""
        fc = FeatureConfig()
        fc._config = {"platform": {"forms": True}}
        fc._loaded = True

        assert fc.is_feature_enabled("platform.forms") is True

    def test_simple_bool_disabled(self):
        """Simple bool feature returns False when off."""
        fc = FeatureConfig()
        fc._config = {"platform": {"forms": False}}
        fc._loaded = True

        assert fc.is_feature_enabled("platform.forms") is False

    def test_dict_feature_is_truthy(self):
        """Dict feature value (e.g., business.cms = {...}) is truthy."""
        fc = FeatureConfig()
        fc._config = {"business": {"cms": {"enabled": True, "max_sites": 0}}}
        fc._loaded = True

        # The dict itself is truthy
        assert fc.is_feature_enabled("business.cms") is True
        # The nested .enabled path works
        assert fc.is_feature_enabled("business.cms.enabled") is True

    def test_nested_enabled(self):
        """Nested .enabled feature returns True when set."""
        fc = FeatureConfig()
        fc._config = {"business": {"network": {"enabled": True}}}
        fc._loaded = True

        assert fc.is_feature_enabled("business.network.enabled") is True

    def test_nested_disabled(self):
        """Nested .enabled feature returns False when off."""
        fc = FeatureConfig()
        fc._config = {"business": {"network": {"enabled": False}}}
        fc._loaded = True

        assert fc.is_feature_enabled("business.network.enabled") is False

    def test_missing_feature_defaults_false(self):
        """Missing feature path defaults to False."""
        fc = FeatureConfig()
        fc._config = {"business": {"cms": {"enabled": True}}}
        fc._loaded = True

        assert fc.is_feature_enabled("business.network.enabled") is False

    def test_empty_config_all_features_off(self):
        """Empty config means all features off."""
        fc = FeatureConfig()
        fc._config = {}
        fc._loaded = True

        assert fc.is_feature_enabled("business.cms.enabled") is False
        assert fc.is_feature_enabled("business.network.enabled") is False
        assert fc.is_feature_enabled("user.chat.enabled") is False
        assert fc.is_feature_enabled("platform.forms") is False


# =============================================================================
# FeatureConfig — Value Gates (VG)
# =============================================================================


class TestFeatureConfigValueGates:
    """Tests for VG-level limit and value access."""

    def test_get_limit_from_config(self):
        """Numeric limit read from config."""
        fc = FeatureConfig()
        fc._config = {"business": {"members": {"max_members": 50}}}
        fc._loaded = True

        assert fc.get_limit("business.members.max_members") == 50

    def test_get_limit_missing_returns_default(self):
        """Missing limit returns specified default."""
        fc = FeatureConfig()
        fc._config = {}
        fc._loaded = True

        assert fc.get_limit("business.members.max_members", default=1) == 1

    def test_get_limit_zero_means_unlimited(self):
        """Zero limit means unlimited (convention)."""
        fc = FeatureConfig()
        fc._config = {"limits": {"max_users": 0}}
        fc._loaded = True

        assert fc.get_limit("limits.max_users") == 0

    def test_get_limit_non_numeric_returns_default(self):
        """Non-numeric value returns default."""
        fc = FeatureConfig()
        fc._config = {"limits": {"max_users": "not_a_number"}}
        fc._loaded = True

        assert fc.get_limit("limits.max_users", default=10) == 10

    def test_get_value_returns_string(self):
        """get_value returns string values."""
        fc = FeatureConfig()
        fc._config = {"auth": {"verification": {"method": "both"}}}
        fc._loaded = True

        assert fc.get_value("auth.verification.method") == "both"

    def test_get_value_returns_list(self):
        """get_value returns list values."""
        fc = FeatureConfig()
        fc._config = {"chat": {"reactions": {"types": ["like", "heart"]}}}
        fc._loaded = True

        assert fc.get_value("chat.reactions.types") == ["like", "heart"]

    def test_get_value_missing_returns_default(self):
        """Missing value returns default."""
        fc = FeatureConfig()
        fc._config = {}
        fc._loaded = True

        assert fc.get_value("missing.path", default="fallback") == "fallback"


# =============================================================================
# FeatureConfig — effective_limit()
# =============================================================================


class TestEffectiveLimit:
    """Tests for dual limit resolution (config vs model)."""

    def test_both_unlimited(self):
        """Both 0 means unlimited."""
        assert FeatureConfig.effective_limit(0, 0) == 0

    def test_config_unlimited_model_set(self):
        """Config unlimited (0), model sets limit."""
        assert FeatureConfig.effective_limit(0, 5) == 5

    def test_model_unlimited_config_set(self):
        """Model unlimited (0), config sets limit."""
        assert FeatureConfig.effective_limit(10, 0) == 10

    def test_both_set_config_tighter(self):
        """Both set, config is tighter."""
        assert FeatureConfig.effective_limit(3, 10) == 3

    def test_both_set_model_tighter(self):
        """Both set, model is tighter."""
        assert FeatureConfig.effective_limit(10, 3) == 3

    def test_both_set_equal(self):
        """Both set to same value."""
        assert FeatureConfig.effective_limit(5, 5) == 5


# =============================================================================
# Minimal Deployment
# =============================================================================


class TestMinimalDeployment:
    """Tests confirming minimal-by-default behavior."""

    def test_no_config_all_systems_off(self):
        """No config loaded means all systems off."""
        fc = FeatureConfig()
        fc._config = {}
        fc._loaded = True

        for system in ("transaction", "forms", "network", "chat", "cms", "explore"):
            assert fc.is_system_enabled(system) is False, f"{system} should be off"

    def test_no_config_org_mode_user_only(self):
        """No config means org_mode defaults to user_only."""
        fc = FeatureConfig()
        fc._config = {}
        fc._loaded = True

        assert fc.get_org_mode() == "user_only"
        assert fc.has_business() is False
        assert fc.has_platform() is False

    def test_no_config_all_features_off(self):
        """No config means all FG gates off."""
        fc = FeatureConfig()
        fc._config = {}
        fc._loaded = True

        paths = [
            "user.can_create_business",
            "user.network.enabled",
            "business.members.enabled",
            "business.cms.enabled",
            "platform.members.enabled",
            "platform.forms",
        ]
        for path in paths:
            assert fc.is_feature_enabled(path) is False, f"{path} should be off"

    def test_empty_dict_same_as_missing(self):
        """Empty dict config behaves same as missing file."""
        fc = FeatureConfig()
        fc._config = {}
        fc._loaded = True

        assert fc.get_org_mode() == "user_only"
        assert fc.is_system_enabled("chat") is False
        assert fc.is_feature_enabled("business.network.enabled") is False
        assert fc.get_limit("limits.max_users") == 0


# =============================================================================
# FeatureDisabled Exception
# =============================================================================


class TestFeatureDisabledException:
    """Tests for the FeatureDisabled domain exception."""

    def test_default_message(self):
        """Default message is set correctly."""
        exc = FeatureDisabled()

        assert exc.message == "This feature is not available"

    def test_default_code(self):
        """Default code is 'feature_disabled'."""
        exc = FeatureDisabled()

        assert exc.code == "feature_disabled"

    def test_custom_message(self):
        """Accept custom message."""
        exc = FeatureDisabled(message="Chat is not available in this deployment")

        assert exc.message == "Chat is not available in this deployment"

    def test_feature_in_details(self):
        """Feature path included in details."""
        exc = FeatureDisabled(feature="business.network.enabled")

        assert exc.details == {"feature": "business.network.enabled"}

    def test_no_feature_empty_details(self):
        """No feature param means empty details."""
        exc = FeatureDisabled()

        assert exc.details == {}

    def test_to_dict_format(self):
        """to_dict produces correct API response structure."""
        exc = FeatureDisabled(feature="business.cms")
        result = exc.to_dict()

        assert result == {
            "message": "This feature is not available",
            "code": "feature_disabled",
            "details": {"feature": "business.cms"},
        }

    def test_inherits_domain_exception(self):
        """FeatureDisabled inherits from DomainException."""
        exc = FeatureDisabled()

        assert isinstance(exc, DomainException)

    def test_maps_to_403(self):
        """feature_disabled code maps to HTTP 403 in status map."""
        assert "feature_disabled" in STATUS_CODE_MAP
        assert STATUS_CODE_MAP["feature_disabled"] == status.HTTP_403_FORBIDDEN

    def test_get_status_code_returns_403(self):
        """get_status_code() returns 403 for feature_disabled."""
        assert get_status_code("feature_disabled") == 403


# =============================================================================
# FeatureRequired Permission
# =============================================================================


class TestFeatureRequiredPermission:
    """Tests for the FeatureRequired DRF permission class factory."""

    def test_returns_class_not_instance(self):
        """FeatureRequired() returns a class, not an instance."""
        result = FeatureRequired("business.cms.enabled")

        assert isinstance(result, type)

    def test_returned_class_has_readable_name(self):
        """Returned class has a readable __name__."""
        cls = FeatureRequired("business.network.enabled")

        assert cls.__name__ == "FeatureRequired_business.network.enabled"
        assert cls.__qualname__ == "FeatureRequired_business.network.enabled"

    def test_feature_enabled_allows_access(self, feature_config_override):
        """Permission passes when feature is on."""
        feature_config_override({"business": {"cms": {"enabled": True}}})
        cls = FeatureRequired("business.cms.enabled")
        permission = cls()
        request = factory.get("/test/")

        assert permission.has_permission(request, None) is True

    def test_feature_disabled_raises_feature_disabled(self, feature_config_override):
        """Permission raises FeatureDisabled when feature is off."""
        feature_config_override({"business": {"cms": {"enabled": False}}})
        cls = FeatureRequired("business.cms.enabled")
        permission = cls()
        request = factory.get("/test/")

        with pytest.raises(FeatureDisabled) as exc_info:
            permission.has_permission(request, None)

        assert exc_info.value.code == "feature_disabled"

    def test_feature_disabled_includes_feature_path(self, feature_config_override):
        """FeatureDisabled exception includes the feature path in details."""
        feature_config_override({"business": {"network": {"enabled": False}}})
        cls = FeatureRequired("business.network.enabled")
        permission = cls()
        request = factory.get("/test/")

        with pytest.raises(FeatureDisabled) as exc_info:
            permission.has_permission(request, None)

        assert exc_info.value.details["feature"] == "business.network.enabled"

    def test_distinct_from_permission_denied(self, feature_config_override):
        """feature_disabled code is distinct from permission_denied."""
        feature_config_override({"business": {"cms": {"enabled": False}}})
        cls = FeatureRequired("business.cms.enabled")
        permission = cls()
        request = factory.get("/test/")

        with pytest.raises(FeatureDisabled) as exc_info:
            permission.has_permission(request, None)

        assert exc_info.value.code == "feature_disabled"
        assert exc_info.value.code != "permission_denied"

    def test_works_with_drf_permission_classes_pattern(self, feature_config_override):
        """FeatureRequired class works with DRF's permission_classes list."""
        feature_config_override({"business": {"cms": {"enabled": True}}})
        permission_classes = [FeatureRequired("business.cms.enabled")]

        # DRF instantiates permissions via [perm() for perm in permission_classes]
        instances = [perm() for perm in permission_classes]

        assert len(instances) == 1
        request = factory.get("/test/")
        assert instances[0].has_permission(request, None) is True

    def test_multiple_feature_required_classes_independent(
        self, feature_config_override
    ):
        """Multiple FeatureRequired classes are independent."""
        feature_config_override(
            {
                "business": {
                    "cms": {"enabled": True},
                    "network": {"enabled": False},
                },
            }
        )
        cls_a = FeatureRequired("business.cms.enabled")
        cls_b = FeatureRequired("business.network.enabled")
        request = factory.get("/test/")

        # cls_a passes, cls_b raises
        assert cls_a().has_permission(request, None) is True

        with pytest.raises(FeatureDisabled):
            cls_b().has_permission(request, None)

    def test_message_attribute(self):
        """Permission class has correct message attribute."""
        cls = FeatureRequired("business.cms.enabled")

        assert cls.message == "This feature is not available"

    def test_code_attribute(self):
        """Permission class has correct code attribute."""
        cls = FeatureRequired("business.cms.enabled")

        assert cls.code == "feature_disabled"


# =============================================================================
# Test Fixtures
# =============================================================================


class TestFeatureConfigOverrideFixture:
    """Tests for the feature_config_override fixture."""

    def test_override_enables_feature(self, feature_config_override):
        """Override can enable a previously disabled feature."""
        from apps.core.feature_config import feature_config

        # Baseline has all features on (from session fixture)
        assert feature_config.is_feature_enabled("business.cms.enabled") is True

        # Override to disable
        feature_config_override({"business": {"cms": {"enabled": False}}})
        assert feature_config.is_feature_enabled("business.cms.enabled") is False

    def test_override_disables_system(self, feature_config_override):
        """Override can disable a system gate."""
        from apps.core.feature_config import feature_config

        assert feature_config.is_system_enabled("chat") is True

        feature_config_override({"systems": {"chat": False}})
        assert feature_config.is_system_enabled("chat") is False

    def test_override_deep_merges(self, feature_config_override):
        """Override deep-merges into config (doesn't replace entire sections)."""
        from apps.core.feature_config import feature_config

        # Disable only chat, keep other systems
        feature_config_override({"systems": {"chat": False}})

        assert feature_config.is_system_enabled("chat") is False
        assert feature_config.is_system_enabled("network") is True
        assert feature_config.is_system_enabled("forms") is True

    def test_override_restores_after_test(self, feature_config_override):
        """Config is restored after test (verified by checking baseline state)."""
        from apps.core.feature_config import feature_config

        # This test runs after test_override_disables_system but chat should be on
        # because fixture restores original config on teardown
        assert feature_config.is_system_enabled("chat") is True
        assert feature_config.get_org_mode() == "full"
