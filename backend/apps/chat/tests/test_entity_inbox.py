"""
Entity Inbox Tests
==================
Tests for the entity inbox endpoint (Phase 4).
"""

import uuid
from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.chat.constants import (
    ConversationType,
    ParticipantRole,
    ParticipantType,
    RequestStatus,
    ScopeType,
)
from apps.chat.models import Conversation, ConversationParticipant
from apps.users.tests.factories import UserFactory


@pytest.fixture
def business_owner(db, business):
    """User who owns the business and has can_manage_chat."""
    return business.created_by


@pytest.fixture
def business_client(api_client, business_owner):
    api_client.force_authenticate(user=business_owner)
    return api_client


@pytest.fixture
def entity_dm(db, business, user_b):
    """DM conversation between business and user_b."""
    conv = Conversation.objects.create(
        scope_type=ScopeType.GLOBAL,
        scope_id=None,
        conversation_type=ConversationType.DIRECT,
        created_by_type=ParticipantType.BUSINESS,
        created_by_id=business.id,
    )
    ConversationParticipant.objects.create(
        conversation=conv,
        participant_type=ParticipantType.BUSINESS,
        participant_id=business.id,
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


@pytest.mark.django_db
class TestEntityInboxView:
    def _url(self, account_type, account_id):
        return f"/api/v1/chat/entity/{account_type}/{account_id}/inbox/"

    def test_entity_inbox_returns_conversations(
        self, business_client, business, entity_dm
    ):
        url = self._url("business", business.id)
        resp = business_client.get(url)

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] >= 1
        conv_ids = [r["id"] for r in resp.data["results"]]
        assert str(entity_dm.id) in conv_ids

    def test_entity_inbox_requires_authentication(self, api_client, business):
        url = self._url("business", business.id)
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_entity_inbox_requires_can_manage_chat(self, api_client, business):
        outsider = UserFactory(is_verified=True)
        api_client.force_authenticate(user=outsider)
        url = self._url("business", business.id)
        resp = api_client.get(url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_entity_inbox_invalid_account_type(self, business_client, business):
        url = self._url("invalid", business.id)
        resp = business_client.get(url)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_entity_inbox_empty_for_nonexistent_entity(self, business_client):
        url = self._url("business", uuid.uuid4())
        resp = business_client.get(url)
        # Permission denied because user can't manage chat for unknown business
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_entity_inbox_excludes_user_conversations(
        self, business_client, business, dm_conversation, entity_dm
    ):
        """Entity inbox only shows conversations where entity is a participant."""
        url = self._url("business", business.id)
        resp = business_client.get(url)

        assert resp.status_code == status.HTTP_200_OK
        conv_ids = [r["id"] for r in resp.data["results"]]
        # dm_conversation is user↔user, not entity
        assert str(dm_conversation.id) not in conv_ids
        # entity_dm is business↔user
        assert str(entity_dm.id) in conv_ids

    def test_entity_inbox_multiple_conversations(
        self, business_client, business, entity_dm
    ):
        """Multiple entity conversations appear in inbox."""
        user_c = UserFactory(is_verified=True)
        conv2 = Conversation.objects.create(
            scope_type=ScopeType.GLOBAL,
            scope_id=None,
            conversation_type=ConversationType.DIRECT,
            created_by_type=ParticipantType.BUSINESS,
            created_by_id=business.id,
        )
        ConversationParticipant.objects.create(
            conversation=conv2,
            participant_type=ParticipantType.BUSINESS,
            participant_id=business.id,
            role=ParticipantRole.MEMBER,
            request_status=RequestStatus.NONE,
        )
        ConversationParticipant.objects.create(
            conversation=conv2,
            participant_type=ParticipantType.USER,
            participant_id=user_c.id,
            role=ParticipantRole.MEMBER,
            request_status=RequestStatus.NONE,
        )

        url = self._url("business", business.id)
        resp = business_client.get(url)

        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["count"] == 2
