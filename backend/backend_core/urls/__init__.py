"""
URL Coordinator — reads feature config, assembles urlpatterns.

This package replaces the monolithic `backend_core/urls.py`. Each URL group
file contains routes for a single system. The coordinator imports only the
groups that are enabled in the deployment config.

Disabled groups are never imported → their app URL modules never load →
Django returns natural 404 for any path in a disabled system.

ROOT_URLCONF = "backend_core.urls" still works — Python resolves it to
this __init__.py.
"""

from django.conf import settings

from apps.core.feature_config import feature_config

from .base import urlpatterns as base_patterns

# ── Decision layer (testable as pure data) ──────────────────────────────

GATED_GROUPS = {
    "organization": lambda fc: fc.has_business() or fc.has_platform(),
    "transaction": lambda fc: fc.is_system_enabled("transaction"),
    "forms": lambda fc: fc.is_system_enabled("forms"),
    "cms": lambda fc: fc.is_system_enabled("cms"),
    "explore": lambda fc: fc.is_system_enabled("explore"),
    "network": lambda fc: fc.is_system_enabled("network"),
    "chat": lambda fc: fc.is_system_enabled("chat"),
    "notifications": lambda fc: fc.is_system_enabled("notifications"),
    "governance": lambda fc: fc.is_system_enabled("governance"),
}


def get_enabled_groups(fc=None):
    """Return the set of enabled URL group names.

    Accepts an optional FeatureConfig instance for testing.
    Uses the singleton when called without arguments.
    """
    fc = fc or feature_config
    return {name for name, check in GATED_GROUPS.items() if check(fc)}


# ── Assembly layer (runs once at startup) ───────────────────────────────

urlpatterns = list(base_patterns)  # copy to avoid mutating base module
_enabled = get_enabled_groups()

if "organization" in _enabled:
    from .organization import urlpatterns as org_patterns

    urlpatterns += org_patterns

if "transaction" in _enabled:
    from .transaction import urlpatterns as txn_patterns

    urlpatterns += txn_patterns

if "forms" in _enabled:
    from .forms import urlpatterns as forms_patterns

    urlpatterns += forms_patterns

if "cms" in _enabled:
    from .cms import urlpatterns as cms_patterns

    urlpatterns += cms_patterns

if "explore" in _enabled:
    from .explore import urlpatterns as explore_patterns

    urlpatterns += explore_patterns

if "network" in _enabled:
    from .network import urlpatterns as network_patterns

    urlpatterns += network_patterns

if "chat" in _enabled:
    from .chat import urlpatterns as chat_patterns

    urlpatterns += chat_patterns

if "notifications" in _enabled:
    from .notifications import urlpatterns as notif_patterns

    urlpatterns += notif_patterns

if "governance" in _enabled:
    from .governance import urlpatterns as gov_patterns

    urlpatterns += gov_patterns

# Dev-only routes (schema, swagger, redoc, silk, media serving)
if settings.DEBUG:
    from .dev import urlpatterns as dev_patterns

    urlpatterns += dev_patterns
