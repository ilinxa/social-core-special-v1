"""
WS Serializer Tests
===================
Tests for lightweight dict-based WebSocket event serializers.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from apps.chat.ws_serializers import (
    serialize_delivered_update,
    serialize_message,
    serialize_message_deleted,
    serialize_message_edited,
    serialize_presence,
    serialize_seen_update,
    serialize_typing,
)


class TestSerializeMessage:
    def test_full_message_shape(self):
        msg = MagicMock()
        msg.id = uuid.uuid4()
        msg.conversation_id = uuid.uuid4()
        msg.sender_type = "user"
        msg.sender_id = uuid.uuid4()
        msg.content_type = "text"
        msg.content = "Hello world"
        msg.status = "active"
        msg.sequence_number = 1
        msg.edited_at = None
        msg.created_at = datetime(2026, 3, 20, 12, 0, 0, tzinfo=timezone.utc)

        mock_att_qs = MagicMock()
        mock_att_qs.order_by.return_value = []

        with (
            patch(
                "apps.chat.ws_serializers._resolve_participant_display",
                return_value=("Alice", "https://example.com/avatar.jpg"),
            ),
            patch(
                "apps.chat.models.MessageAttachment.objects.filter",
                return_value=mock_att_qs,
            ),
        ):
            result = serialize_message(msg)

        assert result["id"] == str(msg.id)
        assert result["conversation_id"] == str(msg.conversation_id)
        assert result["sender_type"] == "user"
        assert result["sender_id"] == str(msg.sender_id)
        assert result["sender_name"] == "Alice"
        assert result["sender_avatar_url"] == "https://example.com/avatar.jpg"
        assert result["content_type"] == "text"
        assert result["content"] == "Hello world"
        assert result["status"] == "active"
        assert result["sequence_number"] == 1
        assert result["edited_at"] is None
        assert result["created_at"] == "2026-03-20T12:00:00+00:00"
        assert result["attachments"] == []

    def test_uuids_are_strings(self):
        msg = MagicMock()
        msg.id = uuid.uuid4()
        msg.conversation_id = uuid.uuid4()
        msg.sender_type = "user"
        msg.sender_id = uuid.uuid4()
        msg.content_type = "text"
        msg.content = "test"
        msg.status = "active"
        msg.sequence_number = 1
        msg.edited_at = None
        msg.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

        mock_att_qs = MagicMock()
        mock_att_qs.order_by.return_value = []

        with (
            patch(
                "apps.chat.ws_serializers._resolve_participant_display",
                return_value=("", None),
            ),
            patch(
                "apps.chat.models.MessageAttachment.objects.filter",
                return_value=mock_att_qs,
            ),
        ):
            result = serialize_message(msg)

        # All UUID fields must be strings
        assert isinstance(result["id"], str)
        assert isinstance(result["conversation_id"], str)
        assert isinstance(result["sender_id"], str)


class TestSerializeMessageEdited:
    def test_edited_shape(self):
        msg = MagicMock()
        msg.conversation_id = uuid.uuid4()
        msg.id = uuid.uuid4()
        msg.content = "Edited content"
        msg.edited_at = datetime(2026, 3, 20, 12, 5, 0, tzinfo=timezone.utc)

        result = serialize_message_edited(msg)

        assert result["conversation_id"] == str(msg.conversation_id)
        assert result["message_id"] == str(msg.id)
        assert result["content"] == "Edited content"
        assert result["edited_at"] == "2026-03-20T12:05:00+00:00"


class TestSerializeOtherEvents:
    def test_typing_shape(self):
        conv_id = uuid.uuid4()
        user_id = uuid.uuid4()
        result = serialize_typing(conv_id, user_id, True)

        assert result["conversation_id"] == str(conv_id)
        assert result["user_id"] == str(user_id)
        assert result["is_typing"] is True

    def test_seen_update_shape(self):
        conv_id = uuid.uuid4()
        pid = uuid.uuid4()
        msg_id = uuid.uuid4()
        result = serialize_seen_update(conv_id, pid, msg_id)

        assert result["conversation_id"] == str(conv_id)
        assert result["participant_id"] == str(pid)
        assert result["last_seen_message_id"] == str(msg_id)

    def test_delivered_update_shape(self):
        conv_id = uuid.uuid4()
        pid = uuid.uuid4()
        msg_id = uuid.uuid4()
        result = serialize_delivered_update(conv_id, pid, msg_id)

        assert result["conversation_id"] == str(conv_id)
        assert result["participant_id"] == str(pid)
        assert result["last_delivered_message_id"] == str(msg_id)

    def test_presence_shape(self):
        user_id = uuid.uuid4()
        result = serialize_presence(user_id, True)

        assert result["user_id"] == str(user_id)
        assert result["is_online"] is True

    def test_message_deleted_shape(self):
        msg = MagicMock()
        msg.conversation_id = uuid.uuid4()
        msg.id = uuid.uuid4()

        result = serialize_message_deleted(msg)

        assert result["conversation_id"] == str(msg.conversation_id)
        assert result["message_id"] == str(msg.id)
