"""
Chat View Tests
================
Tests for REST API views. Mock ChatService/ChatSelector/ChatPolicy
to isolate view logic from service logic.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework import status

from apps.chat.constants import (
    ConversationType,
    MessageContentType,
    MessageStatus,
    ParticipantRole,
    ParticipantType,
    RequestStatus,
    ScopeType,
)
from apps.chat.models import ConversationParticipant, Message
from apps.chat.tests.factories import (
    ChatBlockFactory,
    ConversationFactory,
    ConversationParticipantFactory,
    MessageFactory,
)

pytestmark = pytest.mark.django_db


# =============================================================================
# CONVERSATION LIST/CREATE VIEW
# =============================================================================


class TestConversationListCreateView:
    def test_list_requires_auth(self, api_client):
        url = reverse("chat:conversation-list-create")
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_returns_conversations(self, authenticated_client, user):
        conv = ConversationFactory(scope_type=ScopeType.GLOBAL)
        ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )
        url = reverse("chat:conversation-list-create")
        resp = authenticated_client.get(url, {"scope_type": "global"})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] >= 1

    def test_create_conversation(self, authenticated_client, user, user_b):
        url = reverse("chat:conversation-list-create")
        data = {
            "scope_type": "global",
            "conversation_type": "direct",
            "participant_ids": [
                {
                    "participant_type": "user",
                    "participant_id": str(user_b.id),
                }
            ],
        }
        resp = authenticated_client.post(url, data, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["conversation_type"] == "direct"

    def test_create_group(self, authenticated_client, user, user_b, user_c):
        url = reverse("chat:conversation-list-create")
        data = {
            "scope_type": "global",
            "conversation_type": "group",
            "name": "My Group",
            "participant_ids": [
                {
                    "participant_type": "user",
                    "participant_id": str(user_b.id),
                },
                {
                    "participant_type": "user",
                    "participant_id": str(user_c.id),
                },
            ],
        }
        resp = authenticated_client.post(url, data, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["name"] == "My Group"


# =============================================================================
# CONVERSATION DETAIL VIEW
# =============================================================================


class TestConversationDetailView:
    def test_get_conversation_detail(self, authenticated_client, dm_conversation, user):
        url = reverse(
            "chat:conversation-detail",
            kwargs={"conversation_id": dm_conversation.id},
        )
        resp = authenticated_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["id"] == str(dm_conversation.id)
        assert "participants" in resp.data

    def test_patch_group(self, authenticated_client, user, group_conversation):
        url = reverse(
            "chat:conversation-detail",
            kwargs={"conversation_id": group_conversation.id},
        )
        resp = authenticated_client.patch(
            url, {"name": "Updated"}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["name"] == "Updated"

    def test_patch_dm_fails(self, authenticated_client, dm_conversation):
        url = reverse(
            "chat:conversation-detail",
            kwargs={"conversation_id": dm_conversation.id},
        )
        resp = authenticated_client.patch(
            url, {"name": "Nope"}, format="json"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# PARTICIPANT VIEWS
# =============================================================================


class TestParticipantListAddView:
    def test_list_participants(self, authenticated_client, dm_conversation):
        url = reverse(
            "chat:participant-list-add",
            kwargs={"conversation_id": dm_conversation.id},
        )
        resp = authenticated_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 2  # user + user_b

    def test_add_participant_to_group(
        self, authenticated_client, user, group_conversation
    ):
        new_user_id = uuid.uuid4()
        url = reverse(
            "chat:participant-list-add",
            kwargs={"conversation_id": group_conversation.id},
        )
        resp = authenticated_client.post(
            url,
            {
                "participant_type": "user",
                "participant_id": str(new_user_id),
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED


class TestLeaveConversationView:
    def test_leave_group(self, authenticated_client, user_b, group_conversation):
        # Authenticate as user_b to leave
        api_client = authenticated_client
        api_client.force_authenticate(user=user_b)
        url = reverse(
            "chat:conversation-leave",
            kwargs={"conversation_id": group_conversation.id},
        )
        resp = api_client.post(url)
        assert resp.status_code == status.HTTP_204_NO_CONTENT


# =============================================================================
# MESSAGE VIEWS
# =============================================================================


class TestMessageListCreateView:
    def test_get_messages(self, authenticated_client, dm_conversation, user):
        MessageFactory(
            conversation=dm_conversation,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            sequence_number=1,
        )
        url = reverse(
            "chat:message-list-create",
            kwargs={"conversation_id": dm_conversation.id},
        )
        resp = authenticated_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1

    def test_send_message(self, authenticated_client, dm_conversation, user):
        url = reverse(
            "chat:message-list-create",
            kwargs={"conversation_id": dm_conversation.id},
        )
        resp = authenticated_client.post(
            url, {"content": "Hello!"}, format="json"
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["content"] == "Hello!"
        assert resp.data["sequence_number"] == 1


class TestMessageEditDeleteView:
    def test_edit_message(self, authenticated_client, dm_conversation, user):
        msg = MessageFactory(
            conversation=dm_conversation,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            sequence_number=1,
            content="Original",
        )
        url = reverse(
            "chat:message-edit-delete",
            kwargs={
                "conversation_id": dm_conversation.id,
                "message_id": msg.id,
            },
        )
        resp = authenticated_client.patch(
            url, {"content": "Edited"}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["content"] == "Edited"

    def test_delete_message(self, authenticated_client, dm_conversation, user):
        msg = MessageFactory(
            conversation=dm_conversation,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            sequence_number=1,
        )
        url = reverse(
            "chat:message-edit-delete",
            kwargs={
                "conversation_id": dm_conversation.id,
                "message_id": msg.id,
            },
        )
        resp = authenticated_client.delete(url)
        assert resp.status_code == status.HTTP_204_NO_CONTENT


# =============================================================================
# WATERMARK / MUTE VIEWS
# =============================================================================


class TestMarkSeenView:
    def test_mark_seen(self, authenticated_client, dm_conversation, user):
        msg = MessageFactory(
            conversation=dm_conversation, sequence_number=1
        )
        url = reverse(
            "chat:mark-seen",
            kwargs={"conversation_id": dm_conversation.id},
        )
        resp = authenticated_client.post(
            url,
            {"last_seen_message_id": str(msg.id)},
            format="json",
        )
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_mark_seen_missing_id_returns_400(
        self, authenticated_client, dm_conversation
    ):
        url = reverse(
            "chat:mark-seen",
            kwargs={"conversation_id": dm_conversation.id},
        )
        resp = authenticated_client.post(url, {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


class TestMuteConversationView:
    def test_mute(self, authenticated_client, dm_conversation, user):
        url = reverse(
            "chat:mute-conversation",
            kwargs={"conversation_id": dm_conversation.id},
        )
        resp = authenticated_client.post(url)
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        cp = ConversationParticipant.objects.get(
            conversation=dm_conversation,
            participant_id=user.id,
            is_active=True,
        )
        assert cp.is_muted is True


class TestUnmuteConversationView:
    def test_unmute(self, authenticated_client, dm_conversation, user):
        # First mute
        cp = ConversationParticipant.objects.get(
            conversation=dm_conversation,
            participant_id=user.id,
            is_active=True,
        )
        cp.is_muted = True
        cp.save(update_fields=["is_muted"])

        url = reverse(
            "chat:unmute-conversation",
            kwargs={"conversation_id": dm_conversation.id},
        )
        resp = authenticated_client.post(url)
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        cp.refresh_from_db()
        assert cp.is_muted is False


# =============================================================================
# CHAT REQUEST VIEWS
# =============================================================================


class TestChatRequestListView:
    def test_list_requests(self, api_client, user_b, dm_with_request):
        api_client.force_authenticate(user=user_b)
        url = reverse("chat:request-list")
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] >= 1


class TestAcceptChatRequestView:
    def test_accept_request(self, api_client, user_b, dm_with_request):
        api_client.force_authenticate(user=user_b)
        url = reverse(
            "chat:request-accept",
            kwargs={"conversation_id": dm_with_request.id},
        )
        resp = api_client.post(url)
        assert resp.status_code == status.HTTP_200_OK


class TestIgnoreChatRequestView:
    def test_ignore_request(self, api_client, user_b, dm_with_request):
        api_client.force_authenticate(user=user_b)
        url = reverse(
            "chat:request-ignore",
            kwargs={"conversation_id": dm_with_request.id},
        )
        resp = api_client.post(url)
        assert resp.status_code == status.HTTP_204_NO_CONTENT


# =============================================================================
# BLOCK VIEWS
# =============================================================================


class TestBlockListCreateView:
    def test_list_blocks(self, authenticated_client, user):
        ChatBlockFactory(blocker=user)
        url = reverse("chat:block-list-create")
        resp = authenticated_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] >= 1

    def test_create_block(self, authenticated_client, user):
        blocked_id = uuid.uuid4()
        url = reverse("chat:block-list-create")
        resp = authenticated_client.post(
            url,
            {
                "blocked_type": "user",
                "blocked_id": str(blocked_id),
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["blocked_id"] == str(blocked_id)


class TestUnblockView:
    def test_unblock(self, authenticated_client, user):
        block = ChatBlockFactory(blocker=user)
        url = reverse("chat:unblock", kwargs={"block_id": block.id})
        resp = authenticated_client.delete(url)
        assert resp.status_code == status.HTTP_204_NO_CONTENT


# =============================================================================
# UNREAD COUNTS VIEW
# =============================================================================


class TestUnreadCountsView:
    def test_get_unread_counts(self, authenticated_client, user, user_b):
        conv = ConversationFactory(scope_type=ScopeType.GLOBAL)
        ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )
        MessageFactory(
            conversation=conv,
            sender_type=ParticipantType.USER,
            sender_id=user_b.id,
            sequence_number=1,
        )
        url = reverse("chat:unread-counts")
        resp = authenticated_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        assert "global" in resp.data
        assert resp.data["global"] >= 1
