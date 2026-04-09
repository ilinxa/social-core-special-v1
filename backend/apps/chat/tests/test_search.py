"""
Message Search Tests
====================
Tests for FTS message search (Phase 5).

Selector tests use SQLite fallback (icontains). PostgreSQL FTS tests
are marked with requires_postgres.
"""

import uuid
from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.chat.constants import (
    ConversationType,
    MessageContentType,
    MessageStatus,
    ParticipantRole,
    ParticipantType,
    RequestStatus,
    ScopeType,
)
from apps.chat.models import Conversation, ConversationParticipant, Message
from apps.chat.selectors import ChatSelector
from apps.users.tests.factories import UserFactory


def _create_message(conversation, user, content, seq):
    return Message.objects.create(
        conversation=conversation,
        sender_type=ParticipantType.USER,
        sender_id=user.id,
        content=content,
        content_type=MessageContentType.TEXT,
        sequence_number=seq,
    )


# =============================================================================
# SELECTOR-LEVEL SEARCH TESTS (SQLite fallback)
# =============================================================================


@pytest.mark.django_db
class TestSearchMessagesSelector:
    def test_search_returns_matching_messages(self, dm_conversation, user, user_b):
        _create_message(dm_conversation, user, "Hello world", 1)
        _create_message(dm_conversation, user_b, "Goodbye world", 2)
        _create_message(dm_conversation, user, "Nothing here", 3)

        results = list(
            ChatSelector.search_messages(
                query="world",
                participant_type=ParticipantType.USER,
                participant_id=user.id,
                scope_type=ScopeType.GLOBAL,
            )
        )

        assert len(results) == 2
        contents = {r.content for r in results}
        assert "Hello world" in contents
        assert "Goodbye world" in contents

    def test_search_empty_query_returns_empty(self, dm_conversation, user):
        _create_message(dm_conversation, user, "Something", 1)

        results = list(
            ChatSelector.search_messages(
                query="nonexistent",
                participant_type=ParticipantType.USER,
                participant_id=user.id,
                scope_type=ScopeType.GLOBAL,
            )
        )
        assert len(results) == 0

    def test_search_respects_scope(self, user, user_b):
        # Global scope conversation
        global_conv = Conversation.objects.create(
            scope_type=ScopeType.GLOBAL,
            conversation_type=ConversationType.DIRECT,
            created_by_type=ParticipantType.USER,
            created_by_id=user.id,
        )
        ConversationParticipant.objects.create(
            conversation=global_conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            role=ParticipantRole.MEMBER,
            request_status=RequestStatus.NONE,
        )
        _create_message(global_conv, user, "Global payment info", 1)

        # Business scope conversation
        biz_id = uuid.uuid4()
        biz_conv = Conversation.objects.create(
            scope_type=ScopeType.BUSINESS,
            scope_id=biz_id,
            conversation_type=ConversationType.DIRECT,
            created_by_type=ParticipantType.USER,
            created_by_id=user.id,
        )
        ConversationParticipant.objects.create(
            conversation=biz_conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            role=ParticipantRole.MEMBER,
            request_status=RequestStatus.NONE,
        )
        _create_message(biz_conv, user, "Business payment info", 1)

        # Search in global scope only
        results = list(
            ChatSelector.search_messages(
                query="payment",
                participant_type=ParticipantType.USER,
                participant_id=user.id,
                scope_type=ScopeType.GLOBAL,
            )
        )
        assert len(results) == 1
        assert results[0].content == "Global payment info"

    def test_search_respects_conversation_filter(
        self, dm_conversation, group_conversation, user, user_b
    ):
        _create_message(dm_conversation, user, "Payment in DM", 1)
        _create_message(group_conversation, user, "Payment in group", 1)

        results = list(
            ChatSelector.search_messages(
                query="Payment",
                participant_type=ParticipantType.USER,
                participant_id=user.id,
                scope_type=ScopeType.GLOBAL,
                conversation_id=dm_conversation.id,
            )
        )
        assert len(results) == 1
        assert results[0].content == "Payment in DM"

    def test_search_excludes_deleted_messages(self, dm_conversation, user):
        msg = _create_message(dm_conversation, user, "Secret info", 1)
        msg.status = MessageStatus.DELETED
        msg.save(update_fields=["status"])

        results = list(
            ChatSelector.search_messages(
                query="Secret",
                participant_type=ParticipantType.USER,
                participant_id=user.id,
                scope_type=ScopeType.GLOBAL,
            )
        )
        assert len(results) == 0

    def test_search_includes_edited_messages(self, dm_conversation, user):
        msg = _create_message(dm_conversation, user, "Edited content", 1)
        msg.status = MessageStatus.EDITED
        msg.save(update_fields=["status"])

        results = list(
            ChatSelector.search_messages(
                query="Edited",
                participant_type=ParticipantType.USER,
                participant_id=user.id,
                scope_type=ScopeType.GLOBAL,
            )
        )
        assert len(results) == 1

    def test_search_only_in_participated_conversations(self, user, user_b):
        """User cannot search messages in conversations they don't participate in."""
        # Create conversation user_b participates in but user does NOT
        conv = Conversation.objects.create(
            scope_type=ScopeType.GLOBAL,
            conversation_type=ConversationType.DIRECT,
            created_by_type=ParticipantType.USER,
            created_by_id=user_b.id,
        )
        other = UserFactory(is_verified=True)
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
            participant_id=other.id,
            role=ParticipantRole.MEMBER,
            request_status=RequestStatus.NONE,
        )
        _create_message(conv, user_b, "Private conversation", 1)

        # user searches — should NOT see messages from that conversation
        results = list(
            ChatSelector.search_messages(
                query="Private",
                participant_type=ParticipantType.USER,
                participant_id=user.id,
                scope_type=ScopeType.GLOBAL,
            )
        )
        assert len(results) == 0

    def test_search_case_insensitive(self, dm_conversation, user):
        _create_message(dm_conversation, user, "Important Update", 1)

        results = list(
            ChatSelector.search_messages(
                query="important",
                participant_type=ParticipantType.USER,
                participant_id=user.id,
                scope_type=ScopeType.GLOBAL,
            )
        )
        assert len(results) == 1


# =============================================================================
# VIEW-LEVEL SEARCH TESTS
# =============================================================================


@pytest.mark.django_db
class TestMessageSearchView:
    URL = "/api/v1/chat/messages/search/"

    def test_search_returns_results(self, authenticated_client, dm_conversation, user):
        _create_message(dm_conversation, user, "Payment received", 1)

        resp = authenticated_client.get(self.URL, {"q": "Payment"})

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] >= 1
        assert resp.data["results"][0]["content"] == "Payment received"

    def test_search_empty_query_returns_empty(self, authenticated_client):
        resp = authenticated_client.get(self.URL, {"q": ""})
        assert resp.status_code == status.HTTP_200_OK
        # Empty query returns empty list directly
        assert resp.data == []

    def test_search_no_match_returns_empty(
        self, authenticated_client, dm_conversation, user
    ):
        _create_message(dm_conversation, user, "Hello", 1)

        resp = authenticated_client.get(self.URL, {"q": "xyz123"})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] == 0

    def test_search_requires_authentication(self, api_client):
        resp = api_client.get(self.URL, {"q": "test"})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_search_with_scope_filter(
        self, authenticated_client, dm_conversation, user
    ):
        _create_message(dm_conversation, user, "Scoped message", 1)

        resp = authenticated_client.get(
            self.URL, {"q": "Scoped", "scope_type": "global"}
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] >= 1

    def test_search_with_conversation_filter(
        self, authenticated_client, dm_conversation, group_conversation, user
    ):
        _create_message(dm_conversation, user, "DM search target", 1)
        _create_message(group_conversation, user, "Group search target", 1)

        resp = authenticated_client.get(
            self.URL,
            {"q": "search target", "conversation_id": str(dm_conversation.id)},
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] == 1
        assert "DM" in resp.data["results"][0]["content"]

    def test_search_result_shape(self, authenticated_client, dm_conversation, user):
        _create_message(dm_conversation, user, "Shape test message", 1)

        resp = authenticated_client.get(self.URL, {"q": "Shape"})

        assert resp.status_code == status.HTTP_200_OK
        result = resp.data["results"][0]
        assert "id" in result
        assert "conversation_id" in result
        assert "sender_type" in result
        assert "sender_id" in result
        assert "sender_name" in result
        assert "content" in result
        assert "status" in result
        assert "sequence_number" in result
        assert "created_at" in result
        assert "conversation_name" in result
