"""
Security Headers, CORS, and CSRF Tests
=======================================

Validates that security-related HTTP headers, CORS configuration,
and CSRF protections are correctly set across environments.

Tests are organized into three classes:
    - TestCORSConfiguration: CORS middleware behavior and settings
    - TestCSRFConfiguration: CSRF middleware presence and JWT bypass
    - TestSecurityHeaderSettings: Production security header defaults
"""

import importlib
import sys

import pytest
from django.conf import settings
from django.test import override_settings
from rest_framework.test import APIClient

from apps.core.utils.jwt import encode_token
from apps.users.tests.factories import UserFactory


def _load_production_settings():
    """Import the production settings module without polluting the active
    middleware stack.

    Production settings do ``from .base import *`` which gives them a
    reference to the *same* ``MIDDLEWARE`` list object used by every other
    settings module.  When production.py inserts ``whitenoise`` into that
    list, it mutates the live settings and causes subsequent tests that
    make HTTP requests to fail with ``ModuleNotFoundError: whitenoise``.

    This helper snapshots ``MIDDLEWARE`` before importing, and restores it
    afterwards so the test-time settings remain clean.
    """
    # Ensure a fresh import (not cached from a previous test run).
    mod_name = "backend_core.settings.production"
    cached = mod_name in sys.modules
    if cached:
        return sys.modules[mod_name]

    # Snapshot the mutable list referenced by base.py
    base_mod = sys.modules.get("backend_core.settings.base")
    original_middleware = list(settings.MIDDLEWARE)
    base_middleware_backup = None
    if base_mod and hasattr(base_mod, "MIDDLEWARE"):
        base_middleware_backup = list(base_mod.MIDDLEWARE)

    try:
        prod = importlib.import_module(mod_name)
        return prod
    finally:
        # Restore the base MIDDLEWARE list in-place so all references stay
        # consistent.
        if base_mod and base_middleware_backup is not None:
            base_mod.MIDDLEWARE[:] = base_middleware_backup
        settings.MIDDLEWARE = original_middleware


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------


class TestCORSConfiguration:
    """Tests for Cross-Origin Resource Sharing (CORS) middleware behaviour."""

    def test_cors_allows_credentials(self):
        """CORS_ALLOW_CREDENTIALS must be True so browsers send cookies/auth
        headers on cross-origin requests."""
        assert settings.CORS_ALLOW_CREDENTIALS is True

    def test_cors_preflight_returns_allow_methods(self):
        """An OPTIONS preflight to a valid endpoint should include the
        Access-Control-Allow-Methods header listing permitted HTTP methods."""
        client = APIClient()
        response = client.options(
            "/api/v1/auth/login/",
            HTTP_ORIGIN="http://localhost:3000",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        )
        assert "Access-Control-Allow-Methods" in response

    @override_settings(
        CORS_ALLOW_ALL_ORIGINS=False,
        CORS_ALLOWED_ORIGINS=["https://example.com"],
    )
    def test_cors_allowed_origin_reflected(self):
        """When a request arrives from an explicitly allowed origin the
        response must echo it back in Access-Control-Allow-Origin."""
        client = APIClient()
        response = client.get(
            "/api/v1/explore/businesses/",
            HTTP_ORIGIN="https://example.com",
        )
        assert response["Access-Control-Allow-Origin"] == "https://example.com"

    @override_settings(
        CORS_ALLOW_ALL_ORIGINS=False,
        CORS_ALLOWED_ORIGINS=["https://example.com"],
    )
    def test_cors_disallowed_origin_not_reflected(self):
        """Requests from origins not in the allow-list must NOT receive an
        Access-Control-Allow-Origin header."""
        client = APIClient()
        response = client.get(
            "/api/v1/explore/businesses/",
            HTTP_ORIGIN="https://evil.com",
        )
        assert "Access-Control-Allow-Origin" not in response

    def test_cors_custom_headers_allowed(self):
        """The custom x-client-type header must be present in the configured
        CORS_ALLOW_HEADERS so the frontend can send it on cross-origin
        requests without triggering a preflight rejection."""
        assert "x-client-type" in settings.CORS_ALLOW_HEADERS

    def test_cors_dev_allows_all_origins(self):
        """In the local (test) settings CORS_ALLOW_ALL_ORIGINS should be True
        so development against any frontend port works without friction."""
        assert settings.CORS_ALLOW_ALL_ORIGINS is True

    def test_cors_request_without_origin_has_no_cors_headers(self):
        """Same-origin requests (no Origin header) should not carry any CORS
        response headers since they are not needed."""
        client = APIClient()
        response = client.get("/api/v1/explore/businesses/")
        assert "Access-Control-Allow-Origin" not in response


# ---------------------------------------------------------------------------
# CSRF
# ---------------------------------------------------------------------------


class TestCSRFConfiguration:
    """Tests for CSRF middleware configuration and JWT bypass."""

    def test_csrf_middleware_in_stack(self):
        """CsrfViewMiddleware must be present in the middleware stack to
        protect session-based views against cross-site request forgery."""
        assert "django.middleware.csrf.CsrfViewMiddleware" in settings.MIDDLEWARE

    @pytest.mark.django_db
    def test_jwt_api_works_without_csrf_token(self):
        """JWT-authenticated API requests must succeed without a CSRF token.
        DRF's SessionAuthentication enforces CSRF, but our JWT auth does not,
        so POST requests with a valid Bearer token should not receive a 403."""
        user = UserFactory()
        token = encode_token(
            payload={"user_id": str(user.id), "token_type": "access"},
            expires_in=3600,
        )

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        # POST to logout — a simple authenticated endpoint that accepts POST
        response = client.post("/api/v1/auth/logout/")
        # Any status other than 403 proves CSRF was not enforced
        assert response.status_code != 403

    def test_csrf_cookie_secure_in_production(self):
        """Production settings must mark the CSRF cookie as Secure so it is
        never transmitted over plain HTTP."""
        prod = _load_production_settings()
        assert prod.CSRF_COOKIE_SECURE is True

    def test_ses_webhook_csrf_exempt_exists(self):
        """The SES webhook view must exist and be callable.  It is decorated
        with @csrf_exempt because AWS SNS cannot supply a Django CSRF token."""
        from apps.email.webhooks import ses_webhook

        assert callable(ses_webhook)
        # csrf_exempt wraps the view and sets csrf_exempt = True on it
        assert getattr(ses_webhook, "csrf_exempt", False) is True


# ---------------------------------------------------------------------------
# Security Header Settings (production)
# ---------------------------------------------------------------------------


class TestSecurityHeaderSettings:
    """Verify that production settings enable critical security headers."""

    def test_production_x_frame_options(self):
        """X-Frame-Options must be DENY to prevent click-jacking by
        disallowing the site from being rendered in any iframe."""
        prod = _load_production_settings()
        assert prod.X_FRAME_OPTIONS == "DENY"

    def test_production_content_type_nosniff(self):
        """SECURE_CONTENT_TYPE_NOSNIFF must be True so Django adds
        X-Content-Type-Options: nosniff, preventing MIME-type sniffing."""
        prod = _load_production_settings()
        assert prod.SECURE_CONTENT_TYPE_NOSNIFF is True

    def test_production_ssl_redirect(self):
        """SECURE_SSL_REDIRECT should default to True in production so all
        HTTP requests are redirected to HTTPS."""
        prod = _load_production_settings()
        assert hasattr(prod, "SECURE_SSL_REDIRECT")
        # Default (no env override) is True
        assert prod.SECURE_SSL_REDIRECT is True

    def test_production_hsts_enabled(self):
        """HSTS must be configured with a 1-year max-age (31536000 seconds)
        to instruct browsers to always use HTTPS."""
        prod = _load_production_settings()
        assert prod.SECURE_HSTS_SECONDS == 31536000
