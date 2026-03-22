# apps/notifications/tests/test_services.py
"""
Tests for Notification and Preference services.

Covers:
    - NotificationService.send() — validation, logging, async/sync dispatch
    - NotificationService.send_bulk() — per-user delivery and error isolation
    - NotificationService._dispatch_now() — channel dispatch and status resolution
    - PreferenceService.update_preference() — CRUD, audit, validation
    - PreferenceService.get_preference() / get_all_preferences() — reads + defaults
    - PreferenceService.reset_preference() — revert to defaults
"""

from unittest.mock import MagicMock, patch

import pytest

from apps.core.exceptions import NotFound, ValidationError
from apps.core.observability.audit.models import AuditLog
from apps.notifications.models import NotificationLog, NotificationPreference
from apps.notifications.services.notification_service import NotificationService
from apps.notifications.services.preference_service import PreferenceService
from apps.notifications.tests.factories import (
    DisabledPreferenceFactory,
    NotificationLogFactory,
    NotificationPreferenceFactory,
)
from apps.users.tests.factories import UserFactory

# =============================================================================
# NotificationService.send()
# =============================================================================


@pytest.mark.django_db
class TestNotificationServiceSend:
    """Tests for NotificationService.send()."""

    def test_send_creates_log_with_pending_status(self, user):
        """Happy path: send() creates a NotificationLog with PENDING status."""
        with (
            patch(
                "apps.notifications.services.notification_service.PreferenceService"
                ".get_enabled_channels",
                return_value=["email"],
            ),
            patch(
                "apps.notifications.tasks.dispatch_notification_task.delay"
            ) as mock_delay,
        ):
            log = NotificationService.send(
                user=user,
                notification_type="welcome",
                context={},
            )

        assert log.status == NotificationLog.Status.PENDING
        assert log.user == user
        assert log.notification_type == "welcome"
        assert NotificationLog.objects.filter(id=log.id).exists()
        mock_delay.assert_called_once_with(str(log.id))

    def test_send_raises_not_found_for_unknown_type(self, user):
        """send() raises NotFound when the notification type does not exist."""
        with pytest.raises(NotFound):
            NotificationService.send(
                user=user,
                notification_type="nonexistent_type",
                context={},
            )

    def test_send_validates_required_context(self, user):
        """send() raises ValidationError when a required context key is missing."""
        with pytest.raises(ValidationError, match="Missing required context"):
            NotificationService.send(
                user=user,
                notification_type="new_login",
                context={"device": "iPhone"},  # missing 'location' and 'time'
            )

    def test_send_passes_with_valid_context(self, user):
        """send() succeeds when all required context keys are provided."""
        with (
            patch(
                "apps.notifications.services.notification_service.PreferenceService"
                ".get_enabled_channels",
                return_value=["email"],
            ),
            patch("apps.notifications.tasks.dispatch_notification_task.delay"),
        ):
            log = NotificationService.send(
                user=user,
                notification_type="new_login",
                context={"device": "iPhone", "location": "NYC", "time": "now"},
            )

        assert log.status == NotificationLog.Status.PENDING

    def test_send_async_queues_task(self, user):
        """send() with async_dispatch=True calls dispatch_notification_task.delay()."""
        with (
            patch(
                "apps.notifications.services.notification_service.PreferenceService"
                ".get_enabled_channels",
                return_value=["email"],
            ),
            patch(
                "apps.notifications.tasks.dispatch_notification_task.delay"
            ) as mock_delay,
        ):
            log = NotificationService.send(
                user=user,
                notification_type="welcome",
                context={},
                async_dispatch=True,
            )

        mock_delay.assert_called_once_with(str(log.id))

    def test_send_sync_calls_dispatch_now(self, user):
        """send() with async_dispatch=False calls _dispatch_now() directly."""
        with (
            patch(
                "apps.notifications.services.notification_service.PreferenceService"
                ".get_enabled_channels",
                return_value=["email"],
            ),
            patch.object(NotificationService, "_dispatch_now") as mock_dispatch,
        ):
            log = NotificationService.send(
                user=user,
                notification_type="welcome",
                context={},
                async_dispatch=False,
            )

        mock_dispatch.assert_called_once_with(log)

    def test_send_force_channels_overrides_preferences(self, user):
        """force_channels bypasses user preference lookup."""
        # Create a preference that would return only 'push'
        NotificationPreferenceFactory(
            user=user,
            notification_type="new_login",
            email_enabled=False,
            push_enabled=True,
            sms_enabled=False,
        )

        with patch("apps.notifications.tasks.dispatch_notification_task.delay"):
            log = NotificationService.send(
                user=user,
                notification_type="new_login",
                context={"device": "iPhone", "location": "NYC", "time": "now"},
                force_channels=["email", "sms"],
            )

        assert log.channels == ["email", "sms"]

    def test_send_no_channels_creates_sent_log(self, user):
        """When user has disabled all channels, log is created with SENT status and a note."""
        DisabledPreferenceFactory(user=user, notification_type="new_login")

        log = NotificationService.send(
            user=user,
            notification_type="new_login",
            context={"device": "iPhone", "location": "NYC", "time": "now"},
        )

        assert log.status == NotificationLog.Status.SENT
        assert log.channels == []
        assert log.channel_results == {"note": "No channels enabled"}

    def test_send_stores_context_in_log(self, user):
        """send() persists the context dict to the NotificationLog."""
        context = {"device": "Pixel", "location": "London", "time": "14:00"}

        with (
            patch(
                "apps.notifications.services.notification_service.PreferenceService"
                ".get_enabled_channels",
                return_value=["email"],
            ),
            patch("apps.notifications.tasks.dispatch_notification_task.delay"),
        ):
            log = NotificationService.send(
                user=user,
                notification_type="new_login",
                context=context,
            )

        log.refresh_from_db()
        assert log.context == context

    def test_send_stores_channels_in_log(self, user):
        """send() records the resolved channels list on the log."""
        with (
            patch(
                "apps.notifications.services.notification_service.PreferenceService"
                ".get_enabled_channels",
                return_value=["email", "push"],
            ),
            patch("apps.notifications.tasks.dispatch_notification_task.delay"),
        ):
            log = NotificationService.send(
                user=user,
                notification_type="welcome",
                context={},
            )

        log.refresh_from_db()
        assert log.channels == ["email", "push"]

    def test_send_with_disabled_type_raises_validation_error(self, user):
        """send() raises ValidationError when the notification type is disabled."""
        with patch(
            "apps.notifications.services.notification_service.get_notification_type"
        ) as mock_get:
            mock_config = MagicMock()
            mock_config.enabled = False
            mock_get.return_value = mock_config

            with pytest.raises(ValidationError, match="disabled"):
                NotificationService.send(
                    user=user,
                    notification_type="welcome",
                    context={},
                )

    def test_send_bulk_returns_logs_per_user(self):
        """send_bulk() returns one NotificationLog per user."""
        users = UserFactory.create_batch(3)

        with (
            patch(
                "apps.notifications.services.notification_service.PreferenceService"
                ".get_enabled_channels",
                return_value=["email"],
            ),
            patch("apps.notifications.tasks.dispatch_notification_task.delay"),
        ):
            logs = NotificationService.send_bulk(
                users=users,
                notification_type="welcome",
                context_fn=lambda u: {},
            )

        assert len(logs) == 3
        log_user_ids = {log.user_id for log in logs}
        expected_user_ids = {u.id for u in users}
        assert log_user_ids == expected_user_ids


# =============================================================================
# NotificationService._dispatch_now()
# =============================================================================


@pytest.mark.django_db
class TestNotificationServiceDispatch:
    """Tests for NotificationService._dispatch_now()."""

    def test_dispatch_now_sends_to_all_channels(self, user):
        """_dispatch_now() invokes each channel's send() method."""
        log = NotificationLogFactory(
            user=user,
            channels=["email", "push"],
            context={"key": "val"},
        )

        mock_email_channel = MagicMock()
        mock_email_channel.send.return_value = {"status": "sent"}
        mock_push_channel = MagicMock()
        mock_push_channel.send.return_value = {"status": "sent"}

        def fake_get_channel(name):
            return {"email": mock_email_channel, "push": mock_push_channel}.get(name)

        with patch(
            "apps.notifications.services.channels.get_channel",
            side_effect=fake_get_channel,
        ):
            NotificationService._dispatch_now(log)

        mock_email_channel.send.assert_called_once()
        mock_push_channel.send.assert_called_once()

    def test_dispatch_now_skips_non_pending_log(self, user):
        """_dispatch_now() does nothing if the log is not PENDING (e.g. already PROCESSING)."""
        log = NotificationLogFactory(
            user=user,
            channels=["email"],
            status=NotificationLog.Status.PROCESSING,
        )

        with patch("apps.notifications.services.channels.get_channel") as mock_get:
            NotificationService._dispatch_now(log)

        mock_get.assert_not_called()
        log.refresh_from_db()
        assert log.status == NotificationLog.Status.PROCESSING

    def test_dispatch_now_marks_sent_when_all_succeed(self, user):
        """Final status is SENT when every channel returns status='sent'."""
        log = NotificationLogFactory(
            user=user,
            channels=["email"],
            context={},
        )

        mock_channel = MagicMock()
        mock_channel.send.return_value = {"status": "sent"}

        with patch(
            "apps.notifications.services.channels.get_channel",
            return_value=mock_channel,
        ):
            NotificationService._dispatch_now(log)

        log.refresh_from_db()
        assert log.status == NotificationLog.Status.SENT

    def test_dispatch_now_marks_partial_when_some_fail(self, user):
        """Final status is PARTIAL when at least one channel sent and one failed."""
        log = NotificationLogFactory(
            user=user,
            channels=["email", "push"],
            context={},
        )

        mock_email = MagicMock()
        mock_email.send.return_value = {"status": "sent"}
        mock_push = MagicMock()
        mock_push.send.return_value = {"status": "failed", "error": "unavailable"}

        def fake_get_channel(name):
            return {"email": mock_email, "push": mock_push}.get(name)

        with patch(
            "apps.notifications.services.channels.get_channel",
            side_effect=fake_get_channel,
        ):
            NotificationService._dispatch_now(log)

        log.refresh_from_db()
        assert log.status == NotificationLog.Status.PARTIAL

    def test_dispatch_now_marks_failed_when_all_fail(self, user):
        """Final status is FAILED when all channels fail."""
        log = NotificationLogFactory(
            user=user,
            channels=["email", "push"],
            context={},
        )

        mock_email = MagicMock()
        mock_email.send.return_value = {"status": "failed", "error": "smtp error"}
        mock_push = MagicMock()
        mock_push.send.return_value = {"status": "failed", "error": "push error"}

        def fake_get_channel(name):
            return {"email": mock_email, "push": mock_push}.get(name)

        with patch(
            "apps.notifications.services.channels.get_channel",
            side_effect=fake_get_channel,
        ):
            NotificationService._dispatch_now(log)

        log.refresh_from_db()
        assert log.status == NotificationLog.Status.FAILED

    def test_dispatch_now_handles_all_skipped_as_sent(self, user):
        """When get_channel returns None for all channels (unknown), final status is SENT.

        This tests the edge case where all channels resolve to None and produce
        no results — the statuses list is empty, and ``all(s == 'sent' for s in [])``
        is True, so the final status becomes SENT.
        """
        log = NotificationLogFactory(
            user=user,
            channels=["unknown_channel"],
            context={},
        )

        with patch(
            "apps.notifications.services.channels.get_channel",
            return_value=None,
        ):
            NotificationService._dispatch_now(log)

        log.refresh_from_db()
        # No channel_results produced → empty statuses → all() on empty = True → SENT
        assert log.status == NotificationLog.Status.SENT


# =============================================================================
# PreferenceService.update_preference()
# =============================================================================


@pytest.mark.django_db
class TestPreferenceServiceUpdate:
    """Tests for PreferenceService.update_preference()."""

    def test_update_creates_preference_if_not_exists(self, user):
        """update_preference() creates a new preference record if none exists."""
        assert not NotificationPreference.objects.filter(
            user=user, notification_type="new_login"
        ).exists()

        with patch("apps.notifications.services.preference_service.AuditService.log"):
            pref = PreferenceService.update_preference(
                user=user,
                notification_type="new_login",
                email_enabled=False,
            )

        assert pref.pk is not None
        assert pref.user == user
        assert pref.notification_type == "new_login"
        assert pref.email_enabled is False

    def test_update_modifies_existing_preference(self, user):
        """update_preference() updates an existing preference record."""
        NotificationPreferenceFactory(
            user=user,
            notification_type="new_login",
            email_enabled=True,
            push_enabled=False,
        )

        with patch("apps.notifications.services.preference_service.AuditService.log"):
            pref = PreferenceService.update_preference(
                user=user,
                notification_type="new_login",
                push_enabled=True,
            )

        pref.refresh_from_db()
        assert pref.push_enabled is True
        # email_enabled should remain unchanged
        assert pref.email_enabled is True

    def test_update_raises_not_found_for_unknown_type(self, user):
        """update_preference() raises NotFound for an unregistered notification type."""
        with pytest.raises(NotFound):
            PreferenceService.update_preference(
                user=user,
                notification_type="does_not_exist",
                email_enabled=True,
            )

    def test_update_raises_validation_error_for_non_configurable_type(self, user):
        """update_preference() raises ValidationError for non-user-configurable types."""
        with pytest.raises(ValidationError, match="Cannot modify"):
            PreferenceService.update_preference(
                user=user,
                notification_type="verify_email",
                email_enabled=False,
            )

    def test_update_only_changes_provided_fields(self, user):
        """Only fields explicitly passed are modified; others stay at their prior values."""
        NotificationPreferenceFactory(
            user=user,
            notification_type="newsletter",
            email_enabled=True,
            push_enabled=False,
            sms_enabled=False,
        )

        with patch("apps.notifications.services.preference_service.AuditService.log"):
            pref = PreferenceService.update_preference(
                user=user,
                notification_type="newsletter",
                email_enabled=False,
                # push_enabled and sms_enabled not provided → no change
            )

        pref.refresh_from_db()
        assert pref.email_enabled is False
        assert pref.push_enabled is False  # unchanged
        assert pref.sms_enabled is False  # unchanged

    def test_update_calls_audit_service_on_change(self, user):
        """AuditService.log() is called when a preference field actually changes."""
        NotificationPreferenceFactory(
            user=user,
            notification_type="new_login",
            email_enabled=True,
        )

        with patch(
            "apps.notifications.services.preference_service.AuditService.log"
        ) as mock_audit:
            PreferenceService.update_preference(
                user=user,
                notification_type="new_login",
                email_enabled=False,
            )

        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args
        assert call_kwargs.kwargs["actor"] == user
        assert "email_enabled" in call_kwargs.kwargs["changes"]

    def test_update_no_audit_when_no_changes(self, user):
        """AuditService.log() is NOT called when the submitted values are identical."""
        NotificationPreferenceFactory(
            user=user,
            notification_type="new_login",
            email_enabled=True,
            push_enabled=True,
        )

        with patch(
            "apps.notifications.services.preference_service.AuditService.log"
        ) as mock_audit:
            PreferenceService.update_preference(
                user=user,
                notification_type="new_login",
                email_enabled=True,  # same value
                push_enabled=True,  # same value
            )

        mock_audit.assert_not_called()

    def test_update_returns_preference_object(self, user):
        """update_preference() returns the NotificationPreference instance."""
        with patch("apps.notifications.services.preference_service.AuditService.log"):
            result = PreferenceService.update_preference(
                user=user,
                notification_type="new_login",
                email_enabled=True,
            )

        assert isinstance(result, NotificationPreference)
        assert result.notification_type == "new_login"


# =============================================================================
# PreferenceService.get_preference() / get_all_preferences() /
# get_enabled_channels()
# =============================================================================


@pytest.mark.django_db
class TestPreferenceServiceGet:
    """Tests for PreferenceService read methods."""

    def test_get_preference_returns_defaults_when_no_override(self, user):
        """get_preference() returns type defaults when user has no stored preference."""
        result = PreferenceService.get_preference(
            user=user,
            notification_type="welcome",
        )

        assert result["notification_type"] == "welcome"
        assert result["email_enabled"] is True  # default channel for 'welcome'
        assert result["push_enabled"] is False
        assert result["sms_enabled"] is False
        assert result["user_configurable"] is False
        assert result["category"] == "auth"

    def test_get_preference_returns_stored_values(self, user):
        """get_preference() returns the user's stored override when one exists."""
        NotificationPreferenceFactory(
            user=user,
            notification_type="new_login",
            email_enabled=False,
            push_enabled=True,
            sms_enabled=True,
        )

        result = PreferenceService.get_preference(
            user=user,
            notification_type="new_login",
        )

        assert result["email_enabled"] is False
        assert result["push_enabled"] is True
        assert result["sms_enabled"] is True

    def test_get_preference_raises_not_found_for_unknown_type(self, user):
        """get_preference() raises NotFound for an unregistered type."""
        with pytest.raises(NotFound):
            PreferenceService.get_preference(
                user=user,
                notification_type="nonexistent",
            )

    def test_get_all_preferences_returns_only_configurable(self, user):
        """get_all_preferences() only includes user_configurable types."""
        result = PreferenceService.get_all_preferences(user=user)

        # 'new_login', 'newsletter', 'promotions' are configurable
        assert "new_login" in result
        assert "newsletter" in result
        assert "promotions" in result

        # 'welcome', 'verify_email', 'suspicious_activity' are NOT configurable
        assert "welcome" not in result
        assert "verify_email" not in result
        assert "suspicious_activity" not in result

    def test_get_all_preferences_includes_user_overrides(self, user):
        """get_all_preferences() reflects stored overrides for the user."""
        NotificationPreferenceFactory(
            user=user,
            notification_type="newsletter",
            email_enabled=False,
            push_enabled=True,
            sms_enabled=False,
        )

        result = PreferenceService.get_all_preferences(user=user)

        assert result["newsletter"]["email_enabled"] is False
        assert result["newsletter"]["push_enabled"] is True

    def test_get_enabled_channels_returns_defaults(self, user):
        """get_enabled_channels() returns type default channels when no preference exists."""
        channels = PreferenceService.get_enabled_channels(
            user=user,
            notification_type="suspicious_activity",
        )

        # suspicious_activity defaults: [Channel.EMAIL, Channel.PUSH]
        assert "email" in channels
        assert "push" in channels
        assert "sms" not in channels


# =============================================================================
# PreferenceService.reset_preference()
# =============================================================================


@pytest.mark.django_db
class TestPreferenceServiceReset:
    """Tests for PreferenceService.reset_preference()."""

    def test_reset_deletes_stored_preference(self, user):
        """reset_preference() deletes the stored override row."""
        NotificationPreferenceFactory(
            user=user,
            notification_type="new_login",
        )
        assert NotificationPreference.objects.filter(
            user=user, notification_type="new_login"
        ).exists()

        PreferenceService.reset_preference(
            user=user,
            notification_type="new_login",
        )

        assert not NotificationPreference.objects.filter(
            user=user, notification_type="new_login"
        ).exists()

    def test_reset_no_error_when_no_preference_exists(self, user):
        """reset_preference() is a no-op (no error) when there is nothing to delete."""
        # Should not raise
        PreferenceService.reset_preference(
            user=user,
            notification_type="new_login",
        )

    def test_reset_raises_not_found_for_unknown_type(self, user):
        """reset_preference() raises NotFound for an unregistered type."""
        with pytest.raises(NotFound):
            PreferenceService.reset_preference(
                user=user,
                notification_type="completely_fake",
            )

    def test_reset_reverts_to_defaults(self, user):
        """After reset, get_preference() returns type defaults again."""
        NotificationPreferenceFactory(
            user=user,
            notification_type="new_login",
            email_enabled=False,
            push_enabled=False,
            sms_enabled=True,
        )

        PreferenceService.reset_preference(
            user=user,
            notification_type="new_login",
        )

        result = PreferenceService.get_preference(
            user=user,
            notification_type="new_login",
        )

        # 'new_login' default is [Channel.EMAIL] → email=True, push=False, sms=False
        assert result["email_enabled"] is True
        assert result["push_enabled"] is False
        assert result["sms_enabled"] is False


# =============================================================================
# NotificationService.send_bulk() — dedicated bulk tests
# =============================================================================


@pytest.mark.django_db
class TestNotificationServiceBulk:
    """Tests for NotificationService.send_bulk()."""

    def test_send_bulk_creates_log_per_user(self):
        """send_bulk() produces one NotificationLog per user."""
        users = UserFactory.create_batch(4)

        with (
            patch(
                "apps.notifications.services.notification_service.PreferenceService"
                ".get_enabled_channels",
                return_value=["email"],
            ),
            patch("apps.notifications.tasks.dispatch_notification_task.delay"),
        ):
            logs = NotificationService.send_bulk(
                users=users,
                notification_type="welcome",
                context_fn=lambda u: {},
            )

        assert len(logs) == 4
        assert all(isinstance(l, NotificationLog) for l in logs)

    def test_send_bulk_continues_on_error(self):
        """If one user's send() raises, the others still succeed."""
        users = UserFactory.create_batch(3)

        original_send = NotificationService.send

        def patched_send(
            *,
            user,
            notification_type,
            context,
            force_channels=None,
            async_dispatch=True,
        ):
            if user == users[1]:
                raise RuntimeError("Simulated failure for second user")
            return original_send(
                user=user,
                notification_type=notification_type,
                context=context,
                force_channels=force_channels,
                async_dispatch=async_dispatch,
            )

        with (
            patch.object(NotificationService, "send", staticmethod(patched_send)),
            patch(
                "apps.notifications.services.notification_service.PreferenceService"
                ".get_enabled_channels",
                return_value=["email"],
            ),
            patch("apps.notifications.tasks.dispatch_notification_task.delay"),
        ):
            logs = NotificationService.send_bulk(
                users=users,
                notification_type="welcome",
                context_fn=lambda u: {},
            )

        # Only 2 of 3 succeed (user at index 1 fails)
        assert len(logs) == 2
        successful_user_ids = {log.user_id for log in logs}
        assert users[0].id in successful_user_ids
        assert users[2].id in successful_user_ids
        assert users[1].id not in successful_user_ids
