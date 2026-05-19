"""
Root-level pytest configuration and shared fixtures.

This file is automatically loaded by pytest for ALL tests in the project
(both apps/ and tests/ directories). Fixtures defined here are globally
available.

Note: App-specific fixtures are defined in each app's own conftest.py.
Integration test fixtures are in tests/conftest.py.
"""

import copy

import pytest
from rest_framework.test import APIClient

# =============================================================================
# Feature Gate Configuration
# =============================================================================

# Full-feature config for test suite baseline — all systems ON, all features ON.
# Matches the structure of deployment_config_full_example.json.
_FULL_FEATURE_CONFIG = {
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
    "limits": {
        "max_users": 0,
        "max_businesses": 0,
        "max_businesses_per_user": 0,
    },
    "user": {
        "can_create_business": True,
        "can_be_member": True,
        "profile_visibility": True,
        "profile_default_public": True,
        "max_memberships": 0,
        "forms": True,
        "network": {
            "enabled": True,
            "connections": True,
            "follows": True,
            "max_connections": 0,
            "max_follows": 0,
        },
        "chat": {
            "enabled": True,
            "group": True,
            "file_sharing": True,
            "reactions": True,
            "search": True,
            "max_groups": 0,
        },
        "explore": {
            "can_explore": True,
            "search_users": True,
            "search_businesses": True,
            "is_discoverable": True,
        },
        "transactions": {
            "enabled": True,
            "max_pending": 0,
        },
        "notifications": {
            "enabled": True,
        },
    },
    "business": {
        "members": {
            "enabled": True,
            "invitations": True,
            "requests": True,
            "custom_roles": True,
            "max_members": 0,
            "max_roles": 0,
        },
        "chat": {
            "enabled": True,
            "entity": True,
            "group": True,
            "file_sharing": True,
            "max_groups": 0,
        },
        "network": {
            "enabled": True,
            "followers": True,
            "connections": True,
            "max_followers": 0,
            "max_connections": 0,
        },
        "forms": {
            "enabled": True,
            "transaction_mapping": True,
            "max_forms": 0,
        },
        "cms": {
            "enabled": True,
            "activation_request": True,
            "max_sites": 0,
            "max_pages_per_site": 0,
            "max_api_keys_per_site": 0,
            "max_active_block_templates": 0,
            "max_active_section_templates": 0,
            "max_media_files": 0,
            "max_media_file_size_mb": 10,
            "api_key_rate_limit": 60,
        },
        "profile_visibility": True,
        "profile_default_public": True,
        "transactions": {
            "enabled": True,
            "verification": True,
            "ownership_transfer": True,
        },
        "notifications": {
            "enabled": True,
        },
    },
    "platform": {
        "members": {
            "enabled": True,
            "invitations": True,
            "requests": True,
            "custom_roles": True,
            "max_members": 0,
            "max_roles": 0,
        },
        "chat": {
            "enabled": True,
            "entity": True,
        },
        "network": True,
        "forms": True,
        "cms": True,
        "governance": {
            "business_approval": True,
            "business_verification": True,
            "approved_creators": True,
            "global_moderation": True,
        },
        "transactions": {
            "ownership_transfer": True,
        },
        "notifications": {
            "enabled": True,
        },
    },
    "chat": {
        "messages": {
            "max_length": 5000,
            "edit_window_minutes": 15,
            "preview_length": 200,
        },
        "groups": {"max_participants": 100},
        "requests": {"enabled": True, "max_messages": 3, "expiry_days": 30},
        "attachments": {
            "max_per_message": 10,
            "max_image_size_mb": 10,
            "allowed_image_types": ["jpeg", "png", "gif", "webp"],
        },
        "rate_limits": {
            "messages_per_minute": 30,
            "conversations_per_hour": 5,
            "requests_per_hour": 10,
        },
        "presence": {"ttl_seconds": 30, "heartbeat_interval_seconds": 20},
        "reactions": {"types": ["like", "heart", "laugh", "wow", "sad", "angry"]},
    },
    "cms": {
        "max_versions_per_placement": 50,
        "max_folder_depth": 5,
        "version_throttle_seconds": 30,
        "api_key_rate_limit": 60,
        "allowed_media_types": [
            "jpeg",
            "png",
            "gif",
            "webp",
            "svg",
            "pdf",
            "mp4",
            "webm",
            "mp3",
            "ogg",
        ],
    },
    "transaction": {
        "default_expiry_days": 30,
        "resubmission_cooldown_days": 7,
        "expiration_reminder_hours": 48,
    },
    "network": {
        "follow_approval_required": False,
        "connection_approval_required": True,
    },
    "auth": {
        "signup": {"email_password": True, "email_verification_required": True},
        "verification": {"method": "both", "code_length": 6, "expiry_minutes": 15},
        "password_reset": {"enabled": True, "method": "link", "expiry_minutes": 60},
        "sessions": {
            "max_per_user": 5,
            "access_token_lifetime": 900,
            "refresh_token_lifetime": 604800,
        },
        "lockout": {"max_failed_attempts": 10, "duration": 900},
        "oauth": {"google": True, "apple": True, "state_ttl": 600},
        "governance": {
            "token_lifetime": 1800,
            "allow_password_stepup": True,
            "allow_email_otp_stepup": True,
            "otp_code_length": 6,
            "otp_expiry_seconds": 300,
            "otp_max_attempts": 5,
            "lockout_shared": True,
        },
    },
    "notifications": {
        "log_retention_days": 90,
        "email_enabled": True,
        "push_enabled": True,
        "sms_enabled": True,
    },
    "explore": {
        "results_per_page": 20,
        "min_search_length": 2,
        "suggested_tags_enabled": True,
    },
    "infra": {
        "audit_log_retention_days": 730,
        "email_log_retention_days": 90,
    },
}


@pytest.hookimpl(trylast=True)
def pytest_configure(config):
    """Set feature config BEFORE test module collection.

    Test modules that import from ``backend_core.urls`` trigger URL pattern
    assembly at import time.  That assembly reads ``feature_config`` to decide
    which URL groups to include.  Because test modules are imported during
    collection (before session fixtures run), we must set the config here
    in ``pytest_configure`` (which runs after pytest-django configures Django
    but before collection).  ``trylast=True`` ensures Django is ready.
    """
    from apps.core.feature_config import feature_config

    feature_config._config = _FULL_FEATURE_CONFIG
    feature_config._loaded = True


@pytest.fixture(autouse=True, scope="session")
def _enable_all_features():
    """Enable all features for the test suite baseline.

    Ensures existing 4000+ tests pass unchanged by setting the feature config
    to an all-enabled state. Individual tests use feature_config_override()
    to test disabled scenarios.

    Also handles teardown (resetting config after the session).
    """
    from apps.core.feature_config import feature_config

    # Config is already set by pytest_configure — this is for safety/teardown.
    feature_config._config = _FULL_FEATURE_CONFIG
    feature_config._loaded = True
    yield
    feature_config._config = {}
    feature_config._loaded = False


def _deep_merge(base: dict, overrides: dict) -> dict:
    """Recursively merge overrides into base dict."""
    result = base.copy()
    for key, value in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


@pytest.fixture
def feature_config_override():
    """Override feature config for individual tests.

    Returns a callable that deep-merges overrides into the current config.
    Restores the original config after the test.

    Usage::

        def test_feature_off(feature_config_override):
            feature_config_override({"systems": {"chat": False}})
            # chat is now off, all other features still on from baseline
    """
    from apps.core.feature_config import feature_config

    original = copy.deepcopy(feature_config._config)

    def _override(overrides: dict):
        feature_config._config = _deep_merge(original, overrides)

    yield _override
    feature_config._config = original


# =============================================================================
# Shared API Client + User Fixtures (hoisted from per-app conftests — PR9)
# =============================================================================


@pytest.fixture
def api_client():
    """Return an unauthenticated DRF APIClient instance."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create and return a regular test user.

    Apps needing a specialized ``user`` (e.g. ``is_verified=True`` or a custom
    email) MUST override this fixture in their own ``conftest.py``. Currently
    overridden by: chat, explore, network, rbac (``is_verified=True``);
    forms, transaction (custom emails).
    """
    from apps.users.tests.factories import UserFactory

    return UserFactory()


@pytest.fixture
def authenticated_client(api_client, user):
    """Return an APIClient authenticated as a regular user via ``force_authenticate``.

    The ``explore`` app overrides this with a real JWT-login flow because its
    tests exercise the full authentication path.
    """
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def verified_user(db):
    """Create and return a verified test user."""
    from apps.users.tests.factories import VerifiedUserFactory

    return VerifiedUserFactory()


@pytest.fixture
def staff_user(db):
    """Create and return a staff test user."""
    from apps.users.tests.factories import StaffUserFactory

    return StaffUserFactory()


@pytest.fixture
def superuser(db):
    """Create and return a superuser."""
    from apps.users.tests.factories import SuperuserFactory

    return SuperuserFactory()
