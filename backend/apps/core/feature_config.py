"""
Feature Configuration
=====================
Deployment-level feature gate configuration loader.

Reads a JSON config file once and provides typed access via dot-notation paths.
Missing file or missing keys default to the most restrictive state (minimal deployment).

Three gate levels:
    SG (System Gate):  is_system_enabled()  — controls URL registration at startup
    FG (Feature Gate):  is_feature_enabled() — controls module/sub-feature access at runtime
    VG (Value Gate):   get_limit() / get_value() — controls numeric limits and config values

Usage:
    from apps.core.feature_config import feature_config

    if feature_config.is_system_enabled("chat"):
        ...
    if feature_config.is_feature_enabled("business.network.enabled"):
        ...
    limit = feature_config.get_limit("business.members.max_members", default=1)
"""

import json
from pathlib import Path
from typing import Any


def _logger():
    """Return a structlog BoundLogger for this module.

    Imported lazily because ``feature_config`` is loaded during Django URL
    assembly (see ``backend/conftest.py``), which can run before
    ``CoreConfig.ready()`` has called ``configure_logging()``. The lazy
    import here defers the structlog initialization until the first log
    emission, by which time Django startup is complete.
    """
    from apps.core.observability import get_logger

    return get_logger(__name__)


class FeatureConfig:
    """Singleton deployment feature configuration.

    Lazy-loaded from a JSON config file. Missing file or missing keys
    default to the most restrictive state (minimal deployment):
    all systems OFF, org_mode=user_only, all FG gates OFF.
    """

    def __init__(self):
        self._config: dict = {}
        self._loaded = False

    def _ensure_loaded(self):
        """Load config on first access (lazy init)."""
        if not self._loaded:
            from django.conf import settings

            path = getattr(settings, "DEPLOYMENT_CONFIG_PATH", None)
            if path:
                self._config = self._load_config(path)
            self._loaded = True

    @staticmethod
    def _load_config(path: str) -> dict:
        """Read JSON config file. Returns empty dict if missing or invalid."""
        config_path = Path(path)
        if not config_path.exists():
            _logger().info(
                "feature_config.missing",
                path=str(path),
                note="using minimal defaults",
            )
            return {}
        try:
            with open(config_path) as f:
                data = json.load(f)
            if not isinstance(data, dict):
                _logger().warning(
                    "feature_config.invalid_shape",
                    path=str(path),
                    note="not a JSON object; using minimal defaults",
                )
                return {}
            _logger().info("feature_config.loaded", path=str(path))
            return data
        except (json.JSONDecodeError, OSError) as e:
            _logger().warning(
                "feature_config.read_failed",
                path=str(path),
                error=str(e),
                note="using minimal defaults",
            )
            return {}

    def get(self, dotted_key: str, default: Any = None) -> Any:
        """Traverse nested config via dot-notation. Returns default if any key missing."""
        self._ensure_loaded()
        keys = dotted_key.split(".")
        current = self._config
        for key in keys:
            if not isinstance(current, dict):
                return default
            current = current.get(key)
            if current is None:
                return default
        return current

    # ── SG: System Gates ──────────────────────────────────────────

    def is_system_enabled(self, name: str) -> bool:
        """Check if a top-level system is enabled. Default: False (minimal)."""
        return bool(self.get(f"systems.{name}", False))

    def get_org_mode(self) -> str:
        """Get organization mode. Default: 'user_only' (minimal)."""
        return self.get("org_mode", "user_only")

    def has_business(self) -> bool:
        """True if org_mode allows business accounts (org_mode == 'full')."""
        return self.get_org_mode() == "full"

    def has_platform(self) -> bool:
        """True if org_mode allows platform accounts (org_mode in {'full', 'user_and_platform'})."""
        return self.get_org_mode() in ("full", "user_and_platform")

    # ── FG: Feature Gates ─────────────────────────────────────────

    def is_feature_enabled(self, path: str) -> bool:
        """Check if a feature path is enabled. Default: False (minimal)."""
        return bool(self.get(path, False))

    # ── VG: Value Gates ───────────────────────────────────────────

    def get_limit(self, path: str, default: int = 0) -> int:
        """Get a numeric limit. 0 = unlimited."""
        value = self.get(path, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def get_value(self, path: str, default: Any = None) -> Any:
        """Get a generic config value."""
        return self.get(path, default)

    def check_limit(
        self, path: str, current: int, *, rule: str, resource: str = ""
    ) -> None:
        """VG limit check: raise BusinessRuleViolation if current >= limit. 0 = unlimited."""
        limit = self.get_limit(path, default=0)
        if limit > 0 and current >= limit:
            from apps.core.exceptions import BusinessRuleViolation

            raise BusinessRuleViolation(
                message=(
                    f"{resource} limit reached ({limit})"
                    if resource
                    else f"Limit reached ({limit})"
                ),
                rule=rule,
                limit=limit,
                current=current,
            )

    @staticmethod
    def effective_limit(config_limit: int, model_limit: int) -> int:
        """Return the tighter of two limits. 0 means unlimited in both."""
        if config_limit == 0 and model_limit == 0:
            return 0  # both unlimited
        if config_limit == 0:
            return model_limit  # config unlimited, model sets limit
        if model_limit == 0:
            return config_limit  # model unlimited, config sets limit
        return min(config_limit, model_limit)  # both set, take tighter

    # ── Management ────────────────────────────────────────────────

    def reload(self):
        """Re-read config file. For FG/VG runtime changes (not SG — URLs fixed at startup)."""
        self._loaded = False
        self._ensure_loaded()


# Module-level singleton
feature_config = FeatureConfig()
