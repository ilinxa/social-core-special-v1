"""
Chat Selector Tests
====================
Tests for ChatSelector read-only query layer.
"""

import uuid

import pytest

from unittest.mock import patch

from apps.chat.constants import (
    ConversationType,
    MessageContentType,
    MessageStatus,
    ParticipantType,
    RequestStatus,
    ScopeType,
)
from apps.chat.models import Conversation, ConversationParticipant, Message
from apps.chat.selectors import ChatSelector
from apps.chat.tests.factories import (
    ChatBlockFactory,
    ConversationFactory,
    ConversationParticipantFactory,
    MessageFactory,
)
from apps.core.exceptions import NotFound

pytestmark = pytest.mark.django_db


# =============================================================================
# CONVERSATIONS
# =============================================================================


class TestGetConversationById:
    def test_returns_active_conversation(self):
        conv = ConversationFactory()
        result = ChatSelector.get_conversation_by_id(conversation_id=conv.id)
        assert result.id == conv.id

    def test_raises_not_found_for_inactive(self):
        conv = ConversationFactory(is_active=False)
        with pytest.raises(NotFound):
            ChatSelector.get_conversation_by_id(conversation_id=conv.id)

    def test_raises_not_found_for_nonexistent(self):
        with pytest.raises(NotFound):
            ChatSelector.get_conversation_by_id(conversation_id=uuid.uuid4())


class TestGetConversationsForParticipant:
    def test_returns_conversations_for_user(self, user):
        conv = ConversationFactory(scope_type=ScopeType.GLOBAL)
        ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )
        result = ChatSelector.get_conversations_for_participant(
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            scope_type=ScopeType.GLOBAL,
        )
        assert result.count() == 1
        assert result.first().id == conv.id

    def test_excludes_pending_requests_by_default(self, user):
        conv = ConversationFactory(scope_type=ScopeType.GLOBAL)
        ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            request_status=RequestStatus.PENDING,
        )
        result = ChatSelector.get_conversations_for_participant(
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            scope_type=ScopeType.GLOBAL,
        )
        assert result.count() == 0

    def test_includes_pending_requests_when_requested(self, user):
        conv = ConversationFactory(scope_type=ScopeType.GLOBAL)
        ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            request_status=RequestStatus.PENDING,
        )
        result = ChatSelector.get_conversations_for_participant(
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            scope_type=ScopeType.GLOBAL,
            exclude_requests=False,
        )
        assert result.count() == 1

    def test_excludes_inactive_participants(self, user):
        conv = ConversationFactory(scope_type=ScopeType.GLOBAL)
        ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            is_active=False,
        )
        result = ChatSelector.get_conversations_for_participant(
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            scope_type=ScopeType.GLOBAL,
        )
        assert result.count() == 0

    def test_filters_by_business_scope(self, user):
        biz_id = uuid.uuid4()
        conv1 = ConversationFactory(scope_type=ScopeType.BUSINESS, scope_id=biz_id)
        conv2 = ConversationFactory(scope_type=ScopeType.GLOBAL)
        ConversationParticipantFactory(
            conversation=conv1,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )
        ConversationParticipantFactory(
            conversation=conv2,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )
        result = ChatSelector.get_conversations_for_participant(
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            scope_type=ScopeType.BUSINESS,
            scope_id=biz_id,
        )
        assert result.count() == 1
        assert result.first().id == conv1.id


class TestGetDmConversation:
    def test_finds_existing_dm(self, user, user_b):
        conv = ConversationFactory(
            scope_type=ScopeType.GLOBAL,
            conversation_type=ConversationType.DIRECT,
        )
        ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )
        ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user_b.id,
        )
        result = ChatSelector.get_dm_conversation(
            scope_type=ScopeType.GLOBAL,
            scope_id=None,
            participant_a_type=ParticipantType.USER,
            participant_a_id=user.id,
            participant_b_type=ParticipantType.USER,
            participant_b_id=user_b.id,
        )
        assert result is not None
        assert result.id == conv.id

    def test_returns_none_when_no_dm(self, user, user_b):
        result = ChatSelector.get_dm_conversation(
            scope_type=ScopeType.GLOBAL,
            scope_id=None,
            participant_a_type=ParticipantType.USER,
            participant_a_id=user.id,
            participant_b_type=ParticipantType.USER,
            participant_b_id=user_b.id,
        )
        assert result is None

    def test_does_not_find_group_conversation(self, user, user_b):
        conv = ConversationFactory(
            scope_type=ScopeType.GLOBAL,
            conversation_type=ConversationType.GROUP,
            name="Group",
        )
        ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )
        ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user_b.id,
        )
        result = ChatSelector.get_dm_conversation(
            scope_type=ScopeType.GLOBAL,
            scope_id=None,
            participant_a_type=ParticipantType.USER,
            participant_a_id=user.id,
            participant_b_type=ParticipantType.USER,
            participant_b_id=user_b.id,
        )
        assert result is None

    def test_scope_isolation(self, user, user_b):
        """DM in global scope is not found when searching business scope."""
        conv = ConversationFactory(
            scope_type=ScopeType.GLOBAL,
            conversation_type=ConversationType.DIRECT,
        )
        ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )
        ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user_b.id,
        )
        result = ChatSelector.get_dm_conversation(
            scope_type=ScopeType.BUSINESS,
            scope_id=uuid.uuid4(),
            participant_a_type=ParticipantType.USER,
            participant_a_id=user.id,
            participant_b_type=ParticipantType.USER,
            participant_b_id=user_b.id,
        )
        assert result is None


# =============================================================================
# MESSAGES
# =============================================================================


class TestGetMessages:
    def test_latest_messages_without_cursor(self):
        conv = ConversationFactory()
        m1 = MessageFactory(conversation=conv, sequence_number=1)
        m2 = MessageFactory(conversation=conv, sequence_number=2)
        m3 = MessageFactory(conversation=conv, sequence_number=3)

        result = list(ChatSelector.get_messages(conversation_id=conv.id, page_size=10))
        # Default: latest first (descending)
        assert result[0].id == m3.id
        assert result[1].id == m2.id
        assert result[2].id == m1.id

    def test_cursor_older_direction(self):
        conv = ConversationFactory()
        m1 = MessageFactory(conversation=conv, sequence_number=1)
        m2 = MessageFactory(conversation=conv, sequence_number=2)
        m3 = MessageFactory(conversation=conv, sequence_number=3)

        result = list(
            ChatSelector.get_messages(
                conversation_id=conv.id,
                cursor=3,
                direction="older",
                page_size=10,
            )
        )
        assert len(result) == 2
        assert result[0].id == m2.id
        assert result[1].id == m1.id

    def test_cursor_newer_direction(self):
        conv = ConversationFactory()
        m1 = MessageFactory(conversation=conv, sequence_number=1)
        m2 = MessageFactory(conversation=conv, sequence_number=2)
        m3 = MessageFactory(conversation=conv, sequence_number=3)

        result = list(
            ChatSelector.get_messages(
                conversation_id=conv.id,
                cursor=1,
                direction="newer",
                page_size=10,
            )
        )
        assert len(result) == 2
        assert result[0].id == m2.id
        assert result[1].id == m3.id

    def test_page_size_limit(self):
        conv = ConversationFactory()
        for i in range(5):
            MessageFactory(conversation=conv, sequence_number=i + 1)

        result = list(ChatSelector.get_messages(conversation_id=conv.id, page_size=3))
        assert len(result) == 3


class TestGetMessageById:
    def test_returns_message(self):
        msg = MessageFactory(sequence_number=1)
        result = ChatSelector.get_message_by_id(message_id=msg.id)
        assert result.id == msg.id

    def test_raises_not_found(self):
        with pytest.raises(NotFound):
            ChatSelector.get_message_by_id(message_id=uuid.uuid4())


# =============================================================================
# PARTICIPANTS
# =============================================================================


class TestGetParticipants:
    def test_returns_active_participants(self, user, user_b):
        conv = ConversationFactory()
        cp1 = ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )
        cp2 = ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user_b.id,
        )
        result = ChatSelector.get_participants(conversation_id=conv.id)
        assert result.count() == 2

    def test_excludes_inactive(self, user):
        conv = ConversationFactory()
        ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            is_active=False,
        )
        result = ChatSelector.get_participants(conversation_id=conv.id)
        assert result.count() == 0


class TestGetParticipant:
    def test_returns_active_participant(self, user):
        conv = ConversationFactory()
        cp = ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )
        result = ChatSelector.get_participant(
            conversation_id=conv.id,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )
        assert result is not None
        assert result.id == cp.id

    def test_returns_none_for_inactive(self, user):
        conv = ConversationFactory()
        ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            is_active=False,
        )
        result = ChatSelector.get_participant(
            conversation_id=conv.id,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )
        assert result is None


class TestIsParticipant:
    def test_true_for_active_participant(self, user):
        conv = ConversationFactory()
        ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )
        assert ChatSelector.is_participant(
            conversation_id=conv.id,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )

    def test_false_for_nonparticipant(self, user):
        conv = ConversationFactory()
        assert not ChatSelector.is_participant(
            conversation_id=conv.id,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )


# =============================================================================
# CHAT REQUESTS
# =============================================================================


class TestGetPendingRequests:
    def test_returns_pending_requests(self, user):
        conv = ConversationFactory()
        cp = ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            request_status=RequestStatus.PENDING,
        )
        result = ChatSelector.get_pending_requests(
            recipient_type=ParticipantType.USER,
            recipient_id=user.id,
        )
        assert result.count() == 1
        assert result.first().id == cp.id

    def test_excludes_accepted_requests(self, user):
        conv = ConversationFactory()
        ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            request_status=RequestStatus.ACCEPTED,
        )
        result = ChatSelector.get_pending_requests(
            recipient_type=ParticipantType.USER,
            recipient_id=user.id,
        )
        assert result.count() == 0

    def test_excludes_inactive_participants(self, user):
        conv = ConversationFactory()
        ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            request_status=RequestStatus.PENDING,
            is_active=False,
        )
        result = ChatSelector.get_pending_requests(
            recipient_type=ParticipantType.USER,
            recipient_id=user.id,
        )
        assert result.count() == 0


class TestCountPendingRequests:
    def test_counts_correctly(self, user):
        for _ in range(3):
            conv = ConversationFactory()
            ConversationParticipantFactory(
                conversation=conv,
                participant_type=ParticipantType.USER,
                participant_id=user.id,
                request_status=RequestStatus.PENDING,
            )
        result = ChatSelector.count_pending_requests(
            recipient_type=ParticipantType.USER,
            recipient_id=user.id,
        )
        assert result == 3


# =============================================================================
# BLOCKS
# =============================================================================


class TestIsBlocked:
    def test_returns_true_when_blocked(self, user):
        blocked_id = uuid.uuid4()
        ChatBlockFactory(
            blocker=user,
            blocked_type=ParticipantType.USER,
            blocked_id=blocked_id,
        )
        assert ChatSelector.is_blocked(
            blocker_id=user.id,
            blocked_type=ParticipantType.USER,
            blocked_id=blocked_id,
        )

    def test_returns_false_when_not_blocked(self, user):
        assert not ChatSelector.is_blocked(
            blocker_id=user.id,
            blocked_type=ParticipantType.USER,
            blocked_id=uuid.uuid4(),
        )


class TestGetBlocksForUser:
    def test_returns_user_blocks(self, user):
        b1 = ChatBlockFactory(blocker=user)
        b2 = ChatBlockFactory(blocker=user)
        result = ChatSelector.get_blocks_for_user(user_id=user.id)
        assert result.count() == 2


# =============================================================================
# UNREAD COUNTS
# =============================================================================


class TestGetUnreadCount:
    def test_counts_unread_messages(self, user, user_b):
        conv = ConversationFactory()
        cp = ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )
        # Messages from user_b that user hasn't seen
        MessageFactory(
            conversation=conv,
            sender_type=ParticipantType.USER,
            sender_id=user_b.id,
            sequence_number=1,
        )
        MessageFactory(
            conversation=conv,
            sender_type=ParticipantType.USER,
            sender_id=user_b.id,
            sequence_number=2,
        )
        result = ChatSelector.get_unread_count(
            conversation_id=conv.id,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )
        assert result == 2

    def test_excludes_own_messages(self, user):
        conv = ConversationFactory()
        ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )
        MessageFactory(
            conversation=conv,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            sequence_number=1,
        )
        result = ChatSelector.get_unread_count(
            conversation_id=conv.id,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )
        assert result == 0

    def test_counts_after_watermark(self, user, user_b):
        conv = ConversationFactory()
        m1 = MessageFactory(
            conversation=conv,
            sender_type=ParticipantType.USER,
            sender_id=user_b.id,
            sequence_number=1,
        )
        m2 = MessageFactory(
            conversation=conv,
            sender_type=ParticipantType.USER,
            sender_id=user_b.id,
            sequence_number=2,
        )
        m3 = MessageFactory(
            conversation=conv,
            sender_type=ParticipantType.USER,
            sender_id=user_b.id,
            sequence_number=3,
        )
        # User has seen up to m1
        ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            last_seen_message_id=m1.id,
        )
        result = ChatSelector.get_unread_count(
            conversation_id=conv.id,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )
        assert result == 2

    def test_returns_zero_for_nonparticipant(self, user):
        conv = ConversationFactory()
        result = ChatSelector.get_unread_count(
            conversation_id=conv.id,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )
        assert result == 0

    def test_excludes_deleted_messages(self, user, user_b):
        conv = ConversationFactory()
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
            status=MessageStatus.DELETED,
        )
        result = ChatSelector.get_unread_count(
            conversation_id=conv.id,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )
        assert result == 0


class TestGetUnreadCountsByScope:
    def test_aggregates_by_scope(self, user, user_b):
        # Global conversation
        conv_global = ConversationFactory(scope_type=ScopeType.GLOBAL)
        ConversationParticipantFactory(
            conversation=conv_global,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )
        MessageFactory(
            conversation=conv_global,
            sender_type=ParticipantType.USER,
            sender_id=user_b.id,
            sequence_number=1,
        )

        # Business conversation
        biz_id = uuid.uuid4()
        conv_biz = ConversationFactory(scope_type=ScopeType.BUSINESS, scope_id=biz_id)
        ConversationParticipantFactory(
            conversation=conv_biz,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )
        MessageFactory(
            conversation=conv_biz,
            sender_type=ParticipantType.USER,
            sender_id=user_b.id,
            sequence_number=1,
        )

        result = ChatSelector.get_unread_counts_by_scope(user_id=user.id)
        assert result["global"] == 1
        assert result["business"][str(biz_id)] == 1
        assert result["platform"] == 0

    def test_result_includes_entity_key(self, user):
        """Unread counts result always has entity.business and entity.platform keys."""
        result = ChatSelector.get_unread_counts_by_scope(user_id=user.id)
        assert "entity" in result
        assert "business" in result["entity"]
        assert "platform" in result["entity"]

    @patch("apps.chat.policies.ChatPolicy.can_manage_entity_chat", return_value=True)
    def test_entity_unread_for_managed_business(self, mock_policy, user, user_b):
        """Entity unread counts include business entities the user can manage."""
        biz_id = uuid.uuid4()

        # Conversation where a business entity is a participant
        conv = ConversationFactory(scope_type=ScopeType.GLOBAL)
        ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.BUSINESS,
            participant_id=biz_id,
        )
        # Message from user_b creates unread for the entity
        MessageFactory(
            conversation=conv,
            sender_type=ParticipantType.USER,
            sender_id=user_b.id,
            sequence_number=1,
        )

        result = ChatSelector.get_unread_counts_by_scope(user_id=user.id)
        assert result["entity"]["business"][str(biz_id)] >= 1

    @patch("apps.chat.policies.ChatPolicy.can_manage_entity_chat", return_value=False)
    def test_entity_unread_excludes_non_managed(self, mock_policy, user, user_b):
        """Entity unread counts exclude entities the user cannot manage."""
        biz_id = uuid.uuid4()

        conv = ConversationFactory(scope_type=ScopeType.GLOBAL)
        ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.BUSINESS,
            participant_id=biz_id,
        )
        MessageFactory(
            conversation=conv,
            sender_type=ParticipantType.USER,
            sender_id=user_b.id,
            sequence_number=1,
        )

        result = ChatSelector.get_unread_counts_by_scope(user_id=user.id)
        assert str(biz_id) not in result["entity"]["business"]

    @patch("apps.chat.policies.ChatPolicy.can_manage_entity_chat", return_value=True)
    def test_entity_unread_platform(self, mock_policy, user, user_b):
        """Entity unread counts for platform entity participants."""
        platform_id = uuid.uuid4()

        conv = ConversationFactory(scope_type=ScopeType.GLOBAL)
        ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.PLATFORM,
            participant_id=platform_id,
        )
        MessageFactory(
            conversation=conv,
            sender_type=ParticipantType.USER,
            sender_id=user_b.id,
            sequence_number=1,
        )

        result = ChatSelector.get_unread_counts_by_scope(user_id=user.id)
        assert result["entity"]["platform"][str(platform_id)] >= 1
