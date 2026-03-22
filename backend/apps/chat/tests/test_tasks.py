"""
Chat Task Tests
===============
Tests for Celery tasks in the chat system.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.chat.constants import (
    ConversationType,
    ParticipantRole,
    ParticipantType,
    RequestStatus,
    ScopeType,
)
from apps.chat.models import Conversation, ConversationParticipant
from apps.chat.tasks import expire_stale_chat_requests
from apps.users.tests.factories import UserFactory


@pytest.fixture
def user(db):
    return UserFactory(is_verified=True)


@pytest.fixture
def user_b(db):
    return UserFactory(is_verified=True)


def _make_dm_with_request(user, user_b, request_status=RequestStatus.PENDING):
    """Create a DM with a specific request status on user_b."""
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
    p = ConversationParticipant.objects.create(
        conversation=conv,
        participant_type=ParticipantType.USER,
        participant_id=user_b.id,
        role=ParticipantRole.MEMBER,
        request_status=request_status,
    )
    return conv, p


@pytest.mark.django_db
class TestExpireStaleChatRequests:
    def test_expires_old_pending_requests(self, user, user_b):
        conv, participant = _make_dm_with_request(user, user_b)
        # Set created_at to 31 days ago
        cutoff = timezone.now() - timedelta(days=31)
        ConversationParticipant.objects.filter(id=participant.id).update(
            created_at=cutoff
        )

        count = expire_stale_chat_requests()

        participant.refresh_from_db()
        assert participant.request_status == RequestStatus.NONE
        assert count == 1

    def test_skips_recent_pending_requests(self, user, user_b):
        conv, participant = _make_dm_with_request(user, user_b)
        # Default created_at is now — should NOT be expired

        count = expire_stale_chat_requests()

        participant.refresh_from_db()
        assert participant.request_status == RequestStatus.PENDING
        assert count == 0

    def test_skips_accepted_requests(self, user, user_b):
        conv, participant = _make_dm_with_request(
            user, user_b, request_status=RequestStatus.ACCEPTED
        )
        cutoff = timezone.now() - timedelta(days=31)
        ConversationParticipant.objects.filter(id=participant.id).update(
            created_at=cutoff
        )

        count = expire_stale_chat_requests()

        participant.refresh_from_db()
        assert participant.request_status == RequestStatus.ACCEPTED
        assert count == 0

    def test_skips_ignored_requests(self, user, user_b):
        conv, participant = _make_dm_with_request(
            user, user_b, request_status=RequestStatus.IGNORED
        )
        cutoff = timezone.now() - timedelta(days=31)
        ConversationParticipant.objects.filter(id=participant.id).update(
            created_at=cutoff
        )

        count = expire_stale_chat_requests()

        participant.refresh_from_db()
        assert participant.request_status == RequestStatus.IGNORED
        assert count == 0

    def test_returns_zero_when_nothing_to_expire(self, db):
        count = expire_stale_chat_requests()
        assert count == 0
