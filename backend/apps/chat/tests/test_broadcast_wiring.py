"""
Broadcast Wiring Tests
======================
Tests that REST views call broadcast functions after service calls.
All service and broadcast functions are mocked — these are integration
tests for the view→broadcast bridge, not the service or broadcast logic.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.chat.constants import (
    ConversationType,
    MessageStatus,
    ParticipantRole,
    ParticipantType,
    RequestStatus,
    ScopeType,
)
from apps.chat.models import Conversation, ConversationParticipant, Message
from apps.users.tests.factories import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


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
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


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
    return conv


@pytest.fixture
def message_in_dm(db, dm_conversation, user):
    return Message.objects.create(
        conversation=dm_conversation,
        sender_type=ParticipantType.USER,
        sender_id=user.id,
        content="Hello",
        content_type="text",
        sequence_number=1,
    )


# =============================================================================
# MESSAGE CREATE BROADCAST
# =============================================================================


@pytest.mark.django_db
class TestMessageCreateBroadcast:
    def test_message_create_calls_broadcast(
        self, authenticated_client, dm_conversation
    ):
        url = f"/api/v1/chat/conversations/{dm_conversation.id}/messages/"
        with patch("apps.chat.broadcast.broadcast_message_new") as mock_bc:
            resp = authenticated_client.post(url, {"content": "Hello!"}, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        mock_bc.assert_called_once()

    def test_message_create_broadcast_failure_doesnt_fail_request(
        self, authenticated_client, dm_conversation
    ):
        url = f"/api/v1/chat/conversations/{dm_conversation.id}/messages/"
        with patch(
            "apps.chat.broadcast.broadcast_message_new", side_effect=Exception("boom")
        ):
            resp = authenticated_client.post(url, {"content": "Hello!"}, format="json")
        assert resp.status_code == status.HTTP_201_CREATED

    def test_message_get_does_not_broadcast(
        self, authenticated_client, dm_conversation
    ):
        url = f"/api/v1/chat/conversations/{dm_conversation.id}/messages/"
        with patch("apps.chat.broadcast.broadcast_message_new") as mock_bc:
            resp = authenticated_client.get(url)
        assert resp.status_code == status.HTTP_200_OK
        mock_bc.assert_not_called()


# =============================================================================
# MESSAGE EDIT BROADCAST
# =============================================================================


@pytest.mark.django_db
class TestMessageEditBroadcast:
    def test_message_edit_calls_broadcast(
        self, authenticated_client, dm_conversation, message_in_dm
    ):
        url = f"/api/v1/chat/conversations/{dm_conversation.id}/messages/{message_in_dm.id}/"
        with patch("apps.chat.broadcast.broadcast_message_edited") as mock_bc:
            resp = authenticated_client.patch(
                url, {"content": "Edited!"}, format="json"
            )
        assert resp.status_code == status.HTTP_200_OK
        mock_bc.assert_called_once()

    def test_message_edit_broadcast_failure_doesnt_fail_request(
        self, authenticated_client, dm_conversation, message_in_dm
    ):
        url = f"/api/v1/chat/conversations/{dm_conversation.id}/messages/{message_in_dm.id}/"
        with patch(
            "apps.chat.broadcast.broadcast_message_edited",
            side_effect=Exception("boom"),
        ):
            resp = authenticated_client.patch(
                url, {"content": "Edited!"}, format="json"
            )
        assert resp.status_code == status.HTTP_200_OK


# =============================================================================
# MESSAGE DELETE BROADCAST
# =============================================================================


@pytest.mark.django_db
class TestMessageDeleteBroadcast:
    def test_message_delete_calls_broadcast(
        self, authenticated_client, dm_conversation, message_in_dm
    ):
        url = f"/api/v1/chat/conversations/{dm_conversation.id}/messages/{message_in_dm.id}/"
        with patch("apps.chat.broadcast.broadcast_message_deleted_by_ids") as mock_bc:
            resp = authenticated_client.delete(url)
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        mock_bc.assert_called_once_with(dm_conversation.id, message_in_dm.id)

    def test_message_delete_broadcast_failure_doesnt_fail_request(
        self, authenticated_client, dm_conversation, message_in_dm
    ):
        url = f"/api/v1/chat/conversations/{dm_conversation.id}/messages/{message_in_dm.id}/"
        with patch(
            "apps.chat.broadcast.broadcast_message_deleted_by_ids",
            side_effect=Exception("boom"),
        ):
            resp = authenticated_client.delete(url)
        assert resp.status_code == status.HTTP_204_NO_CONTENT


# =============================================================================
# CONVERSATION CREATE BROADCAST
# =============================================================================


@pytest.mark.django_db
class TestConversationCreateBroadcast:
    def test_conversation_create_calls_broadcast(self, authenticated_client, user_b):
        url = "/api/v1/chat/conversations/"
        payload = {
            "scope_type": "global",
            "conversation_type": "direct",
            "participant_ids": [
                {"participant_type": "user", "participant_id": str(user_b.id)}
            ],
        }
        with patch("apps.chat.broadcast.broadcast_new_conversation") as mock_bc:
            resp = authenticated_client.post(url, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        mock_bc.assert_called_once()

    def test_conversation_create_broadcast_failure_doesnt_fail_request(
        self, authenticated_client, user_b
    ):
        url = "/api/v1/chat/conversations/"
        payload = {
            "scope_type": "global",
            "conversation_type": "direct",
            "participant_ids": [
                {"participant_type": "user", "participant_id": str(user_b.id)}
            ],
        }
        with patch(
            "apps.chat.broadcast.broadcast_new_conversation",
            side_effect=Exception("boom"),
        ):
            resp = authenticated_client.post(url, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED


# =============================================================================
# MARK SEEN BROADCAST
# =============================================================================


@pytest.mark.django_db
class TestMarkSeenBroadcast:
    def test_mark_seen_calls_broadcast(
        self, authenticated_client, dm_conversation, message_in_dm
    ):
        url = f"/api/v1/chat/conversations/{dm_conversation.id}/seen/"
        with patch("apps.chat.broadcast.broadcast_seen_update") as mock_bc:
            resp = authenticated_client.post(
                url,
                {"last_seen_message_id": str(message_in_dm.id)},
                format="json",
            )
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        mock_bc.assert_called_once()

    def test_mark_seen_broadcast_failure_doesnt_fail_request(
        self, authenticated_client, dm_conversation, message_in_dm
    ):
        url = f"/api/v1/chat/conversations/{dm_conversation.id}/seen/"
        with patch(
            "apps.chat.broadcast.broadcast_seen_update", side_effect=Exception("boom")
        ):
            resp = authenticated_client.post(
                url,
                {"last_seen_message_id": str(message_in_dm.id)},
                format="json",
            )
        assert resp.status_code == status.HTTP_204_NO_CONTENT


# =============================================================================
# ADD PARTICIPANT BROADCAST
# =============================================================================


@pytest.mark.django_db
class TestAddParticipantBroadcast:
    def test_add_participant_calls_broadcast(
        self, authenticated_client, group_conversation, user_c
    ):
        url = f"/api/v1/chat/conversations/{group_conversation.id}/participants/"
        payload = {
            "participant_type": "user",
            "participant_id": str(user_c.id),
        }
        with patch("apps.chat.broadcast.broadcast_new_conversation") as mock_bc:
            resp = authenticated_client.post(url, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        mock_bc.assert_called_once()

    def test_add_participant_broadcast_failure_doesnt_fail_request(
        self, authenticated_client, group_conversation, user_c
    ):
        url = f"/api/v1/chat/conversations/{group_conversation.id}/participants/"
        payload = {
            "participant_type": "user",
            "participant_id": str(user_c.id),
        }
        with patch(
            "apps.chat.broadcast.broadcast_new_conversation",
            side_effect=Exception("boom"),
        ):
            resp = authenticated_client.post(url, payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
