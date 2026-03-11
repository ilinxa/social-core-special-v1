# apps/email/tests/conftest.py
"""
Pytest configuration and fixtures for Email app tests.

These fixtures are available to all tests in the email app.
"""

import pytest
from rest_framework.test import APIClient

from apps.users.tests.factories import UserFactory, VerifiedUserFactory
from apps.email.tests.factories import (
    EmailTemplateFactory,
    InactiveEmailTemplateFactory,
    ArchivedEmailTemplateFactory,
    EmailLogFactory,
    SentEmailLogFactory,
    DeliveredEmailLogFactory,
    FailedEmailLogFactory,
    BouncedEmailLogFactory,
    ComplainedEmailLogFactory,
    QueuedEmailLogFactory,
)


# =============================================================================
# API CLIENT FIXTURES
# =============================================================================


@pytest.fixture
def api_client():
    """Return an unauthenticated DRF APIClient instance."""
    return APIClient()


# =============================================================================
# USER FIXTURES
# =============================================================================


@pytest.fixture
def user(db):
    """Create and return a regular test user."""
    return UserFactory()


@pytest.fixture
def verified_user(db):
    """Create and return a verified test user."""
    return VerifiedUserFactory()


# =============================================================================
# FACTORY FIXTURES
# =============================================================================


@pytest.fixture
def email_template_factory(db):
    """Return the EmailTemplateFactory."""
    return EmailTemplateFactory


@pytest.fixture
def email_log_factory(db):
    """Return the EmailLogFactory."""
    return EmailLogFactory


# =============================================================================
# TEMPLATE FIXTURES
# =============================================================================


@pytest.fixture
def welcome_template(db):
    """Create a 'welcome' email template with variables."""
    return EmailTemplateFactory(
        name="welcome",
        subject="Welcome {{ user_name }}!",
        html_body="<h1>Welcome {{ user_name }}</h1><p>Email: {{ email }}</p>",
        text_body="Welcome {{ user_name }}. Email: {{ email }}",
        variables={
            "user_name": {"type": "string", "required": True},
            "email": {"type": "string", "required": True},
        },
        category="auth",
    )


@pytest.fixture
def password_reset_template(db):
    """Create a 'password_reset' email template."""
    return EmailTemplateFactory(
        name="password_reset",
        subject="Reset your password",
        html_body="<p>Click <a href='{{ reset_link }}'>here</a> to reset.</p>",
        text_body="Reset link: {{ reset_link }}",
        variables={
            "reset_link": {"type": "string", "required": True},
        },
        category="auth",
    )


# =============================================================================
# URL FIXTURES
# =============================================================================


@pytest.fixture
def ses_webhook_url():
    """Return the SES webhook endpoint URL."""
    return "/api/v1/email/webhooks/ses/"
