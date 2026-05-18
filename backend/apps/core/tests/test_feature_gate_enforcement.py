"""
Feature Gate Enforcement Tests (MAJOR #1 audit follow-up).

Verifies the per-feature FG gates added for auth signup, OAuth providers,
password reset, governance endpoints, and the email log retention VG.

Each test disables a single gate via ``feature_config_override`` and confirms
the corresponding endpoint returns ``feature_disabled`` (HTTP 403) or that the
service-layer behavior honors the deployment config value.
"""

from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from apps.users.tests.factories import UserFactory


def _assert_feature_disabled(response, feature_path):
    """Assert response is 403 with feature_disabled code and correct path."""
    assert response.status_code == 403, response.data
    assert response.data["error"]["code"] == "feature_disabled"
    assert response.data["error"]["details"]["feature"] == feature_path


# =============================================================================
# Auth — Signup / OAuth / Password Reset Gates (AllowAny views — gate fires
# without authentication)
# =============================================================================


@pytest.mark.django_db
class TestAuthSignupGate:
    """auth.signup.email_password → RegisterView."""

    def test_signup_email_password_disabled(self, feature_config_override):
        feature_config_override({"auth": {"signup": {"email_password": False}}})
        client = APIClient()
        response = client.post(
            "/api/v1/auth/register/",
            {
                "email": "new@example.com",
                "password": "StrongPassw0rd!",
                "username": "newuser",
            },
            format="json",
        )
        _assert_feature_disabled(response, "auth.signup.email_password")


@pytest.mark.django_db
class TestAuthOAuthGoogleGate:
    """auth.oauth.google → GoogleOAuthView."""

    def test_oauth_google_disabled(self, feature_config_override):
        feature_config_override({"auth": {"oauth": {"google": False}}})
        client = APIClient()
        response = client.get("/api/v1/auth/oauth/google/")
        _assert_feature_disabled(response, "auth.oauth.google")


@pytest.mark.django_db
class TestAuthOAuthAppleGate:
    """auth.oauth.apple → AppleOAuthView."""

    def test_oauth_apple_disabled(self, feature_config_override):
        feature_config_override({"auth": {"oauth": {"apple": False}}})
        client = APIClient()
        response = client.get("/api/v1/auth/oauth/apple/")
        _assert_feature_disabled(response, "auth.oauth.apple")


@pytest.mark.django_db
class TestAuthPasswordResetGate:
    """auth.password_reset.enabled → PasswordResetRequestView."""

    def test_password_reset_disabled(self, feature_config_override):
        feature_config_override({"auth": {"password_reset": {"enabled": False}}})
        client = APIClient()
        response = client.post(
            "/api/v1/auth/password/reset/",
            {"email": "user@example.com"},
            format="json",
        )
        _assert_feature_disabled(response, "auth.password_reset.enabled")


# =============================================================================
# Governance Gates — require authenticated user with governance token bypassing
# the GovernanceTokenRequired check so the FeatureRequired gate is reached.
# =============================================================================


GOV_TOKEN_PAYLOAD = {"token_scope": "governance"}


@pytest.fixture
def gov_client(db):
    """Authenticated client with a governance-scoped token.

    Bypasses ``GovernanceAuthService.has_any_global_permission`` so the request
    survives ``GovernanceTokenRequired`` and the ``FeatureRequired`` gate is the
    permission check that fires.
    """
    user = UserFactory()
    client = APIClient()
    client.force_authenticate(user=user, token=GOV_TOKEN_PAYLOAD)
    with patch(
        "apps.auth.services.governance_service.GovernanceAuthService.has_any_global_permission",
        return_value=True,
    ):
        yield client


@pytest.mark.django_db
class TestGovernanceBusinessApprovalGate:
    """platform.governance.business_approval → GovernanceBusiness* views."""

    def test_business_approval_disabled(self, gov_client, feature_config_override):
        feature_config_override(
            {"platform": {"governance": {"business_approval": False}}}
        )
        response = gov_client.get("/api/v1/governance/businesses/")
        _assert_feature_disabled(response, "platform.governance.business_approval")


@pytest.mark.django_db
class TestGovernanceBusinessVerificationGate:
    """platform.governance.business_verification → GovernanceVerificationListView."""

    def test_business_verification_disabled(self, gov_client, feature_config_override):
        feature_config_override(
            {"platform": {"governance": {"business_verification": False}}}
        )
        response = gov_client.get("/api/v1/governance/verification/")
        _assert_feature_disabled(response, "platform.governance.business_verification")


@pytest.mark.django_db
class TestGovernanceApprovedCreatorsGate:
    """platform.governance.approved_creators → GovernanceApprovedCreatorsView."""

    def test_approved_creators_disabled(self, gov_client, feature_config_override):
        feature_config_override(
            {"platform": {"governance": {"approved_creators": False}}}
        )
        response = gov_client.get("/api/v1/governance/approved-creators/")
        _assert_feature_disabled(response, "platform.governance.approved_creators")


@pytest.mark.django_db
class TestGovernanceGlobalModerationGate:
    """platform.governance.global_moderation → GovernanceMember* + GovernanceTransactionListView."""

    def test_global_moderation_disabled_members(
        self, gov_client, feature_config_override
    ):
        feature_config_override(
            {"platform": {"governance": {"global_moderation": False}}}
        )
        response = gov_client.get("/api/v1/governance/members/")
        _assert_feature_disabled(response, "platform.governance.global_moderation")

    def test_global_moderation_disabled_transactions(
        self, gov_client, feature_config_override
    ):
        feature_config_override(
            {"platform": {"governance": {"global_moderation": False}}}
        )
        response = gov_client.get("/api/v1/governance/transactions/")
        _assert_feature_disabled(response, "platform.governance.global_moderation")


# =============================================================================
# Infra — Email Log Retention (VG read from feature_config)
# =============================================================================


@pytest.mark.django_db
class TestEmailLogRetentionValueGate:
    """infra.email_log_retention_days → cleanup_old_email_logs reads via feature_config."""

    def test_cleanup_reads_retention_from_feature_config(self, feature_config_override):
        from datetime import timedelta

        from django.utils import timezone

        from apps.email.models import EmailLog
        from apps.email.tasks import cleanup_old_email_logs
        from apps.email.tests.factories import EmailLogFactory

        feature_config_override({"infra": {"email_log_retention_days": 7}})

        # Beyond 7-day retention — should be deleted.
        log_old = EmailLogFactory()
        EmailLog.objects.filter(id=log_old.id).update(
            created_at=timezone.now() - timedelta(days=10)
        )

        # Within 7-day retention — should survive.
        log_recent = EmailLogFactory()
        EmailLog.objects.filter(id=log_recent.id).update(
            created_at=timezone.now() - timedelta(days=3)
        )

        cleanup_old_email_logs()

        assert not EmailLog.objects.filter(id=log_old.id).exists()
        assert EmailLog.objects.filter(id=log_recent.id).exists()
