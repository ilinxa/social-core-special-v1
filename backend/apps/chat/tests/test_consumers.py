"""
Chat Consumer Tests
===================
Tests for the WebSocket ChatConsumer.
All DB and presence calls are mocked to isolate consumer logic.
Uses InMemoryChannelLayer from local settings.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from channels.testing import WebsocketCommunicator
from django.test import override_settings

from apps.chat.consumers import ChatConsumer

# Consumer tests are unit tests with all DB/presence calls mocked.
# Force InMemoryChannelLayer regardless of which settings module is active
# (local_docker uses RedisChannelLayer which breaks WebsocketCommunicator).
_IN_MEMORY_CHANNEL_LAYER = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
}

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.usefixtures("_force_in_memory_channel_layer"),
]


@pytest.fixture(autouse=True)
def _force_in_memory_channel_layer(settings):
    """Override CHANNEL_LAYERS to InMemoryChannelLayer for consumer unit tests."""
    settings.CHANNEL_LAYERS = _IN_MEMORY_CHANNEL_LAYER


# =============================================================================
# HELPERS
# =============================================================================


def _make_user(user_id=None):
    """Create a mock authenticated user."""
    user = MagicMock()
    user.id = user_id or uuid.uuid4()
    user.is_authenticated = True
    return user


def _make_communicator(user=None):
    """Create a WebsocketCommunicator with an authenticated user scope."""
    communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), "/ws/chat/")
    if user:
        communicator.scope["user"] = user
    return communicator


def _consumer_patches(conversation_ids=None):
    """Return common patches for consumer tests."""
    return {
        "get_convs": patch.object(
            ChatConsumer,
            "_get_user_conversation_ids",
            new=AsyncMock(return_value=conversation_ids or []),
        ),
        "presence_on": patch.object(
            ChatConsumer,
            "_set_presence_online",
            new=AsyncMock(),
        ),
        "presence_off": patch.object(
            ChatConsumer,
            "_set_presence_offline",
            new=AsyncMock(),
        ),
        "heartbeat": patch.object(
            ChatConsumer,
            "_heartbeat_loop",
            new=AsyncMock(),
        ),
        "broadcast_presence": patch.object(
            ChatConsumer,
            "_broadcast_presence",
            new=AsyncMock(),
        ),
    }


# =============================================================================
# CONNECTION TESTS
# =============================================================================


class TestConnection:
    async def test_auth_via_scope(self):
        """User authenticated via JWTAuthMiddleware connects successfully."""
        user = _make_user()
        patches = _consumer_patches()
        with patches["get_convs"], patches["presence_on"], patches["heartbeat"]:
            communicator = _make_communicator(user)
            connected, _ = await communicator.connect()
            assert connected is True
            await communicator.disconnect()

    async def test_unauthenticated_connect_waits_for_auth(self):
        """Unauthenticated user can connect but messages are rejected."""
        from django.contrib.auth.models import AnonymousUser

        communicator = _make_communicator(AnonymousUser())
        connected, _ = await communicator.connect()
        assert connected is True

        # Sending a non-auth message should get error
        await communicator.send_json_to({"type": "message.send"})
        response = await communicator.receive_json_from(timeout=2)
        assert response["type"] == "error"
        assert response["code"] == "not_authenticated"
        await communicator.disconnect()

    async def test_group_join_on_connect(self):
        """Consumer joins conversation groups on authentication."""
        user = _make_user()
        conv_id = uuid.uuid4()
        patches = _consumer_patches(conversation_ids=[conv_id])

        with patches["get_convs"], patches["presence_on"], patches["heartbeat"]:
            communicator = _make_communicator(user)
            connected, _ = await communicator.connect()
            assert connected is True
            await communicator.disconnect()

    async def test_presence_set_on_connect(self):
        """Presence is set to online on successful connection."""
        user = _make_user()
        mock_presence_on = AsyncMock()

        with (
            patch.object(
                ChatConsumer,
                "_get_user_conversation_ids",
                new=AsyncMock(return_value=[]),
            ),
            patch.object(
                ChatConsumer,
                "_set_presence_online",
                new=mock_presence_on,
            ),
            patch.object(
                ChatConsumer,
                "_heartbeat_loop",
                new=AsyncMock(),
            ),
        ):
            communicator = _make_communicator(user)
            await communicator.connect()
            mock_presence_on.assert_called_with(user.id)
            await communicator.disconnect()

    async def test_presence_cleared_on_disconnect(self):
        """Presence is cleared when user disconnects."""
        user = _make_user()
        mock_presence_off = AsyncMock()

        patches = _consumer_patches()
        with (
            patches["get_convs"],
            patches["presence_on"],
            patches["heartbeat"],
            patch.object(
                ChatConsumer,
                "_set_presence_offline",
                new=mock_presence_off,
            ),
            patches["broadcast_presence"],
        ):
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.disconnect()
            mock_presence_off.assert_called_with(user.id)

    async def test_disconnect_broadcasts_offline(self):
        """Disconnect broadcasts presence offline to subscribers."""
        user = _make_user()
        mock_broadcast = AsyncMock()

        patches = _consumer_patches()
        with (
            patches["get_convs"],
            patches["presence_on"],
            patches["heartbeat"],
            patches["presence_off"],
            patch.object(
                ChatConsumer,
                "_broadcast_presence",
                new=mock_broadcast,
            ),
        ):
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.disconnect()
            mock_broadcast.assert_called_with(str(user.id), is_online=False)


# =============================================================================
# MESSAGE SEND TESTS
# =============================================================================


class TestMessageSend:
    async def test_send_message_calls_service(self):
        """message.send event calls ChatService.send_message."""
        user = _make_user()
        conv_id = uuid.uuid4()
        mock_msg = MagicMock()
        mock_msg.id = uuid.uuid4()
        mock_msg.conversation_id = conv_id
        mock_msg.sender_type = "user"
        mock_msg.sender_id = user.id
        mock_msg.content_type = "text"
        mock_msg.content = "Hello"
        mock_msg.status = "active"
        mock_msg.sequence_number = 1
        mock_msg.edited_at = None
        mock_msg.created_at = MagicMock()
        mock_msg.created_at.isoformat.return_value = "2026-03-20T12:00:00Z"

        patches = _consumer_patches(conversation_ids=[conv_id])
        mock_att_qs = MagicMock()
        mock_att_qs.order_by.return_value = []
        with (
            patches["get_convs"],
            patches["presence_on"],
            patches["heartbeat"],
            patch.object(
                ChatConsumer,
                "_db_send_message",
                new=AsyncMock(return_value=mock_msg),
            ),
            patch(
                "apps.chat.ws_serializers._resolve_participant_display",
                return_value=("Alice", None),
            ),
            patch(
                "apps.chat.models.MessageAttachment.objects.filter",
                return_value=mock_att_qs,
            ),
        ):
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to(
                {
                    "type": "message.send",
                    "conversation_id": str(conv_id),
                    "content": "Hello",
                }
            )
            response = await communicator.receive_json_from(timeout=2)
            assert response["type"] == "message.new"
            assert response["content"] == "Hello"
            await communicator.disconnect()

    async def test_send_message_missing_content_returns_error(self):
        """message.send without content returns validation error."""
        user = _make_user()
        patches = _consumer_patches()
        with patches["get_convs"], patches["presence_on"], patches["heartbeat"]:
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to(
                {
                    "type": "message.send",
                    "conversation_id": str(uuid.uuid4()),
                }
            )
            response = await communicator.receive_json_from(timeout=2)
            assert response["type"] == "error"
            assert response["code"] == "invalid_payload"
            await communicator.disconnect()

    async def test_send_message_missing_conversation_returns_error(self):
        """message.send without conversation_id returns validation error."""
        user = _make_user()
        patches = _consumer_patches()
        with patches["get_convs"], patches["presence_on"], patches["heartbeat"]:
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to(
                {
                    "type": "message.send",
                    "content": "Hello",
                }
            )
            response = await communicator.receive_json_from(timeout=2)
            assert response["type"] == "error"
            assert response["code"] == "invalid_payload"
            await communicator.disconnect()

    async def test_send_message_entity_sender(self):
        """message.send with entity sender passes correct acting_user_id."""
        user = _make_user()
        conv_id = uuid.uuid4()
        biz_id = uuid.uuid4()
        mock_msg = MagicMock()
        mock_msg.id = uuid.uuid4()
        mock_msg.conversation_id = conv_id
        mock_msg.sender_type = "business"
        mock_msg.sender_id = biz_id
        mock_msg.content_type = "text"
        mock_msg.content = "Hi from biz"
        mock_msg.status = "active"
        mock_msg.sequence_number = 1
        mock_msg.edited_at = None
        mock_msg.created_at = MagicMock()
        mock_msg.created_at.isoformat.return_value = "2026-03-20T12:00:00Z"

        mock_db_send = AsyncMock(return_value=mock_msg)
        patches = _consumer_patches(conversation_ids=[conv_id])
        mock_att_qs = MagicMock()
        mock_att_qs.order_by.return_value = []

        with (
            patches["get_convs"],
            patches["presence_on"],
            patches["heartbeat"],
            patch.object(ChatConsumer, "_db_send_message", new=mock_db_send),
            patch(
                "apps.chat.ws_serializers._resolve_participant_display",
                return_value=("Biz", None),
            ),
            patch(
                "apps.chat.models.MessageAttachment.objects.filter",
                return_value=mock_att_qs,
            ),
        ):
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to(
                {
                    "type": "message.send",
                    "conversation_id": str(conv_id),
                    "content": "Hi from biz",
                    "sender_type": "business",
                    "sender_id": str(biz_id),
                }
            )
            response = await communicator.receive_json_from(timeout=2)
            assert response["type"] == "message.new"
            assert response["sender_type"] == "business"

            # Verify acting_user_id was passed
            call_kwargs = mock_db_send.call_args
            assert call_kwargs[1]["acting_user_id"] == user.id
            await communicator.disconnect()

    async def test_send_message_service_error(self):
        """Service exception is mapped to WS error event."""
        user = _make_user()
        patches = _consumer_patches()

        from apps.core.exceptions import PermissionDenied

        with (
            patches["get_convs"],
            patches["presence_on"],
            patches["heartbeat"],
            patch.object(
                ChatConsumer,
                "_db_send_message",
                new=AsyncMock(
                    side_effect=PermissionDenied(
                        message="Not allowed",
                        action="send_message",
                        resource="Conversation",
                    )
                ),
            ),
        ):
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to(
                {
                    "type": "message.send",
                    "conversation_id": str(uuid.uuid4()),
                    "content": "test",
                }
            )
            response = await communicator.receive_json_from(timeout=2)
            assert response["type"] == "error"
            assert response["code"] == "permission_denied"
            await communicator.disconnect()

    async def test_send_message_validation_error(self):
        """ValidationError from service is mapped correctly."""
        user = _make_user()
        patches = _consumer_patches()

        from apps.core.exceptions import ValidationError

        with (
            patches["get_convs"],
            patches["presence_on"],
            patches["heartbeat"],
            patch.object(
                ChatConsumer,
                "_db_send_message",
                new=AsyncMock(
                    side_effect=ValidationError(
                        message="Content too long", field="content"
                    )
                ),
            ),
        ):
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to(
                {
                    "type": "message.send",
                    "conversation_id": str(uuid.uuid4()),
                    "content": "test",
                }
            )
            response = await communicator.receive_json_from(timeout=2)
            assert response["type"] == "error"
            assert response["code"] == "validation_error"
            await communicator.disconnect()

    async def test_send_message_business_rule_error(self):
        """BusinessRuleViolation from service is mapped correctly."""
        user = _make_user()
        patches = _consumer_patches()

        from apps.core.exceptions import BusinessRuleViolation

        with (
            patches["get_convs"],
            patches["presence_on"],
            patches["heartbeat"],
            patch.object(
                ChatConsumer,
                "_db_send_message",
                new=AsyncMock(
                    side_effect=BusinessRuleViolation(
                        message="Request limit",
                        rule="request_message_limit",
                    )
                ),
            ),
        ):
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to(
                {
                    "type": "message.send",
                    "conversation_id": str(uuid.uuid4()),
                    "content": "test",
                }
            )
            response = await communicator.receive_json_from(timeout=2)
            assert response["type"] == "error"
            assert response["code"] == "business_rule_violation"
            await communicator.disconnect()


# =============================================================================
# MESSAGE EDIT/DELETE TESTS
# =============================================================================


class TestMessageEditDelete:
    async def test_edit_message_broadcasts(self):
        """message.edit broadcasts message.edited to conversation."""
        user = _make_user()
        conv_id = uuid.uuid4()
        msg_id = uuid.uuid4()
        mock_msg = MagicMock()
        mock_msg.id = msg_id
        mock_msg.conversation_id = conv_id
        mock_msg.content = "Edited"
        mock_msg.edited_at = MagicMock()
        mock_msg.edited_at.isoformat.return_value = "2026-03-20T12:05:00Z"

        patches = _consumer_patches(conversation_ids=[conv_id])
        with (
            patches["get_convs"],
            patches["presence_on"],
            patches["heartbeat"],
            patch.object(
                ChatConsumer,
                "_db_edit_message",
                new=AsyncMock(return_value=mock_msg),
            ),
        ):
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to(
                {
                    "type": "message.edit",
                    "message_id": str(msg_id),
                    "content": "Edited",
                }
            )
            response = await communicator.receive_json_from(timeout=2)
            assert response["type"] == "message.edited"
            assert response["content"] == "Edited"
            assert response["message_id"] == str(msg_id)
            await communicator.disconnect()

    async def test_edit_message_missing_fields_returns_error(self):
        """message.edit without required fields returns error."""
        user = _make_user()
        patches = _consumer_patches()
        with patches["get_convs"], patches["presence_on"], patches["heartbeat"]:
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to(
                {
                    "type": "message.edit",
                    "message_id": str(uuid.uuid4()),
                }
            )
            response = await communicator.receive_json_from(timeout=2)
            assert response["type"] == "error"
            assert response["code"] == "invalid_payload"
            await communicator.disconnect()

    async def test_delete_message_broadcasts(self):
        """message.delete broadcasts message.deleted to conversation."""
        user = _make_user()
        conv_id = uuid.uuid4()
        msg_id = uuid.uuid4()
        mock_msg = MagicMock()
        mock_msg.id = msg_id
        mock_msg.conversation_id = conv_id

        patches = _consumer_patches(conversation_ids=[conv_id])
        with (
            patches["get_convs"],
            patches["presence_on"],
            patches["heartbeat"],
            patch.object(
                ChatConsumer,
                "_db_get_message",
                new=AsyncMock(return_value=mock_msg),
            ),
            patch.object(
                ChatConsumer,
                "_db_delete_message",
                new=AsyncMock(),
            ),
        ):
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to(
                {
                    "type": "message.delete",
                    "message_id": str(msg_id),
                }
            )
            response = await communicator.receive_json_from(timeout=2)
            assert response["type"] == "message.deleted"
            assert response["message_id"] == str(msg_id)
            await communicator.disconnect()

    async def test_delete_message_missing_id_returns_error(self):
        """message.delete without message_id returns error."""
        user = _make_user()
        patches = _consumer_patches()
        with patches["get_convs"], patches["presence_on"], patches["heartbeat"]:
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to({"type": "message.delete"})
            response = await communicator.receive_json_from(timeout=2)
            assert response["type"] == "error"
            assert response["code"] == "invalid_payload"
            await communicator.disconnect()


# =============================================================================
# TYPING TESTS
# =============================================================================


class TestTyping:
    async def test_typing_start_broadcasts(self):
        """typing.start broadcasts to conversation group."""
        user = _make_user()
        conv_id = uuid.uuid4()
        patches = _consumer_patches(conversation_ids=[conv_id])

        with patches["get_convs"], patches["presence_on"], patches["heartbeat"]:
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to(
                {
                    "type": "typing.start",
                    "conversation_id": str(conv_id),
                }
            )
            # The sender is excluded (no self-echo), so we should NOT receive
            # a typing event back. receive_nothing returns True if queue is empty.
            assert await communicator.receive_nothing(timeout=0.5) is True
            await communicator.disconnect()

    async def test_typing_stop_broadcasts(self):
        """typing.stop broadcasts to conversation group."""
        user = _make_user()
        conv_id = uuid.uuid4()
        patches = _consumer_patches(conversation_ids=[conv_id])

        with patches["get_convs"], patches["presence_on"], patches["heartbeat"]:
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to(
                {
                    "type": "typing.stop",
                    "conversation_id": str(conv_id),
                }
            )
            # No self-echo expected
            assert await communicator.receive_nothing(timeout=0.5) is True
            await communicator.disconnect()

    async def test_typing_missing_conversation_returns_error(self):
        """typing.start without conversation_id returns error."""
        user = _make_user()
        patches = _consumer_patches()
        with patches["get_convs"], patches["presence_on"], patches["heartbeat"]:
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to({"type": "typing.start"})
            response = await communicator.receive_json_from(timeout=2)
            assert response["type"] == "error"
            assert response["code"] == "invalid_payload"
            await communicator.disconnect()

    async def test_typing_no_self_echo(self):
        """Typing events should not be echoed back to sender."""
        user = _make_user()
        conv_id = uuid.uuid4()
        patches = _consumer_patches(conversation_ids=[conv_id])

        with patches["get_convs"], patches["presence_on"], patches["heartbeat"]:
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to(
                {
                    "type": "typing.start",
                    "conversation_id": str(conv_id),
                }
            )
            # If self-echo was happening, we'd get a typing event.
            # We should NOT receive anything.
            assert await communicator.receive_nothing(timeout=0.5) is True
            await communicator.disconnect()


# =============================================================================
# WATERMARK TESTS
# =============================================================================


class TestWatermarks:
    async def test_seen_update_calls_service_and_broadcasts(self):
        """seen event updates watermark and broadcasts."""
        user = _make_user()
        conv_id = uuid.uuid4()
        msg_id = uuid.uuid4()
        mock_db_seen = AsyncMock()
        patches = _consumer_patches(conversation_ids=[conv_id])

        with (
            patches["get_convs"],
            patches["presence_on"],
            patches["heartbeat"],
            patch.object(ChatConsumer, "_db_update_seen", new=mock_db_seen),
        ):
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to(
                {
                    "type": "seen",
                    "conversation_id": str(conv_id),
                    "last_seen_message_id": str(msg_id),
                }
            )
            response = await communicator.receive_json_from(timeout=2)
            assert response["type"] == "seen.update"
            assert response["conversation_id"] == str(conv_id)
            assert response["last_seen_message_id"] == str(msg_id)
            mock_db_seen.assert_called_once()
            await communicator.disconnect()

    async def test_delivered_update_calls_service_and_broadcasts(self):
        """delivered event updates watermark and broadcasts."""
        user = _make_user()
        conv_id = uuid.uuid4()
        msg_id = uuid.uuid4()
        mock_db_delivered = AsyncMock()
        patches = _consumer_patches(conversation_ids=[conv_id])

        with (
            patches["get_convs"],
            patches["presence_on"],
            patches["heartbeat"],
            patch.object(ChatConsumer, "_db_update_delivered", new=mock_db_delivered),
        ):
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to(
                {
                    "type": "delivered",
                    "conversation_id": str(conv_id),
                    "last_delivered_message_id": str(msg_id),
                }
            )
            response = await communicator.receive_json_from(timeout=2)
            assert response["type"] == "delivered.update"
            assert response["conversation_id"] == str(conv_id)
            assert response["last_delivered_message_id"] == str(msg_id)
            mock_db_delivered.assert_called_once()
            await communicator.disconnect()

    async def test_seen_missing_fields_returns_error(self):
        """seen without required fields returns error."""
        user = _make_user()
        patches = _consumer_patches()
        with patches["get_convs"], patches["presence_on"], patches["heartbeat"]:
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to(
                {
                    "type": "seen",
                    "conversation_id": str(uuid.uuid4()),
                }
            )
            response = await communicator.receive_json_from(timeout=2)
            assert response["type"] == "error"
            assert response["code"] == "invalid_payload"
            await communicator.disconnect()

    async def test_delivered_missing_fields_returns_error(self):
        """delivered without required fields returns error."""
        user = _make_user()
        patches = _consumer_patches()
        with patches["get_convs"], patches["presence_on"], patches["heartbeat"]:
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to(
                {
                    "type": "delivered",
                    "conversation_id": str(uuid.uuid4()),
                }
            )
            response = await communicator.receive_json_from(timeout=2)
            assert response["type"] == "error"
            assert response["code"] == "invalid_payload"
            await communicator.disconnect()


# =============================================================================
# PRESENCE TESTS
# =============================================================================


class TestPresence:
    async def test_presence_subscribe_sends_initial_status(self):
        """presence.subscribe sends current status for subscribed users."""
        user = _make_user()
        target_uid = uuid.uuid4()

        patches = _consumer_patches()
        with (
            patches["get_convs"],
            patches["presence_on"],
            patches["heartbeat"],
            patch.object(
                ChatConsumer,
                "_get_online_users",
                new=AsyncMock(return_value={str(target_uid): True}),
            ),
        ):
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to(
                {
                    "type": "presence.subscribe",
                    "user_ids": [str(target_uid)],
                }
            )
            response = await communicator.receive_json_from(timeout=2)
            assert response["type"] == "presence"
            assert response["user_id"] == str(target_uid)
            assert response["is_online"] is True
            await communicator.disconnect()

    async def test_presence_subscribe_invalid_payload(self):
        """presence.subscribe with non-list user_ids returns error."""
        user = _make_user()
        patches = _consumer_patches()
        with patches["get_convs"], patches["presence_on"], patches["heartbeat"]:
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to(
                {
                    "type": "presence.subscribe",
                    "user_ids": "not-a-list",
                }
            )
            response = await communicator.receive_json_from(timeout=2)
            assert response["type"] == "error"
            assert response["code"] == "invalid_payload"
            await communicator.disconnect()

    async def test_presence_subscribe_too_many(self):
        """presence.subscribe with too many user_ids returns error."""
        user = _make_user()
        patches = _consumer_patches()
        with patches["get_convs"], patches["presence_on"], patches["heartbeat"]:
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to(
                {
                    "type": "presence.subscribe",
                    "user_ids": [str(uuid.uuid4()) for _ in range(51)],
                }
            )
            response = await communicator.receive_json_from(timeout=2)
            assert response["type"] == "error"
            assert response["code"] == "too_many_subscriptions"
            await communicator.disconnect()

    async def test_presence_subscribe_replaces_previous(self):
        """Second presence.subscribe replaces the first."""
        user = _make_user()
        uid1 = uuid.uuid4()
        uid2 = uuid.uuid4()

        patches = _consumer_patches()
        with (
            patches["get_convs"],
            patches["presence_on"],
            patches["heartbeat"],
            patch.object(
                ChatConsumer,
                "_get_online_users",
                new=AsyncMock(return_value={}),
            ),
        ):
            communicator = _make_communicator(user)
            await communicator.connect()

            # First subscribe
            await communicator.send_json_to(
                {
                    "type": "presence.subscribe",
                    "user_ids": [str(uid1)],
                }
            )
            # No responses since _get_online_users returns empty

            # Second subscribe (should replace)
            await communicator.send_json_to(
                {
                    "type": "presence.subscribe",
                    "user_ids": [str(uid2)],
                }
            )
            await communicator.disconnect()


# =============================================================================
# CONVERSATION GROUP MANAGEMENT TESTS
# =============================================================================


class TestGroupManagement:
    async def test_conversation_join_participant(self):
        """conversation.join succeeds for verified participant."""
        user = _make_user()
        conv_id = uuid.uuid4()

        patches = _consumer_patches()
        with (
            patches["get_convs"],
            patches["presence_on"],
            patches["heartbeat"],
            patch.object(
                ChatConsumer,
                "_db_is_participant",
                new=AsyncMock(return_value=True),
            ),
        ):
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to(
                {
                    "type": "conversation.join",
                    "conversation_id": str(conv_id),
                }
            )
            # No response expected (success is silent)
            assert await communicator.receive_nothing(timeout=0.5) is True
            await communicator.disconnect()

    async def test_conversation_join_non_participant_rejected(self):
        """conversation.join fails for non-participant."""
        user = _make_user()
        conv_id = uuid.uuid4()

        patches = _consumer_patches()
        with (
            patches["get_convs"],
            patches["presence_on"],
            patches["heartbeat"],
            patch.object(
                ChatConsumer,
                "_db_is_participant",
                new=AsyncMock(return_value=False),
            ),
        ):
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to(
                {
                    "type": "conversation.join",
                    "conversation_id": str(conv_id),
                }
            )
            response = await communicator.receive_json_from(timeout=2)
            assert response["type"] == "error"
            assert response["code"] == "not_participant"
            await communicator.disconnect()

    async def test_conversation_leave(self):
        """conversation.leave removes from group."""
        user = _make_user()
        conv_id = uuid.uuid4()

        patches = _consumer_patches(conversation_ids=[conv_id])
        with patches["get_convs"], patches["presence_on"], patches["heartbeat"]:
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to(
                {
                    "type": "conversation.leave",
                    "conversation_id": str(conv_id),
                }
            )
            # No response expected (success is silent)
            assert await communicator.receive_nothing(timeout=0.5) is True
            await communicator.disconnect()

    async def test_conversation_join_missing_id_returns_error(self):
        """conversation.join without conversation_id returns error."""
        user = _make_user()
        patches = _consumer_patches()
        with patches["get_convs"], patches["presence_on"], patches["heartbeat"]:
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to({"type": "conversation.join"})
            response = await communicator.receive_json_from(timeout=2)
            assert response["type"] == "error"
            assert response["code"] == "invalid_payload"
            await communicator.disconnect()

    async def test_conversation_leave_missing_id_returns_error(self):
        """conversation.leave without conversation_id returns error."""
        user = _make_user()
        patches = _consumer_patches()
        with patches["get_convs"], patches["presence_on"], patches["heartbeat"]:
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to({"type": "conversation.leave"})
            response = await communicator.receive_json_from(timeout=2)
            assert response["type"] == "error"
            assert response["code"] == "invalid_payload"
            await communicator.disconnect()


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestErrorHandling:
    async def test_unknown_event_type(self):
        """Unknown event type returns error."""
        user = _make_user()
        patches = _consumer_patches()
        with patches["get_convs"], patches["presence_on"], patches["heartbeat"]:
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to({"type": "nonexistent.event"})
            response = await communicator.receive_json_from(timeout=2)
            assert response["type"] == "error"
            assert response["code"] == "unknown_event"
            await communicator.disconnect()

    async def test_missing_event_type(self):
        """Missing type field returns error."""
        user = _make_user()
        patches = _consumer_patches()
        with patches["get_convs"], patches["presence_on"], patches["heartbeat"]:
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to({"data": "no type"})
            response = await communicator.receive_json_from(timeout=2)
            assert response["type"] == "error"
            assert response["code"] == "missing_type"
            await communicator.disconnect()

    async def test_internal_error_mapped(self):
        """Unexpected exception is mapped to internal_error."""
        user = _make_user()
        patches = _consumer_patches()

        with (
            patches["get_convs"],
            patches["presence_on"],
            patches["heartbeat"],
            patch.object(
                ChatConsumer,
                "_db_send_message",
                new=AsyncMock(side_effect=RuntimeError("unexpected")),
            ),
        ):
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to(
                {
                    "type": "message.send",
                    "conversation_id": str(uuid.uuid4()),
                    "content": "test",
                }
            )
            response = await communicator.receive_json_from(timeout=2)
            assert response["type"] == "error"
            assert response["code"] == "internal_error"
            await communicator.disconnect()

    async def test_not_found_error_mapped(self):
        """NotFound exception is mapped correctly."""
        user = _make_user()
        patches = _consumer_patches()

        from apps.core.exceptions import NotFound

        with (
            patches["get_convs"],
            patches["presence_on"],
            patches["heartbeat"],
            patch.object(
                ChatConsumer,
                "_db_update_seen",
                new=AsyncMock(side_effect=NotFound(resource="ConversationParticipant")),
            ),
        ):
            communicator = _make_communicator(user)
            await communicator.connect()
            await communicator.send_json_to(
                {
                    "type": "seen",
                    "conversation_id": str(uuid.uuid4()),
                    "last_seen_message_id": str(uuid.uuid4()),
                }
            )
            response = await communicator.receive_json_from(timeout=2)
            assert response["type"] == "error"
            assert response["code"] == "not_found"
            await communicator.disconnect()
