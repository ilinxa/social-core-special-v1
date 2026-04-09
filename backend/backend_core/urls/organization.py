"""
Organization URL routes — business + platform accounts.

Gated by org_mode: platform routes require org_mode in {full, user_and_platform},
business routes require org_mode == full.
"""

from django.urls import include, path

from apps.core.feature_config import feature_config

urlpatterns = []

if feature_config.has_platform():
    urlpatterns += [
        path(
            "api/v1/platform/",
            include("apps.organization.platform.urls", namespace="platform"),
        ),
    ]

if feature_config.has_business():
    urlpatterns += [
        path(
            "api/v1/business/",
            include("apps.organization.business.urls", namespace="business"),
        ),
    ]
