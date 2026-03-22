"""
Tests for Notification app views.
==================================
Covers PreferencesView, PreferenceDetailView, NotificationHistoryView,
and ConfigurableTypesView endpoints.
"""

from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status

from apps.notifications.models import NotificationLog, NotificationPreference
from apps.notifications.tests.factories import (
    FailedNotificationLogFactory,
    NotificationLogFactory,
    NotificationPreferenceFactory,
    SentNotificationLogFactory,
)
from apps.users.tests.factories import UserFactory

# =============================================================================
# PREFERENCES LIST VIEW
# =============================================================================


@pytest.mark.django_db
class TestPreferencesListView:
    """Tests for GET /api/v1/notifications/preferences/."""

    def test_unauthenticated_returns_401(self, api_client, preferences_url):
        """Unauthenticated request to preferences list returns 401."""
        response = api_client.get(preferences_url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_returns_preferences(
        self, authenticated_client, preferences_url
    ):
        """Authenticated request returns 200 with preference data."""
        response = authenticated_client.get(preferences_url)

        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, dict)

    def test_response_contains_all_types(self, authenticated_client, preferences_url):
        """Response contains all notification types across all categories."""
        response = authenticated_client.get(preferences_url)

        assert response.status_code == status.HTTP_200_OK

        # Flatten all types from all categories
        all_types = []
        for category_prefs in response.data.values():
            for pref in category_prefs:
                all_types.append(pref["notification_type"])

        # All defined notification types should be present
        expected_types = {
            "verify_email",
            "welcome",
            "password_reset",
            "password_changed",
            "new_login",
            "suspicious_activity",
            "newsletter",
            "promotions",
            "transaction_invitation_received",
            "transaction_accepted",
            "transaction_denied",
            "transaction_cancelled",
            "transaction_expired",
            "transaction_expiring_soon",
            "transaction_info_requested",
            "transaction_resubmitted",
            "transaction_pending_approval",
            # Social / Network
            "new_follower",
            "follow_request_received",
            "follow_request_accepted",
            "connection_request_received",
            "connection_accepted",
            # Social / Chat
            "chat_message_received",
            "chat_request_received",
            "chat_request_accepted",
            "chat_group_added",
            "chat_reaction_received",
        }
        assert set(all_types) == expected_types

    def test_response_includes_channel_settings(
        self, authenticated_client, preferences_url
    ):
        """Each preference in the response includes email, push, and sms enabled fields."""
        response = authenticated_client.get(preferences_url)

        assert response.status_code == status.HTTP_200_OK

        for category_prefs in response.data.values():
            for pref in category_prefs:
                assert "email_enabled" in pref
                assert "push_enabled" in pref
                assert "sms_enabled" in pref


# =============================================================================
# PREFERENCE DETAIL VIEW
# =============================================================================


@pytest.mark.django_db
class TestPreferenceDetailView:
    """Tests for GET/PATCH/DELETE /api/v1/notifications/preferences/<type>/."""

    def test_get_preference_returns_200(
        self, authenticated_client, preference_detail_url
    ):
        """GET for an existing notification type returns 200 with preference data."""
        response = authenticated_client.get(preference_detail_url("new_login"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["notification_type"] == "new_login"
        assert response.data["display_name"] == "New Login Alert"
        assert "email_enabled" in response.data
        assert "push_enabled" in response.data
        assert "sms_enabled" in response.data

    def test_get_preference_unknown_type_returns_404(
        self, authenticated_client, preference_detail_url
    ):
        """GET for a nonexistent notification type returns 404."""
        response = authenticated_client.get(preference_detail_url("nonexistent_type"))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_preference_unauthenticated_returns_401(
        self, api_client, preference_detail_url
    ):
        """Unauthenticated GET on preference detail returns 401."""
        response = api_client.get(preference_detail_url("new_login"))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("apps.notifications.services.preference_service.AuditService.log")
    @patch(
        "apps.notifications.services.preference_service.AuditLog",
        new_callable=MagicMock,
    )
    def test_patch_updates_preference(
        self,
        mock_audit_log_model,
        mock_audit_log,
        authenticated_client,
        preference_detail_url,
    ):
        """PATCH with email_enabled=false updates the preference and returns 200."""
        response = authenticated_client.patch(
            preference_detail_url("new_login"),
            data={"email_enabled": False},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["email_enabled"] is False
        assert response.data["notification_type"] == "new_login"

    @patch("apps.notifications.services.preference_service.AuditService.log")
    @patch(
        "apps.notifications.services.preference_service.AuditLog",
        new_callable=MagicMock,
    )
    def test_patch_non_configurable_returns_400(
        self,
        mock_audit_log_model,
        mock_audit_log,
        authenticated_client,
        preference_detail_url,
    ):
        """PATCH on a non-configurable type like 'verify_email' returns 400."""
        response = authenticated_client.patch(
            preference_detail_url("verify_email"),
            data={"email_enabled": False},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("apps.notifications.services.preference_service.AuditService.log")
    @patch(
        "apps.notifications.services.preference_service.AuditLog",
        new_callable=MagicMock,
    )
    def test_patch_no_fields_returns_400(
        self,
        mock_audit_log_model,
        mock_audit_log,
        authenticated_client,
        preference_detail_url,
    ):
        """PATCH with no channel fields returns 400 due to serializer validation."""
        response = authenticated_client.patch(
            preference_detail_url("new_login"),
            data={},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("apps.notifications.services.preference_service.AuditService.log")
    @patch(
        "apps.notifications.services.preference_service.AuditLog",
        new_callable=MagicMock,
    )
    def test_patch_unknown_type_returns_404(
        self,
        mock_audit_log_model,
        mock_audit_log,
        authenticated_client,
        preference_detail_url,
    ):
        """PATCH on a nonexistent notification type returns 404."""
        response = authenticated_client.patch(
            preference_detail_url("nonexistent_type"),
            data={"email_enabled": False},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_resets_preference(
        self, authenticated_client, preference_detail_url, user
    ):
        """DELETE resets the preference to defaults and returns 204."""
        # Create an override preference first
        NotificationPreferenceFactory(
            user=user,
            notification_type="new_login",
            email_enabled=False,
        )
        assert NotificationPreference.objects.filter(
            user=user, notification_type="new_login"
        ).exists()

        response = authenticated_client.delete(preference_detail_url("new_login"))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        # The override record should be deleted
        assert not NotificationPreference.objects.filter(
            user=user, notification_type="new_login"
        ).exists()

    def test_delete_unknown_type_returns_404(
        self, authenticated_client, preference_detail_url
    ):
        """DELETE on a nonexistent notification type returns 404."""
        response = authenticated_client.delete(
            preference_detail_url("nonexistent_type")
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# NOTIFICATION HISTORY VIEW
# =============================================================================


@pytest.mark.django_db
class TestNotificationHistoryView:
    """Tests for GET /api/v1/notifications/history/."""

    def test_unauthenticated_returns_401(self, api_client, history_url):
        """Unauthenticated request to notification history returns 401."""
        response = api_client.get(history_url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_returns_history(
        self, authenticated_client, history_url, user
    ):
        """Authenticated request returns 200 with notification history."""
        NotificationLogFactory(user=user, notification_type="welcome")
        SentNotificationLogFactory(user=user, notification_type="new_login")

        response = authenticated_client.get(history_url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["notifications"]) == 2

    def test_response_format(self, authenticated_client, history_url, user):
        """Response has {notifications: [...], count: int} structure."""
        NotificationLogFactory(user=user)

        response = authenticated_client.get(history_url)

        assert response.status_code == status.HTTP_200_OK
        assert "notifications" in response.data
        assert "count" in response.data
        assert isinstance(response.data["notifications"], list)
        assert isinstance(response.data["count"], int)
        assert response.data["count"] == len(response.data["notifications"])

    def test_filters_by_notification_type(
        self, authenticated_client, history_url, user
    ):
        """Query param notification_type filters to only matching logs."""
        NotificationLogFactory(user=user, notification_type="welcome")
        NotificationLogFactory(user=user, notification_type="new_login")
        NotificationLogFactory(user=user, notification_type="welcome")

        response = authenticated_client.get(
            history_url, {"notification_type": "welcome"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2
        for notification in response.data["notifications"]:
            assert notification["notification_type"] == "welcome"

    def test_filters_by_status(self, authenticated_client, history_url, user):
        """Query param status filters to only logs with that status."""
        SentNotificationLogFactory(user=user)
        SentNotificationLogFactory(user=user)
        FailedNotificationLogFactory(user=user)
        NotificationLogFactory(user=user)  # pending

        response = authenticated_client.get(history_url, {"status": "sent"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2
        for notification in response.data["notifications"]:
            assert notification["status"] == "sent"

    def test_respects_limit(self, authenticated_client, history_url, user):
        """Query param limit caps the number of returned results."""
        for _ in range(5):
            NotificationLogFactory(user=user)

        response = authenticated_client.get(history_url, {"limit": 2})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] <= 2

    def test_only_returns_own_logs(self, authenticated_client, history_url, user):
        """User only sees their own notification logs, not other users' logs."""
        other_user = UserFactory()

        NotificationLogFactory(user=user, notification_type="welcome")
        NotificationLogFactory(user=user, notification_type="new_login")
        NotificationLogFactory(user=other_user, notification_type="welcome")
        NotificationLogFactory(user=other_user, notification_type="newsletter")
        NotificationLogFactory(user=other_user, notification_type="promotions")

        response = authenticated_client.get(history_url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2


# =============================================================================
# CONFIGURABLE TYPES VIEW
# =============================================================================


@pytest.mark.django_db
class TestConfigurableTypesView:
    """Tests for GET /api/v1/notifications/types/."""

    def test_unauthenticated_returns_401(self, api_client, configurable_types_url):
        """Unauthenticated request to configurable types returns 401."""
        response = api_client.get(configurable_types_url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_returns_types(
        self, authenticated_client, configurable_types_url
    ):
        """Authenticated request returns 200 with types and count."""
        response = authenticated_client.get(configurable_types_url)

        assert response.status_code == status.HTTP_200_OK
        assert "types" in response.data
        assert "count" in response.data
        assert isinstance(response.data["types"], list)
        assert isinstance(response.data["count"], int)
        assert response.data["count"] == len(response.data["types"])

    def test_only_configurable_types(
        self, authenticated_client, configurable_types_url
    ):
        """Response only includes user_configurable types."""
        response = authenticated_client.get(configurable_types_url)

        assert response.status_code == status.HTTP_200_OK

        returned_names = {t["name"] for t in response.data["types"]}
        expected_names = {
            "new_login",
            "newsletter",
            "promotions",
            "transaction_invitation_received",
            "transaction_accepted",
            "transaction_denied",
            "transaction_cancelled",
            "transaction_expired",
            "transaction_expiring_soon",
            "transaction_info_requested",
            "transaction_resubmitted",
            "transaction_pending_approval",
            # Social / Network
            "new_follower",
            "follow_request_received",
            "follow_request_accepted",
            "connection_request_received",
            "connection_accepted",
            # Social / Chat
            "chat_message_received",
            "chat_request_received",
            "chat_request_accepted",
            "chat_group_added",
            "chat_reaction_received",
        }
        assert returned_names == expected_names

        # Non-configurable types must not be present
        non_configurable = {
            "verify_email",
            "welcome",
            "password_reset",
            "password_changed",
            "suspicious_activity",
        }
        assert returned_names.isdisjoint(non_configurable)

    def test_type_structure(self, authenticated_client, configurable_types_url):
        """Each type in the response has name, display_name, description, category, default_channels."""
        response = authenticated_client.get(configurable_types_url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] > 0

        for notification_type in response.data["types"]:
            assert "name" in notification_type
            assert "display_name" in notification_type
            assert "description" in notification_type
            assert "category" in notification_type
            assert "default_channels" in notification_type
            assert isinstance(notification_type["default_channels"], list)
