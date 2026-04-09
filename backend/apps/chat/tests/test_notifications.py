"""
Chat Notification Tests
=======================
Tests for notification logic in ChatService (Phase 3).
Mocks NotificationService.send(), PresenceManager, and Redis.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from apps.chat.constants import (
    ConversationType,
    ParticipantRole,
    ParticipantType,
    RequestStatus,
    ScopeType,
)
from apps.chat.models import Conversation, ConversationParticipant, Message
from apps.chat.services import ChatService
from apps.users.tests.factories import UserFactory


@pytest.fixture
def user(db):
    return UserFactory(is_verified=True)


@pytest.fixture
def user_b(db):
    return UserFactory(is_verified=True)


@pytest.fixture
def user_c(db):
    return UserFactory(is_verified=True)


@pytest.fixture
def dm_conversation(db, user, user_b):
    conv = Conversation.objects.create(
        scope_type=ScopeType.GLOBAL,
        conversation_type=ConversationType.DIRECT,
        created_by_type=ParticipantType.USER,
        created_by_id=user.id,
    )
    ConversationParticipant.objects.create(
        conversation=conv,
        participant_type=ParticipantType.USER,
        participant_id=user.id,
        role=ParticipantRole.MEMBER,
        request_status=RequestStatus.NONE,
    )
    ConversationParticipant.objects.create(
        conversation=conv,
        participant_type=ParticipantType.USER,
        participant_id=user_b.id,
        role=ParticipantRole.MEMBER,
        request_status=RequestStatus.NONE,
    )
    return conv


@pytest.fixture
def group_conversation(db, user, user_b, user_c):
    conv = Conversation.objects.create(
        scope_type=ScopeType.GLOBAL,
        conversation_type=ConversationType.GROUP,
        name="Test Group",
        created_by_type=ParticipantType.USER,
        created_by_id=user.id,
    )
    ConversationParticipant.objects.create(
        conversation=conv,
        participant_type=ParticipantType.USER,
        participant_id=user.id,
        role=ParticipantRole.ADMIN,
        request_status=RequestStatus.NONE,
    )
    ConversationParticipant.objects.create(
        conversation=conv,
        participant_type=ParticipantType.USER,
        participant_id=user_b.id,
        role=ParticipantRole.MEMBER,
        request_status=RequestStatus.NONE,
    )
    ConversationParticipant.objects.create(
        conversation=conv,
        participant_type=ParticipantType.USER,
        participant_id=user_c.id,
        role=ParticipantRole.MEMBER,
        request_status=RequestStatus.NONE,
    )
    return conv


@pytest.fixture
def message_in_group(db, group_conversation, user):
    return Message.objects.create(
        conversation=group_conversation,
        sender_type=ParticipantType.USER,
        sender_id=user.id,
        content="Hello group",
        content_type="text",
        sequence_number=1,
    )


# =============================================================================
# NOTIFICATION TYPE REGISTRATION
# =============================================================================


class TestNotificationTypeRegistration:
    def test_chat_message_received_type_exists(self):
        from apps.notifications.types import NOTIFICATION_TYPES

        assert "chat_message_received" in NOTIFICATION_TYPES

    def test_chat_request_received_type_exists(self):
        from apps.notifications.types import NOTIFICATION_TYPES

        assert "chat_request_received" in NOTIFICATION_TYPES

    def test_chat_request_accepted_type_exists(self):
        from apps.notifications.types import NOTIFICATION_TYPES

        assert "chat_request_accepted" in NOTIFICATION_TYPES

    def test_chat_group_added_type_exists(self):
        from apps.notifications.types import NOTIFICATION_TYPES

        assert "chat_group_added" in NOTIFICATION_TYPES

    def test_chat_message_received_config(self):
        from apps.notifications.types import NOTIFICATION_TYPES, Category, Channel

        config = NOTIFICATION_TYPES["chat_message_received"]
        assert config.category == Category.SOCIAL
        assert Channel.PUSH in config.default_channels
        assert config.user_configurable is True
        assert "conversation_id" in config.required_context
        assert "sender_name" in config.required_context
        assert "preview" in config.required_context

    def test_chat_request_received_config(self):
        from apps.notifications.types import NOTIFICATION_TYPES, Channel

        config = NOTIFICATION_TYPES["chat_request_received"]
        assert Channel.EMAIL in config.default_channels
        assert Channel.PUSH in config.default_channels


# =============================================================================
# _notify_safe
# =============================================================================


@pytest.mark.django_db
class TestNotifySafe:
    def test_notify_safe_dispatches_to_handler(self):
        mock_ns = MagicMock()
        with patch.object(
            ChatService,
            "_notify_new_message",
        ) as mock_handler:
            with patch("apps.chat.services.NotificationService", mock_ns, create=True):
                ChatService._notify_safe("new_message", message="m", conversation="c")
            mock_handler.assert_called_once()

    def test_notify_safe_swallows_handler_exception(self):
        with patch(
            "apps.chat.services.NotificationService",
            MagicMock(),
            create=True,
        ):
            with patch.object(
                ChatService,
                "_notify_new_message",
                side_effect=Exception("boom"),
            ):
                # Should not raise
                ChatService._notify_safe("new_message", message="m", conversation="c")

    def test_notify_safe_handles_missing_handler(self):
        with patch(
            "apps.chat.services.NotificationService",
            MagicMock(),
            create=True,
        ):
            # No _notify_nonexistent handler exists
            ChatService._notify_safe("nonexistent", foo="bar")

    def test_notify_safe_handles_import_error(self):
        with patch(
            "apps.chat.services.NotificationService",
            side_effect=ImportError("no module"),
            create=True,
        ):
            # Should not raise
            ChatService._notify_safe("new_message", message="m", conversation="c")


# =============================================================================
# _is_rate_limited
# =============================================================================


class TestIsRateLimited:
    @patch("apps.chat.presence.PresenceManager")
    def test_not_rate_limited_when_key_missing(self, mock_pm):
        mock_redis = MagicMock()
        mock_redis.exists.return_value = 0
        mock_pm._get_redis.return_value = mock_redis

        uid = uuid.uuid4()
        cid = uuid.uuid4()
        assert ChatService._is_rate_limited(uid, cid) is False
        mock_redis.setex.assert_called_once()

    @patch("apps.chat.presence.PresenceManager")
    def test_rate_limited_when_key_exists(self, mock_pm):
        mock_redis = MagicMock()
        mock_redis.exists.return_value = 1
        mock_pm._get_redis.return_value = mock_redis

        assert ChatService._is_rate_limited(uuid.uuid4(), uuid.uuid4()) is True
        mock_redis.setex.assert_not_called()

    @patch("apps.chat.presence.PresenceManager")
    def test_fail_open_when_redis_unavailable(self, mock_pm):
        mock_pm._get_redis.return_value = "unavailable"
        assert ChatService._is_rate_limited(uuid.uuid4(), uuid.uuid4()) is False

    @patch("apps.chat.presence.PresenceManager")
    def test_fail_open_on_redis_exception(self, mock_pm):
        mock_pm._get_redis.side_effect = Exception("redis down")
        assert ChatService._is_rate_limited(uuid.uuid4(), uuid.uuid4()) is False


# =============================================================================
# _notify_new_message
# =============================================================================


@pytest.mark.django_db
class TestNotifyNewMessage:
    @patch("apps.chat.services.ChatService._is_rate_limited", return_value=False)
    @patch("apps.chat.presence.PresenceManager")
    def test_notifies_offline_participant(
        self, mock_pm, mock_rl, group_conversation, message_in_group, user_b
    ):
        mock_pm.is_online.return_value = False
        mock_ns = MagicMock()

        ChatService._notify_new_message(
            mock_ns, message=message_in_group, conversation=group_conversation
        )

        assert mock_ns.send.call_count >= 1
        # user_b should be notified (offline, not sender)
        call_users = [c.kwargs["user"] for c in mock_ns.send.call_args_list]
        call_user_ids = [u.id for u in call_users]
        assert user_b.id in call_user_ids

    @patch("apps.chat.services.ChatService._is_rate_limited", return_value=False)
    @patch("apps.chat.presence.PresenceManager")
    def test_skips_online_participant(
        self, mock_pm, mock_rl, group_conversation, message_in_group
    ):
        mock_pm.is_online.return_value = True
        mock_ns = MagicMock()

        ChatService._notify_new_message(
            mock_ns, message=message_in_group, conversation=group_conversation
        )

        mock_ns.send.assert_not_called()

    @patch("apps.chat.presence.PresenceManager")
    def test_skips_rate_limited_participant(
        self, mock_pm, group_conversation, message_in_group
    ):
        mock_pm.is_online.return_value = False
        mock_ns = MagicMock()

        with patch.object(ChatService, "_is_rate_limited", return_value=True):
            ChatService._notify_new_message(
                mock_ns, message=message_in_group, conversation=group_conversation
            )

        mock_ns.send.assert_not_called()

    @patch("apps.chat.services.ChatService._is_rate_limited", return_value=False)
    @patch("apps.chat.presence.PresenceManager")
    def test_skips_sender(
        self, mock_pm, mock_rl, group_conversation, message_in_group, user
    ):
        mock_pm.is_online.return_value = False
        mock_ns = MagicMock()

        ChatService._notify_new_message(
            mock_ns, message=message_in_group, conversation=group_conversation
        )

        call_user_ids = [c.kwargs["user"].id for c in mock_ns.send.call_args_list]
        assert user.id not in call_user_ids

    @patch("apps.chat.services.ChatService._is_rate_limited", return_value=False)
    @patch("apps.chat.presence.PresenceManager")
    def test_skips_muted_participant(
        self, mock_pm, mock_rl, group_conversation, message_in_group, user_b
    ):
        """Muted participants should not receive notifications."""
        mock_pm.is_online.return_value = False
        mock_ns = MagicMock()

        # Mute user_b's participation
        p = ConversationParticipant.objects.get(
            conversation=group_conversation,
            participant_id=user_b.id,
        )
        p.is_muted = True
        p.save(update_fields=["is_muted"])

        ChatService._notify_new_message(
            mock_ns, message=message_in_group, conversation=group_conversation
        )

        # user_b should NOT be in the notified users
        call_user_ids = [c.kwargs["user"].id for c in mock_ns.send.call_args_list]
        assert user_b.id not in call_user_ids

    @patch("apps.chat.services.ChatService._is_rate_limited", return_value=False)
    @patch("apps.chat.presence.PresenceManager")
    def test_muted_participant_does_not_block_others(
        self, mock_pm, mock_rl, group_conversation, message_in_group, user_b, user_c
    ):
        """Muting one participant doesn't affect notifications for others."""
        mock_pm.is_online.return_value = False
        mock_ns = MagicMock()

        # Mute only user_b
        p = ConversationParticipant.objects.get(
            conversation=group_conversation,
            participant_id=user_b.id,
        )
        p.is_muted = True
        p.save(update_fields=["is_muted"])

        ChatService._notify_new_message(
            mock_ns, message=message_in_group, conversation=group_conversation
        )

        # user_c should still be notified
        call_user_ids = [c.kwargs["user"].id for c in mock_ns.send.call_args_list]
        assert user_c.id in call_user_ids
        assert user_b.id not in call_user_ids

    @patch("apps.chat.services.ChatService._is_rate_limited", return_value=False)
    @patch("apps.chat.presence.PresenceManager")
    def test_notification_context_shape(
        self, mock_pm, mock_rl, dm_conversation, user, user_b
    ):
        mock_pm.is_online.return_value = False
        mock_ns = MagicMock()

        msg = Message.objects.create(
            conversation=dm_conversation,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            content="Test message",
            content_type="text",
            sequence_number=1,
        )

        ChatService._notify_new_message(
            mock_ns, message=msg, conversation=dm_conversation
        )

        mock_ns.send.assert_called_once()
        ctx = mock_ns.send.call_args.kwargs["context"]
        assert "conversation_id" in ctx
        assert "sender_name" in ctx
        assert "preview" in ctx


# =============================================================================
# _notify_request_received
# =============================================================================


@pytest.mark.django_db
class TestNotifyRequestReceived:
    def test_sends_notification_to_recipient(self, user, user_b):
        mock_ns = MagicMock()
        conv = MagicMock()
        conv.id = uuid.uuid4()
        conv.scope_type = "global"
        conv.scope_id = None

        ChatService._notify_request_received(
            mock_ns,
            conversation=conv,
            requester_name="alice",
            recipient_user=user_b,
        )

        mock_ns.send.assert_called_once()
        assert mock_ns.send.call_args.kwargs["user"] == user_b
        assert (
            mock_ns.send.call_args.kwargs["notification_type"]
            == "chat_request_received"
        )


# =============================================================================
# _notify_request_accepted
# =============================================================================


@pytest.mark.django_db
class TestNotifyRequestAccepted:
    def test_sends_notification_to_requester(self, user):
        mock_ns = MagicMock()
        conv = MagicMock()
        conv.id = uuid.uuid4()
        conv.scope_type = "global"
        conv.scope_id = None

        ChatService._notify_request_accepted(
            mock_ns,
            conversation=conv,
            accepter_name="bob",
            requester_user=user,
        )

        mock_ns.send.assert_called_once()
        assert mock_ns.send.call_args.kwargs["user"] == user
        assert (
            mock_ns.send.call_args.kwargs["notification_type"]
            == "chat_request_accepted"
        )


# =============================================================================
# _notify_group_added
# =============================================================================


@pytest.mark.django_db
class TestNotifyGroupAdded:
    def test_sends_notification_to_added_user(self, user_c):
        mock_ns = MagicMock()
        conv = MagicMock()
        conv.id = uuid.uuid4()
        conv.name = "Dev Chat"
        conv.scope_type = "global"
        conv.scope_id = None

        ChatService._notify_group_added(
            mock_ns,
            conversation=conv,
            added_user=user_c,
            added_by_name="alice",
        )

        mock_ns.send.assert_called_once()
        ctx = mock_ns.send.call_args.kwargs["context"]
        assert ctx["group_name"] == "Dev Chat"
        assert ctx["added_by_name"] == "alice"
        assert mock_ns.send.call_args.kwargs["notification_type"] == "chat_group_added"


# =============================================================================
# on_commit WIRING
# =============================================================================


@pytest.mark.django_db
class TestOnCommitWiring:
    def test_send_message_triggers_notification(
        self, dm_conversation, user, immediate_on_commit
    ):
        with patch.object(ChatService, "_notify_safe") as mock_notify:
            ChatService.send_message(
                conversation_id=dm_conversation.id,
                sender_type=ParticipantType.USER,
                sender_id=user.id,
                acting_user_id=user.id,
                content="Hello!",
            )
        mock_notify.assert_called_once()
        assert mock_notify.call_args[0][0] == "new_message"
        assert "message" in mock_notify.call_args[1]
        assert "conversation" in mock_notify.call_args[1]

    def test_accept_request_triggers_notification(
        self, user, user_b, immediate_on_commit
    ):
        conv = Conversation.objects.create(
            scope_type=ScopeType.GLOBAL,
            conversation_type=ConversationType.DIRECT,
            created_by_type=ParticipantType.USER,
            created_by_id=user.id,
        )
        ConversationParticipant.objects.create(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            role=ParticipantRole.MEMBER,
            request_status=RequestStatus.NONE,
        )
        ConversationParticipant.objects.create(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user_b.id,
            role=ParticipantRole.MEMBER,
            request_status=RequestStatus.PENDING,
        )

        with patch.object(ChatService, "_notify_safe") as mock_notify:
            ChatService.accept_request(conversation_id=conv.id, user=user_b)

        mock_notify.assert_called_once()
        assert mock_notify.call_args[0][0] == "request_accepted"

    def test_add_participant_triggers_notification(
        self, group_conversation, user, immediate_on_commit
    ):
        new_user = UserFactory(is_verified=True)
        with patch.object(ChatService, "_notify_safe") as mock_notify:
            ChatService.add_participant(
                conversation_id=group_conversation.id,
                participant_type=ParticipantType.USER,
                participant_id=new_user.id,
                added_by=user,
            )

        mock_notify.assert_called_once()
        assert mock_notify.call_args[0][0] == "group_added"

    def test_notification_handler_failure_doesnt_fail_service(
        self, dm_conversation, user, immediate_on_commit
    ):
        """_notify_safe catches handler exceptions, so service still succeeds."""
        with patch.object(
            ChatService,
            "_notify_new_message",
            side_effect=Exception("handler broken"),
        ):
            message = ChatService.send_message(
                conversation_id=dm_conversation.id,
                sender_type=ParticipantType.USER,
                sender_id=user.id,
                acting_user_id=user.id,
                content="This should still save",
            )

        assert message is not None
        assert Message.objects.filter(id=message.id).exists()
