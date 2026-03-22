"""
Chat Audit Tests
================
Tests for AuditService integration in ChatService methods (Phase 4).
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from apps.chat.constants import (
    ConversationType,
    MessageContentType,
    MessageStatus,
    ParticipantRole,
    ParticipantType,
    RequestStatus,
    ScopeType,
)
from apps.chat.models import (
    ChatBlock,
    Conversation,
    ConversationParticipant,
    Message,
)
from apps.chat.services import ChatService
from apps.core.observability.audit.models import AuditLog
from apps.users.tests.factories import UserFactory


# =============================================================================
# CONVERSATION AUDIT
# =============================================================================


@pytest.mark.django_db
class TestConversationAudit:
    def test_create_conversation_logs_audit(self, user, user_b):
        with patch("apps.network.selectors.ConnectionSelector.is_connected", return_value=True):
            conversation = ChatService.create_conversation(
                scope_type=ScopeType.GLOBAL,
                conversation_type=ConversationType.DIRECT,
                participant_ids=[
                    {"participant_type": ParticipantType.USER, "participant_id": user_b.id}
                ],
                creator_type=ParticipantType.USER,
                creator_id=user.id,
                acting_user=user,
            )

        log = AuditLog.objects.filter(
            action=AuditLog.Action.CHAT_CONVERSATION_CREATED,
        ).first()
        assert log is not None
        assert log.actor_id == str(user.id)
        assert log.resource_type == "Conversation"
        assert log.resource_id == str(conversation.id)
        assert log.details["conversation_type"] == "direct"
        assert log.details["scope_type"] == "global"

    def test_create_group_conversation_logs_audit(self, user, user_b):
        conversation = ChatService.create_conversation(
            scope_type=ScopeType.GLOBAL,
            conversation_type=ConversationType.GROUP,
            participant_ids=[
                {"participant_type": ParticipantType.USER, "participant_id": user_b.id}
            ],
            name="Test Group",
            creator_type=ParticipantType.USER,
            creator_id=user.id,
            acting_user=user,
        )

        log = AuditLog.objects.filter(
            action=AuditLog.Action.CHAT_CONVERSATION_CREATED,
        ).first()
        assert log is not None
        assert log.details["conversation_type"] == "group"


# =============================================================================
# MESSAGE AUDIT
# =============================================================================


@pytest.mark.django_db
class TestMessageAudit:
    def test_entity_message_logs_audit(self, dm_conversation, user, business):
        """Entity messages are audited (regular user messages are not)."""
        # Add business as participant
        ConversationParticipant.objects.create(
            conversation=dm_conversation,
            participant_type=ParticipantType.BUSINESS,
            participant_id=business.id,
            role=ParticipantRole.MEMBER,
            request_status=RequestStatus.NONE,
        )

        with patch(
            "apps.chat.policies.ChatPolicy.can_manage_entity_chat",
            return_value=True,
        ):
            msg = ChatService.send_message(
                conversation_id=dm_conversation.id,
                sender_type=ParticipantType.BUSINESS,
                sender_id=business.id,
                acting_user_id=user.id,
                content="Hello from business",
            )

        log = AuditLog.objects.filter(
            action=AuditLog.Action.CHAT_MESSAGE_SENT,
        ).first()
        assert log is not None
        assert log.details["sender_type"] == "business"
        assert log.details["acting_user_id"] == str(user.id)

    def test_user_message_not_audited(self, dm_conversation, user):
        """Regular user-to-user messages are NOT audited (too high-volume)."""
        ChatService.send_message(
            conversation_id=dm_conversation.id,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            acting_user_id=user.id,
            content="Regular message",
        )

        log = AuditLog.objects.filter(
            action=AuditLog.Action.CHAT_MESSAGE_SENT,
        ).first()
        assert log is None

    def test_edit_message_logs_audit(self, dm_conversation, user):
        msg = Message.objects.create(
            conversation=dm_conversation,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            content="Original",
            content_type=MessageContentType.TEXT,
            sequence_number=1,
        )

        ChatService.edit_message(
            message_id=msg.id,
            new_content="Edited",
            user=user,
        )

        log = AuditLog.objects.filter(
            action=AuditLog.Action.CHAT_MESSAGE_EDITED,
        ).first()
        assert log is not None
        assert log.details["message_id"] == str(msg.id)

    def test_delete_message_logs_audit(self, dm_conversation, user):
        msg = Message.objects.create(
            conversation=dm_conversation,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            content="To delete",
            content_type=MessageContentType.TEXT,
            sequence_number=1,
        )

        ChatService.delete_message(message_id=msg.id, user=user)

        log = AuditLog.objects.filter(
            action=AuditLog.Action.CHAT_MESSAGE_DELETED,
        ).first()
        assert log is not None
        assert log.details["message_id"] == str(msg.id)


# =============================================================================
# REQUEST AUDIT
# =============================================================================


@pytest.mark.django_db
class TestRequestAudit:
    def test_accept_request_logs_audit(self, dm_with_request, user_b):
        ChatService.accept_request(
            conversation_id=dm_with_request.id,
            user=user_b,
        )

        log = AuditLog.objects.filter(
            action=AuditLog.Action.CHAT_REQUEST_ACCEPTED,
        ).first()
        assert log is not None
        assert log.actor_id == str(user_b.id)


# =============================================================================
# PARTICIPANT AUDIT
# =============================================================================


@pytest.mark.django_db
class TestParticipantAudit:
    def test_add_participant_logs_audit(self, group_conversation, user):
        new_user = UserFactory(is_verified=True)

        ChatService.add_participant(
            conversation_id=group_conversation.id,
            participant_type=ParticipantType.USER,
            participant_id=new_user.id,
            added_by=user,
        )

        log = AuditLog.objects.filter(
            action=AuditLog.Action.CHAT_PARTICIPANT_ADDED,
        ).first()
        assert log is not None
        assert log.details["participant_id"] == str(new_user.id)
        assert log.details["added_by"] == str(user.id)

    def test_remove_participant_logs_audit(self, group_conversation, user, user_b):
        ChatService.remove_participant(
            conversation_id=group_conversation.id,
            participant_type=ParticipantType.USER,
            participant_id=user_b.id,
            removed_by=user,
        )

        log = AuditLog.objects.filter(
            action=AuditLog.Action.CHAT_PARTICIPANT_REMOVED,
        ).first()
        assert log is not None
        assert log.details["participant_id"] == str(user_b.id)
        assert log.details["removed_by"] == str(user.id)


# =============================================================================
# BLOCK AUDIT
# =============================================================================


@pytest.mark.django_db
class TestBlockAudit:
    def test_block_logs_audit(self, user, user_b):
        ChatService.block_participant(
            blocker=user,
            blocked_type=ParticipantType.USER,
            blocked_id=user_b.id,
        )

        log = AuditLog.objects.filter(
            action=AuditLog.Action.CHAT_BLOCK_CREATED,
        ).first()
        assert log is not None
        assert log.details["blocker_id"] == str(user.id)
        assert log.details["blocked_id"] == str(user_b.id)

    def test_unblock_logs_audit(self, user, user_b):
        block = ChatBlock.objects.create(
            blocker=user,
            blocked_type=ParticipantType.USER,
            blocked_id=user_b.id,
        )

        ChatService.unblock_participant(
            blocker=user,
            block_id=block.id,
        )

        log = AuditLog.objects.filter(
            action=AuditLog.Action.CHAT_BLOCK_REMOVED,
        ).first()
        assert log is not None
        assert log.details["blocker_id"] == str(user.id)
