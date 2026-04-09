"""
Chat Reaction Tests
===================
Tests for preset emoji reactions on messages (Phase 4).
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.chat.constants import (
    ConversationType,
    MessageContentType,
    MessageStatus,
    ParticipantRole,
    ParticipantType,
    ReactionType,
    RequestStatus,
    ScopeType,
)
from apps.chat.models import (
    Conversation,
    ConversationParticipant,
    Message,
    MessageReaction,
)
from apps.chat.services import ChatService
from apps.users.tests.factories import UserFactory


@pytest.fixture
def message_in_dm(db, dm_conversation, user):
    return Message.objects.create(
        conversation=dm_conversation,
        sender_type=ParticipantType.USER,
        sender_id=user.id,
        content="Test message",
        content_type=MessageContentType.TEXT,
        sequence_number=1,
    )


@pytest.fixture
def message_in_group(db, group_conversation, user):
    return Message.objects.create(
        conversation=group_conversation,
        sender_type=ParticipantType.USER,
        sender_id=user.id,
        content="Group message",
        content_type=MessageContentType.TEXT,
        sequence_number=1,
    )


# =============================================================================
# ADD REACTION (SERVICE LEVEL)
# =============================================================================


@pytest.mark.django_db
class TestAddReaction:
    def test_add_reaction_like(self, message_in_dm, user_b):
        reaction = ChatService.add_reaction(
            message_id=message_in_dm.id,
            user=user_b,
            reaction=ReactionType.LIKE,
        )
        assert reaction.reaction == ReactionType.LIKE
        assert reaction.user == user_b
        assert reaction.message == message_in_dm

    def test_add_reaction_all_types(self, message_in_dm, user_b):
        for rt in ReactionType.values:
            reaction = ChatService.add_reaction(
                message_id=message_in_dm.id,
                user=user_b,
                reaction=rt,
            )
            assert reaction.reaction == rt

    def test_add_reaction_rejects_invalid_type(self, message_in_dm, user_b):
        from apps.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            ChatService.add_reaction(
                message_id=message_in_dm.id,
                user=user_b,
                reaction="invalid_emoji",
            )

    def test_add_reaction_duplicate(self, message_in_dm, user_b):
        ChatService.add_reaction(
            message_id=message_in_dm.id,
            user=user_b,
            reaction=ReactionType.LIKE,
        )
        from apps.core.exceptions import ConflictError

        with pytest.raises(ConflictError):
            ChatService.add_reaction(
                message_id=message_in_dm.id,
                user=user_b,
                reaction=ReactionType.LIKE,
            )

    def test_add_multiple_reaction_types(self, message_in_dm, user_b):
        ChatService.add_reaction(
            message_id=message_in_dm.id,
            user=user_b,
            reaction=ReactionType.LIKE,
        )
        ChatService.add_reaction(
            message_id=message_in_dm.id,
            user=user_b,
            reaction=ReactionType.HEART,
        )
        assert (
            MessageReaction.objects.filter(message=message_in_dm, user=user_b).count()
            == 2
        )

    def test_add_reaction_requires_participant(self, message_in_dm):
        outsider = UserFactory(is_verified=True)
        from apps.core.exceptions import PermissionDenied

        with pytest.raises(PermissionDenied):
            ChatService.add_reaction(
                message_id=message_in_dm.id,
                user=outsider,
                reaction=ReactionType.LIKE,
            )

    def test_add_reaction_on_deleted_message(self, dm_conversation, user, user_b):
        msg = Message.objects.create(
            conversation=dm_conversation,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            content="",
            content_type=MessageContentType.TEXT,
            sequence_number=2,
            status=MessageStatus.DELETED,
        )
        from apps.core.exceptions import NotFound

        with pytest.raises(NotFound):
            ChatService.add_reaction(
                message_id=msg.id,
                user=user_b,
                reaction=ReactionType.LIKE,
            )


# =============================================================================
# REMOVE REACTION (SERVICE LEVEL)
# =============================================================================


@pytest.mark.django_db
class TestRemoveReaction:
    def test_remove_reaction(self, message_in_dm, user_b):
        ChatService.add_reaction(
            message_id=message_in_dm.id,
            user=user_b,
            reaction=ReactionType.LIKE,
        )
        ChatService.remove_reaction(
            message_id=message_in_dm.id,
            user=user_b,
            reaction=ReactionType.LIKE,
        )
        assert not MessageReaction.objects.filter(
            message=message_in_dm, user=user_b, reaction=ReactionType.LIKE
        ).exists()

    def test_remove_nonexistent_reaction(self, message_in_dm, user_b):
        from apps.core.exceptions import NotFound

        with pytest.raises(NotFound):
            ChatService.remove_reaction(
                message_id=message_in_dm.id,
                user=user_b,
                reaction=ReactionType.LIKE,
            )

    def test_remove_only_removes_specified_type(self, message_in_dm, user_b):
        ChatService.add_reaction(
            message_id=message_in_dm.id,
            user=user_b,
            reaction=ReactionType.LIKE,
        )
        ChatService.add_reaction(
            message_id=message_in_dm.id,
            user=user_b,
            reaction=ReactionType.HEART,
        )
        ChatService.remove_reaction(
            message_id=message_in_dm.id,
            user=user_b,
            reaction=ReactionType.LIKE,
        )
        remaining = MessageReaction.objects.filter(message=message_in_dm, user=user_b)
        assert remaining.count() == 1
        assert remaining.first().reaction == ReactionType.HEART


# =============================================================================
# REACTION VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestReactionView:
    def test_add_reaction_via_api(
        self, authenticated_client, dm_conversation, message_in_dm
    ):
        url = f"/api/v1/chat/conversations/{dm_conversation.id}/messages/{message_in_dm.id}/reactions/"
        resp = authenticated_client.post(url, {"reaction": "like"}, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["reaction"] == "like"
        assert "id" in resp.data

    def test_remove_reaction_via_api(
        self, authenticated_client, dm_conversation, message_in_dm, user
    ):
        MessageReaction.objects.create(
            message=message_in_dm, user=user, reaction=ReactionType.LIKE
        )
        url = f"/api/v1/chat/conversations/{dm_conversation.id}/messages/{message_in_dm.id}/reactions/"
        resp = authenticated_client.delete(url, {"reaction": "like"}, format="json")
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_add_reaction_requires_authentication(
        self, api_client, dm_conversation, message_in_dm
    ):
        url = f"/api/v1/chat/conversations/{dm_conversation.id}/messages/{message_in_dm.id}/reactions/"
        resp = api_client.post(url, {"reaction": "like"}, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_add_reaction_invalid_type_via_api(
        self, authenticated_client, dm_conversation, message_in_dm
    ):
        url = f"/api/v1/chat/conversations/{dm_conversation.id}/messages/{message_in_dm.id}/reactions/"
        resp = authenticated_client.post(url, {"reaction": "invalid"}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# REACTION COUNTS & OUTPUT
# =============================================================================


@pytest.mark.django_db
class TestReactionCountsOutput:
    def test_message_output_includes_reaction_counts(
        self, authenticated_client, dm_conversation, message_in_dm, user, user_b
    ):
        MessageReaction.objects.create(
            message=message_in_dm, user=user, reaction=ReactionType.LIKE
        )
        MessageReaction.objects.create(
            message=message_in_dm, user=user_b, reaction=ReactionType.LIKE
        )
        MessageReaction.objects.create(
            message=message_in_dm, user=user_b, reaction=ReactionType.HEART
        )

        url = f"/api/v1/chat/conversations/{dm_conversation.id}/messages/"
        resp = authenticated_client.get(url)

        assert resp.status_code == status.HTTP_200_OK
        msg_data = resp.data[0]
        assert msg_data["reactions"]["like"] == 2
        assert msg_data["reactions"]["heart"] == 1

    def test_message_output_includes_my_reactions(
        self, authenticated_client, dm_conversation, message_in_dm, user
    ):
        MessageReaction.objects.create(
            message=message_in_dm, user=user, reaction=ReactionType.LIKE
        )

        url = f"/api/v1/chat/conversations/{dm_conversation.id}/messages/"
        resp = authenticated_client.get(url)

        assert resp.status_code == status.HTTP_200_OK
        msg_data = resp.data[0]
        assert "like" in msg_data["my_reactions"]

    def test_reaction_counts_aggregate_correctly(
        self, dm_conversation, message_in_dm, user, user_b, user_c
    ):
        MessageReaction.objects.create(
            message=message_in_dm, user=user, reaction=ReactionType.LIKE
        )
        MessageReaction.objects.create(
            message=message_in_dm, user=user_b, reaction=ReactionType.LIKE
        )
        MessageReaction.objects.create(
            message=message_in_dm, user=user_c, reaction=ReactionType.LIKE
        )

        from apps.chat.selectors import ChatSelector

        result = ChatSelector.get_reactions_for_messages(message_ids=[message_in_dm.id])
        assert result[message_in_dm.id]["counts"]["like"] == 3

    def test_empty_reactions(
        self, authenticated_client, dm_conversation, message_in_dm
    ):
        url = f"/api/v1/chat/conversations/{dm_conversation.id}/messages/"
        resp = authenticated_client.get(url)

        assert resp.status_code == status.HTTP_200_OK
        msg_data = resp.data[0]
        assert msg_data["reactions"] == {}
        assert msg_data["my_reactions"] == []


# =============================================================================
# BROADCAST
# =============================================================================


@pytest.mark.django_db
class TestReactionBroadcast:
    def test_add_reaction_broadcasts(
        self, dm_conversation, message_in_dm, user_b, immediate_on_commit
    ):
        with patch("apps.chat.broadcast.broadcast_reaction_update") as mock_bc:
            ChatService.add_reaction(
                message_id=message_in_dm.id,
                user=user_b,
                reaction=ReactionType.LIKE,
            )
        mock_bc.assert_called_once()
        args = mock_bc.call_args[0]
        assert args[4] == "add"

    def test_remove_reaction_broadcasts(
        self, dm_conversation, message_in_dm, user_b, immediate_on_commit
    ):
        MessageReaction.objects.create(
            message=message_in_dm, user=user_b, reaction=ReactionType.LIKE
        )
        with patch("apps.chat.broadcast.broadcast_reaction_update") as mock_bc:
            ChatService.remove_reaction(
                message_id=message_in_dm.id,
                user=user_b,
                reaction=ReactionType.LIKE,
            )
        mock_bc.assert_called_once()
        args = mock_bc.call_args[0]
        assert args[4] == "remove"

    def test_broadcast_failure_doesnt_fail_service(
        self, dm_conversation, message_in_dm, user_b, immediate_on_commit
    ):
        with patch(
            "apps.chat.broadcast.broadcast_reaction_update",
            side_effect=Exception("boom"),
        ):
            reaction = ChatService.add_reaction(
                message_id=message_in_dm.id,
                user=user_b,
                reaction=ReactionType.LIKE,
            )
        assert reaction is not None

    def test_ws_serialize_reaction_update(self):
        from apps.chat.ws_serializers import serialize_reaction_update

        payload = serialize_reaction_update(
            uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), "like", "add"
        )
        assert payload["reaction"] == "like"
        assert payload["action"] == "add"
        assert "conversation_id" in payload
        assert "message_id" in payload
        assert "user_id" in payload


# =============================================================================
# NOTIFICATION
# =============================================================================


@pytest.mark.django_db
class TestReactionNotification:
    def test_reaction_notifies_message_author(
        self, dm_conversation, message_in_dm, user, user_b, immediate_on_commit
    ):
        with patch.object(ChatService, "_notify_safe") as mock_notify:
            ChatService.add_reaction(
                message_id=message_in_dm.id,
                user=user_b,
                reaction=ReactionType.LIKE,
            )
        # _notify_safe called for reaction_received
        notify_calls = [
            c for c in mock_notify.call_args_list if c[0][0] == "reaction_received"
        ]
        assert len(notify_calls) == 1

    def test_reaction_skips_self_notification(
        self, dm_conversation, message_in_dm, user, immediate_on_commit
    ):
        # user reacts on own message — should NOT get notification
        with patch.object(ChatService, "_notify_safe") as mock_notify:
            ChatService.add_reaction(
                message_id=message_in_dm.id,
                user=user,
                reaction=ReactionType.LIKE,
            )
        notify_calls = [
            c for c in mock_notify.call_args_list if c[0][0] == "reaction_received"
        ]
        assert len(notify_calls) == 0

    def test_reaction_notification_handler(
        self, dm_conversation, message_in_dm, user, user_b
    ):
        mock_ns = MagicMock()
        ChatService._notify_reaction_received(
            mock_ns,
            message=message_in_dm,
            conversation=dm_conversation,
            reactor_user=user_b,
        )
        mock_ns.send.assert_called_once()
        ctx = mock_ns.send.call_args.kwargs["context"]
        assert "conversation_id" in ctx
        assert "reactor_name" in ctx
        assert "message_preview" in ctx
        assert (
            mock_ns.send.call_args.kwargs["notification_type"]
            == "chat_reaction_received"
        )

    def test_reaction_notification_type_exists(self):
        from apps.notifications.types import NOTIFICATION_TYPES

        assert "chat_reaction_received" in NOTIFICATION_TYPES
