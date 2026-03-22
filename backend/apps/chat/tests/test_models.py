"""
Chat Model Tests
================
Tests for Conversation, ConversationParticipant, Message, ChatBlock models.
"""

import uuid

import pytest
from django.db import IntegrityError

from apps.chat.constants import (
    ConversationType,
    MessageContentType,
    MessageStatus,
    ParticipantRole,
    ParticipantType,
    RequestStatus,
    ScopeType,
)
from apps.chat.models import ChatBlock, Conversation, ConversationParticipant, Message
from apps.chat.tests.factories import (
    ChatBlockFactory,
    ConversationFactory,
    ConversationParticipantFactory,
    MessageFactory,
)

pytestmark = pytest.mark.django_db


# =============================================================================
# CONVERSATION
# =============================================================================


class TestConversation:
    def test_create_global_dm(self):
        conv = ConversationFactory(
            scope_type=ScopeType.GLOBAL,
            conversation_type=ConversationType.DIRECT,
        )
        assert conv.scope_type == ScopeType.GLOBAL
        assert conv.scope_id is None
        assert conv.conversation_type == ConversationType.DIRECT
        assert conv.is_active is True

    def test_create_global_group(self):
        conv = ConversationFactory(
            scope_type=ScopeType.GLOBAL,
            conversation_type=ConversationType.GROUP,
            name="Test Group",
        )
        assert conv.conversation_type == ConversationType.GROUP
        assert conv.name == "Test Group"

    def test_create_business_scope(self):
        biz_id = uuid.uuid4()
        conv = ConversationFactory(
            scope_type=ScopeType.BUSINESS,
            scope_id=biz_id,
        )
        assert conv.scope_type == ScopeType.BUSINESS
        assert conv.scope_id == biz_id

    def test_default_ordering(self):
        """Conversations ordered by -last_message_at, -created_at."""
        c1 = ConversationFactory()
        c2 = ConversationFactory()
        # Both have null last_message_at, so order by -created_at
        convs = list(Conversation.objects.all())
        assert convs[0].id == c2.id
        assert convs[1].id == c1.id

    def test_str_representation(self):
        conv = ConversationFactory(
            scope_type=ScopeType.GLOBAL,
            conversation_type=ConversationType.DIRECT,
        )
        assert "direct" in str(conv)
        assert "global" in str(conv)

    def test_denormalized_last_message_fields(self):
        conv = ConversationFactory()
        assert conv.last_message_id is None
        assert conv.last_message_at is None
        assert conv.last_message_preview == ""

    def test_is_active_default(self):
        conv = ConversationFactory()
        assert conv.is_active is True


# =============================================================================
# CONVERSATION PARTICIPANT
# =============================================================================


class TestConversationParticipant:
    def test_create_participant(self, user):
        conv = ConversationFactory(created_by_id=user.id)
        cp = ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )
        assert cp.participant_type == ParticipantType.USER
        assert cp.participant_id == user.id
        assert cp.role == ParticipantRole.MEMBER
        assert cp.request_status == RequestStatus.NONE
        assert cp.is_active is True

    def test_unique_active_participant_constraint(self, user):
        conv = ConversationFactory(created_by_id=user.id)
        ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )
        with pytest.raises(IntegrityError):
            ConversationParticipantFactory(
                conversation=conv,
                participant_type=ParticipantType.USER,
                participant_id=user.id,
            )

    def test_inactive_participant_allows_new_active(self, user):
        conv = ConversationFactory(created_by_id=user.id)
        cp1 = ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )
        cp1.is_active = False
        cp1.save(update_fields=["is_active"])

        # Should NOT raise
        cp2 = ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        )
        assert cp2.is_active is True

    def test_watermark_fields_default_null(self, user):
        conv = ConversationFactory(created_by_id=user.id)
        cp = ConversationParticipantFactory(
            conversation=conv,
            participant_id=user.id,
        )
        assert cp.last_delivered_message_id is None
        assert cp.last_seen_message_id is None
        assert cp.last_seen_at is None

    def test_muted_default_false(self, user):
        conv = ConversationFactory(created_by_id=user.id)
        cp = ConversationParticipantFactory(
            conversation=conv,
            participant_id=user.id,
        )
        assert cp.is_muted is False


# =============================================================================
# MESSAGE
# =============================================================================


class TestMessage:
    def test_create_text_message(self):
        conv = ConversationFactory()
        msg = MessageFactory(
            conversation=conv,
            content="Hello!",
            sequence_number=1,
        )
        assert msg.content == "Hello!"
        assert msg.content_type == MessageContentType.TEXT
        assert msg.status == MessageStatus.ACTIVE
        assert msg.sequence_number == 1

    def test_unique_sequence_per_conversation(self):
        conv = ConversationFactory()
        MessageFactory(conversation=conv, sequence_number=1)
        with pytest.raises(IntegrityError):
            MessageFactory(conversation=conv, sequence_number=1)

    def test_different_conversations_same_sequence(self):
        conv1 = ConversationFactory()
        conv2 = ConversationFactory()
        m1 = MessageFactory(conversation=conv1, sequence_number=1)
        m2 = MessageFactory(conversation=conv2, sequence_number=1)
        assert m1.sequence_number == m2.sequence_number

    def test_message_ordering(self):
        conv = ConversationFactory()
        m1 = MessageFactory(conversation=conv, sequence_number=1)
        m2 = MessageFactory(conversation=conv, sequence_number=2)
        m3 = MessageFactory(conversation=conv, sequence_number=3)
        msgs = list(Message.objects.filter(conversation=conv))
        assert msgs[0].id == m1.id
        assert msgs[1].id == m2.id
        assert msgs[2].id == m3.id

    def test_system_message(self):
        conv = ConversationFactory()
        msg = MessageFactory(
            conversation=conv,
            content_type=MessageContentType.SYSTEM,
            content="User joined the group",
            sequence_number=1,
        )
        assert msg.content_type == MessageContentType.SYSTEM

    def test_original_content_default_empty(self):
        msg = MessageFactory(sequence_number=1)
        assert msg.original_content == ""

    def test_metadata_default_dict(self):
        msg = MessageFactory(sequence_number=1)
        assert msg.metadata == {}

    def test_acting_user_id_nullable(self):
        msg = MessageFactory(sequence_number=1, acting_user_id=None)
        assert msg.acting_user_id is None


# =============================================================================
# CHAT BLOCK
# =============================================================================


class TestChatBlock:
    def test_create_block(self, user):
        blocked_id = uuid.uuid4()
        block = ChatBlockFactory(
            blocker=user,
            blocked_type=ParticipantType.USER,
            blocked_id=blocked_id,
        )
        assert block.blocker == user
        assert block.blocked_type == ParticipantType.USER
        assert block.blocked_id == blocked_id

    def test_unique_block_constraint(self, user):
        blocked_id = uuid.uuid4()
        ChatBlockFactory(
            blocker=user,
            blocked_type=ParticipantType.USER,
            blocked_id=blocked_id,
        )
        with pytest.raises(IntegrityError):
            ChatBlockFactory(
                blocker=user,
                blocked_type=ParticipantType.USER,
                blocked_id=blocked_id,
            )

    def test_block_business(self, user):
        biz_id = uuid.uuid4()
        block = ChatBlockFactory(
            blocker=user,
            blocked_type=ParticipantType.BUSINESS,
            blocked_id=biz_id,
        )
        assert block.blocked_type == ParticipantType.BUSINESS

    def test_str_representation(self, user):
        blocked_id = uuid.uuid4()
        block = ChatBlockFactory(
            blocker=user,
            blocked_id=blocked_id,
        )
        assert str(user.id) in str(block)
        assert str(blocked_id) in str(block)
