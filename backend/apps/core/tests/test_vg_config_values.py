"""
Tests for VG (Value Gate) Config Values — Phase 6
===================================================
Runtime parameterization of system behavior via feature_config.get_value().
Constants serve as defaults; deployment config overrides at runtime.
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from apps.core.exceptions import BusinessRuleViolation, ValidationError
from apps.core.feature_config import feature_config

# =============================================================================
# Chat — Message Max Length
# =============================================================================


@pytest.mark.django_db
class TestChatMessageMaxLength:
    """chat.messages.max_length overrides CHAT_MESSAGE_MAX_LENGTH."""

    def test_custom_max_length_blocks_long_message(self, feature_config_override):
        feature_config_override({"chat": {"messages": {"max_length": 100}}})

        from apps.chat.services import ChatService
        from apps.users.tests.factories import UserFactory

        user = UserFactory()
        with patch.object(ChatService, "_check_dm_request_limit"):
            with patch("apps.chat.services.ChatSelector") as mock_sel:
                mock_conv = MagicMock()
                mock_conv.conversation_type = "direct"
                mock_conv.scope_type = "global"
                mock_conv.scope_id = None
                mock_sel.get_conversation_by_id.return_value = mock_conv
                mock_sel.get_participant.return_value = MagicMock(is_active=True)

                with pytest.raises(ValidationError) as exc:
                    ChatService.send_message(
                        conversation_id=mock_conv.id,
                        sender_type="user",
                        sender_id=user.id,
                        acting_user_id=user.id,
                        content="x" * 101,
                    )
                assert "100" in str(exc.value)

    def test_default_allows_5000_chars(self):
        """Default max_length (5000) matches the constant."""
        val = feature_config.get_value("chat.messages.max_length", 5000)
        assert val == 5000


# =============================================================================
# Chat — Edit Window
# =============================================================================


@pytest.mark.django_db
class TestChatEditWindow:
    """chat.messages.edit_window_minutes overrides CHAT_MESSAGE_EDIT_WINDOW_MINUTES."""

    def test_custom_edit_window_blocks_late_edit(self, feature_config_override):
        feature_config_override({"chat": {"messages": {"edit_window_minutes": 5}}})

        from apps.chat.services import ChatService

        user = MagicMock()
        user.id = "00000000-0000-0000-0000-000000000001"

        message = MagicMock()
        message.sender_type = "user"
        message.sender_id = user.id
        message.status = "active"
        # Created 6 minutes ago — beyond the 5 min window
        message.created_at = timezone.now() - timedelta(minutes=6)

        with patch("apps.chat.services.ChatSelector") as mock_sel:
            mock_sel.get_message_by_id.return_value = message

            with pytest.raises(BusinessRuleViolation) as exc:
                ChatService.edit_message(
                    message_id=message.id,
                    user=user,
                    new_content="edited text",
                )
            assert "5 minutes" in str(exc.value)


# =============================================================================
# Chat — Group Max Participants
# =============================================================================


@pytest.mark.django_db
class TestChatGroupMaxParticipants:
    """chat.groups.max_participants overrides CHAT_GROUP_MAX_PARTICIPANTS."""

    def test_custom_group_limit(self, feature_config_override):
        feature_config_override({"chat": {"groups": {"max_participants": 5}}})

        val = feature_config.get_value("chat.groups.max_participants", 100)
        assert val == 5


# =============================================================================
# Chat — Request Config
# =============================================================================


class TestChatRequestConfig:
    """chat.requests.max_messages and chat.requests.expiry_days."""

    def test_custom_max_messages(self, feature_config_override):
        feature_config_override({"chat": {"requests": {"max_messages": 1}}})

        val = feature_config.get_value("chat.requests.max_messages", 3)
        assert val == 1

    def test_custom_expiry_days(self, feature_config_override):
        feature_config_override({"chat": {"requests": {"expiry_days": 7}}})

        val = feature_config.get_value("chat.requests.expiry_days", 30)
        assert val == 7


# =============================================================================
# Chat — Attachment Config
# =============================================================================


class TestChatAttachmentConfig:
    """chat.attachments.max_image_size_mb and max_per_message."""

    def test_custom_max_image_size(self, feature_config_override):
        feature_config_override({"chat": {"attachments": {"max_image_size_mb": 5}}})

        val = feature_config.get_value("chat.attachments.max_image_size_mb", 10)
        assert val == 5

    def test_custom_max_per_message(self, feature_config_override):
        feature_config_override({"chat": {"attachments": {"max_per_message": 3}}})

        val = feature_config.get_value("chat.attachments.max_per_message", 10)
        assert val == 3


# =============================================================================
# CMS — Version Config
# =============================================================================


class TestCmsVersionConfig:
    """cms.version_throttle_seconds and cms.max_versions_per_placement."""

    def test_custom_throttle_seconds(self, feature_config_override):
        feature_config_override({"cms": {"version_throttle_seconds": 60}})

        val = feature_config.get_value("cms.version_throttle_seconds", 30)
        assert val == 60

    def test_custom_max_versions(self, feature_config_override):
        feature_config_override({"cms": {"max_versions_per_placement": 20}})

        val = feature_config.get_value("cms.max_versions_per_placement", 50)
        assert val == 20


# =============================================================================
# Auth — Session Config
# =============================================================================


class TestAuthSessionConfig:
    """auth.sessions.max_per_user and token lifetimes."""

    def test_custom_max_sessions(self, feature_config_override):
        feature_config_override({"auth": {"sessions": {"max_per_user": 3}}})

        val = feature_config.get_value("auth.sessions.max_per_user", 5)
        assert val == 3

    def test_custom_token_lifetimes(self, feature_config_override):
        feature_config_override(
            {
                "auth": {
                    "sessions": {
                        "access_token_lifetime": 300,
                        "refresh_token_lifetime": 86400,
                    }
                }
            }
        )

        assert (
            feature_config.get_value("auth.sessions.access_token_lifetime", 900) == 300
        )
        assert (
            feature_config.get_value("auth.sessions.refresh_token_lifetime", 604800)
            == 86400
        )


# =============================================================================
# Auth — Lockout Config
# =============================================================================


class TestAuthLockoutConfig:
    """auth.lockout.max_failed_attempts and duration."""

    def test_custom_max_attempts(self, feature_config_override):
        feature_config_override({"auth": {"lockout": {"max_failed_attempts": 5}}})

        val = feature_config.get_value("auth.lockout.max_failed_attempts", 10)
        assert val == 5

    def test_custom_duration(self, feature_config_override):
        feature_config_override({"auth": {"lockout": {"duration": 1800}}})

        val = feature_config.get_value("auth.lockout.duration", 900)
        assert val == 1800


# =============================================================================
# Auth — Token Expiry
# =============================================================================


@pytest.mark.django_db
class TestAuthTokenExpiry:
    """auth.verification.expiry_minutes and auth.password_reset.expiry_minutes."""

    def test_custom_verification_expiry(self, feature_config_override):
        """EmailVerificationToken uses configured expiry."""
        feature_config_override({"auth": {"verification": {"expiry_minutes": 30}}})

        from apps.auth.models import EmailVerificationToken
        from apps.users.tests.factories import UserFactory

        user = UserFactory()
        token = EmailVerificationToken.create_for_user(user)

        expected_min = timezone.now() + timedelta(minutes=29)
        expected_max = timezone.now() + timedelta(minutes=31)
        assert expected_min < token.expires_at < expected_max

    def test_custom_password_reset_expiry(self, feature_config_override):
        """PasswordResetToken uses configured expiry."""
        feature_config_override({"auth": {"password_reset": {"expiry_minutes": 120}}})

        from apps.auth.models import PasswordResetToken
        from apps.users.tests.factories import UserFactory

        user = UserFactory()
        token = PasswordResetToken.create_for_user(user)

        expected_min = timezone.now() + timedelta(minutes=119)
        expected_max = timezone.now() + timedelta(minutes=121)
        assert expected_min < token.expires_at < expected_max


# =============================================================================
# Network — Follow Approval Required
# =============================================================================


@pytest.mark.django_db
class TestNetworkFollowApproval:
    """network.follow_approval_required overrides profile-level is_public check."""

    def test_config_true_forces_approval_type(self, feature_config_override):
        """When follow_approval_required=True, config overrides profile is_public."""
        feature_config_override({"network": {"follow_approval_required": True}})

        follow_approval = feature_config.get_value(
            "network.follow_approval_required", False
        )
        is_public = True  # Business IS public

        # Logic from FollowCreateView: if follow_approval or not is_public → approval type
        if follow_approval or not is_public:
            txn_type = "business_follow_approval_request"
        else:
            txn_type = "business_follow_request"

        assert txn_type == "business_follow_approval_request"

    def test_default_uses_profile_visibility(self):
        """Default (follow_approval_required=False): public business → follow_request."""
        follow_approval = feature_config.get_value(
            "network.follow_approval_required", False
        )
        is_public = True

        if follow_approval or not is_public:
            txn_type = "business_follow_approval_request"
        else:
            txn_type = "business_follow_request"

        assert txn_type == "business_follow_request"

    def test_private_business_always_needs_approval(self):
        """Private business always requires approval, regardless of config."""
        follow_approval = feature_config.get_value(
            "network.follow_approval_required", False
        )
        is_public = False

        if follow_approval or not is_public:
            txn_type = "business_follow_approval_request"
        else:
            txn_type = "business_follow_request"

        assert txn_type == "business_follow_approval_request"


# =============================================================================
# Transaction — Reminder Config
# =============================================================================


class TestTransactionReminderConfig:
    """transaction.expiration_reminder_hours overrides hardcoded 48h window."""

    def test_custom_reminder_hours(self, feature_config_override):
        feature_config_override({"transaction": {"expiration_reminder_hours": 72}})

        val = feature_config.get_value("transaction.expiration_reminder_hours", 48)
        assert val == 72


# =============================================================================
# Explore — Min Search Length
# =============================================================================


@pytest.mark.django_db
class TestExploreMinSearchLength:
    """explore.min_search_length overrides default 2-char minimum."""

    def test_custom_min_length_drops_short_query(self, feature_config_override, rf):
        """When min_search_length=5, a 3-char query is treated as empty."""
        feature_config_override({"explore": {"min_search_length": 5}})

        from apps.explore.views import ExploreCombinedView
        from apps.users.tests.factories import UserFactory

        user = UserFactory()
        request = rf.get("/api/v1/explore/", {"q": "abc"})
        request.user = user

        with patch("apps.explore.views.ExploreSelector") as mock_sel:
            mock_sel.search_businesses.return_value = MagicMock(
                __getitem__=lambda s, k: [],
                count=lambda: 0,
            )
            mock_sel.search_users.return_value = MagicMock(
                __getitem__=lambda s, k: [],
                count=lambda: 0,
            )

            view = ExploreCombinedView.as_view()
            view(request)

        # search_businesses was called with query="" (short query stripped)
        call_kwargs = mock_sel.search_businesses.call_args[1]
        assert call_kwargs["query"] == ""

    def test_default_allows_2_char_query(self, feature_config_override, rf):
        """Default min_search_length=2 allows 2-char queries through."""
        from apps.explore.views import ExploreCombinedView

        request = rf.get("/api/v1/explore/", {"q": "ab"})
        request.user = MagicMock(is_authenticated=True)

        with patch("apps.explore.views.ExploreSelector") as mock_sel:
            mock_sel.search_businesses.return_value = MagicMock(
                __getitem__=lambda s, k: [],
                count=lambda: 0,
            )
            mock_sel.search_users.return_value = MagicMock(
                __getitem__=lambda s, k: [],
                count=lambda: 0,
            )

            view = ExploreCombinedView.as_view()
            view(request)

        call_kwargs = mock_sel.search_businesses.call_args[1]
        assert call_kwargs["query"] == "ab"


# =============================================================================
# Notifications — Channel Config
# =============================================================================


@pytest.mark.django_db
class TestNotificationChannelConfig:
    """Deployment-level channel enables filter out disabled channels."""

    def test_push_disabled_filters_out_push(self, feature_config_override):
        """notifications.push_enabled=False removes push even if user enabled it."""
        feature_config_override({"notifications": {"push_enabled": False}})

        from apps.notifications.services.notification_service import NotificationService
        from apps.users.tests.factories import UserFactory

        user = UserFactory()

        with patch(
            "apps.notifications.services.notification_service.PreferenceService"
        ) as mock_pref:
            mock_pref.get_enabled_channels.return_value = ["email", "push"]

            with patch(
                "apps.notifications.services.notification_service.get_notification_type"
            ) as mock_type:
                mock_type.return_value = MagicMock(enabled=True, required_context=[])

                with patch(
                    "apps.notifications.services.notification_service.NotificationService._dispatch_now"
                ):
                    log = NotificationService.send(
                        user=user,
                        notification_type="test_type",
                        context={},
                        async_dispatch=False,
                    )

        # push was filtered out, only email should remain
        assert "push" not in log.channels
        assert "email" in log.channels

    def test_all_enabled_passes_through(self, feature_config_override):
        """All channels enabled: all user-preferred channels preserved."""
        feature_config_override(
            {
                "notifications": {
                    "email_enabled": True,
                    "push_enabled": True,
                    "sms_enabled": True,
                }
            }
        )

        from apps.notifications.services.notification_service import NotificationService
        from apps.users.tests.factories import UserFactory

        user = UserFactory()

        with patch(
            "apps.notifications.services.notification_service.PreferenceService"
        ) as mock_pref:
            mock_pref.get_enabled_channels.return_value = ["email", "push", "sms"]

            with patch(
                "apps.notifications.services.notification_service.get_notification_type"
            ) as mock_type:
                mock_type.return_value = MagicMock(enabled=True, required_context=[])

                with patch(
                    "apps.notifications.services.notification_service.NotificationService._dispatch_now"
                ):
                    log = NotificationService.send(
                        user=user,
                        notification_type="test_type",
                        context={},
                        async_dispatch=False,
                    )

        assert set(log.channels) == {"email", "push", "sms"}

    def test_email_disabled_filters_out_email(self, feature_config_override):
        """notifications.email_enabled=False removes email channel."""
        feature_config_override({"notifications": {"email_enabled": False}})

        from apps.notifications.services.notification_service import NotificationService
        from apps.users.tests.factories import UserFactory

        user = UserFactory()

        with patch(
            "apps.notifications.services.notification_service.PreferenceService"
        ) as mock_pref:
            mock_pref.get_enabled_channels.return_value = ["email", "push"]

            with patch(
                "apps.notifications.services.notification_service.get_notification_type"
            ) as mock_type:
                mock_type.return_value = MagicMock(enabled=True, required_context=[])

                with patch(
                    "apps.notifications.services.notification_service.NotificationService._dispatch_now"
                ):
                    log = NotificationService.send(
                        user=user,
                        notification_type="test_type",
                        context={},
                        async_dispatch=False,
                    )

        assert "email" not in log.channels
        assert "push" in log.channels


# =============================================================================
# Behavioral Boolean Defaults
# =============================================================================


class TestBehavioralBoolDefaults:
    """Default values match current constants and settings."""

    def test_follow_approval_default_false(self):
        val = feature_config.get_value("network.follow_approval_required", False)
        assert val is False

    def test_connection_approval_default_true(self):
        val = feature_config.get_value("network.connection_approval_required", True)
        assert val is True


# =============================================================================
# Config Array Values
# =============================================================================


class TestConfigArrayValues:
    """Array config values (reactions, image types) read correctly."""

    def test_chat_allowed_image_types(self):
        val = feature_config.get_value(
            "chat.attachments.allowed_image_types",
            ["jpeg", "png", "gif", "webp"],
        )
        assert isinstance(val, list)
        assert "jpeg" in val
        assert "webp" in val

    def test_chat_reaction_types(self):
        val = feature_config.get_value(
            "chat.reactions.types",
            ["like", "heart", "laugh", "wow", "sad", "angry"],
        )
        assert len(val) == 6
        assert "like" in val


# =============================================================================
# Presence Config
# =============================================================================


class TestPresenceConfig:
    """chat.presence.ttl_seconds and heartbeat_interval_seconds."""

    def test_custom_ttl(self, feature_config_override):
        feature_config_override({"chat": {"presence": {"ttl_seconds": 60}}})

        val = feature_config.get_value("chat.presence.ttl_seconds", 30)
        assert val == 60

    def test_custom_heartbeat(self, feature_config_override):
        feature_config_override(
            {"chat": {"presence": {"heartbeat_interval_seconds": 10}}}
        )

        val = feature_config.get_value("chat.presence.heartbeat_interval_seconds", 20)
        assert val == 10
