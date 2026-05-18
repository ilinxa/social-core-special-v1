"""
Chat Service Tests
===================
Tests for ChatService write operations.
"""

import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.chat.constants import (
    CHAT_GROUP_MAX_PARTICIPANTS,
    CHAT_MESSAGE_EDIT_WINDOW_MINUTES,
    CHAT_MESSAGE_MAX_LENGTH,
    CHAT_REQUEST_MAX_MESSAGES,
    ConversationType,
    MessageContentType,
    MessageStatus,
    ParticipantRole,
    ParticipantType,
    RequestStatus,
    ScopeType,
)
from apps.chat.models import ChatBlock, Conversation, ConversationParticipant, Message
from apps.chat.services import ChatService
from apps.chat.tests.factories import (
    ChatBlockFactory,
    ConversationFactory,
    ConversationParticipantFactory,
    MessageFactory,
)
from apps.core.exceptions import (
    BusinessRuleViolation,
    ConflictError,
    NotFound,
    PermissionDenied,
    ValidationError,
)

pytestmark = pytest.mark.django_db


# =============================================================================
# CREATE CONVERSATION
# =============================================================================


class TestCreateConversation:
    def test_create_dm_between_users(self, user, user_b):
        conv = ChatService.create_conversation(
            scope_type=ScopeType.GLOBAL,
            conversation_type=ConversationType.DIRECT,
            participant_ids=[
                {
                    "participant_type": ParticipantType.USER,
                    "participant_id": user_b.id,
                }
            ],
            creator_type=ParticipantType.USER,
            creator_id=user.id,
            acting_user=user,
        )
        assert conv.conversation_type == ConversationType.DIRECT
        assert conv.scope_type == ScopeType.GLOBAL
        participants = ConversationParticipant.objects.filter(
            conversation=conv, is_active=True
        )
        assert participants.count() == 2

    def test_create_dm_returns_existing_dm(self, user, user_b):
        """Creating a DM that already exists returns the existing one."""
        conv1 = ChatService.create_conversation(
            scope_type=ScopeType.GLOBAL,
            conversation_type=ConversationType.DIRECT,
            participant_ids=[
                {
                    "participant_type": ParticipantType.USER,
                    "participant_id": user_b.id,
                }
            ],
            creator_type=ParticipantType.USER,
            creator_id=user.id,
            acting_user=user,
        )
        conv2 = ChatService.create_conversation(
            scope_type=ScopeType.GLOBAL,
            conversation_type=ConversationType.DIRECT,
            participant_ids=[
                {
                    "participant_type": ParticipantType.USER,
                    "participant_id": user_b.id,
                }
            ],
            creator_type=ParticipantType.USER,
            creator_id=user.id,
            acting_user=user,
        )
        assert conv1.id == conv2.id

    def test_create_dm_requires_exactly_one_participant(self, user, user_b, user_c):
        with pytest.raises(ValidationError):
            ChatService.create_conversation(
                scope_type=ScopeType.GLOBAL,
                conversation_type=ConversationType.DIRECT,
                participant_ids=[
                    {
                        "participant_type": ParticipantType.USER,
                        "participant_id": user_b.id,
                    },
                    {
                        "participant_type": ParticipantType.USER,
                        "participant_id": user_c.id,
                    },
                ],
                creator_type=ParticipantType.USER,
                creator_id=user.id,
                acting_user=user,
            )

    def test_create_dm_blocked_raises(self, user, user_b):
        """Cannot create DM if blocker has blocked recipient."""
        ChatBlockFactory(
            blocker=user,
            blocked_type=ParticipantType.USER,
            blocked_id=user_b.id,
        )
        with pytest.raises(BusinessRuleViolation):
            ChatService.create_conversation(
                scope_type=ScopeType.GLOBAL,
                conversation_type=ConversationType.DIRECT,
                participant_ids=[
                    {
                        "participant_type": ParticipantType.USER,
                        "participant_id": user_b.id,
                    }
                ],
                creator_type=ParticipantType.USER,
                creator_id=user.id,
                acting_user=user,
            )

    def test_create_dm_blocked_by_recipient_raises(self, user, user_b):
        """Cannot create DM if recipient has blocked the sender."""
        ChatBlockFactory(
            blocker=user_b,
            blocked_type=ParticipantType.USER,
            blocked_id=user.id,
        )
        with pytest.raises(PermissionDenied):
            ChatService.create_conversation(
                scope_type=ScopeType.GLOBAL,
                conversation_type=ConversationType.DIRECT,
                participant_ids=[
                    {
                        "participant_type": ParticipantType.USER,
                        "participant_id": user_b.id,
                    }
                ],
                creator_type=ParticipantType.USER,
                creator_id=user.id,
                acting_user=user,
            )

    @patch("apps.chat.services.ChatService._determine_request_status")
    def test_create_dm_global_sets_request_status(self, mock_determine, user, user_b):
        mock_determine.return_value = RequestStatus.PENDING
        conv = ChatService.create_conversation(
            scope_type=ScopeType.GLOBAL,
            conversation_type=ConversationType.DIRECT,
            participant_ids=[
                {
                    "participant_type": ParticipantType.USER,
                    "participant_id": user_b.id,
                }
            ],
            creator_type=ParticipantType.USER,
            creator_id=user.id,
            acting_user=user,
        )
        recipient = ConversationParticipant.objects.get(
            conversation=conv,
            participant_id=user_b.id,
        )
        assert recipient.request_status == RequestStatus.PENDING

    def test_create_group_conversation(self, user, user_b, user_c):
        conv = ChatService.create_conversation(
            scope_type=ScopeType.GLOBAL,
            conversation_type=ConversationType.GROUP,
            participant_ids=[
                {
                    "participant_type": ParticipantType.USER,
                    "participant_id": user_b.id,
                },
                {
                    "participant_type": ParticipantType.USER,
                    "participant_id": user_c.id,
                },
            ],
            name="Test Group",
            creator_type=ParticipantType.USER,
            creator_id=user.id,
            acting_user=user,
        )
        assert conv.conversation_type == ConversationType.GROUP
        assert conv.name == "Test Group"
        # Creator is admin
        creator_cp = ConversationParticipant.objects.get(
            conversation=conv, participant_id=user.id
        )
        assert creator_cp.role == ParticipantRole.ADMIN

    def test_create_group_requires_name(self, user, user_b):
        with pytest.raises(ValidationError):
            ChatService.create_conversation(
                scope_type=ScopeType.GLOBAL,
                conversation_type=ConversationType.GROUP,
                participant_ids=[
                    {
                        "participant_type": ParticipantType.USER,
                        "participant_id": user_b.id,
                    }
                ],
                name="",
                creator_type=ParticipantType.USER,
                creator_id=user.id,
                acting_user=user,
            )

    def test_create_group_whitespace_name_rejected(self, user, user_b):
        with pytest.raises(ValidationError):
            ChatService.create_conversation(
                scope_type=ScopeType.GLOBAL,
                conversation_type=ConversationType.GROUP,
                participant_ids=[
                    {
                        "participant_type": ParticipantType.USER,
                        "participant_id": user_b.id,
                    }
                ],
                name="   ",
                creator_type=ParticipantType.USER,
                creator_id=user.id,
                acting_user=user,
            )

    def test_create_business_scope(self, user, business):
        """User who is a business member can create conversation in business scope."""
        from apps.rbac.selectors import MembershipSelector

        # The business fixture creates RBAC membership for created_by user
        biz_owner = business.created_by
        conv = ChatService.create_conversation(
            scope_type=ScopeType.BUSINESS,
            scope_id=business.id,
            conversation_type=ConversationType.DIRECT,
            participant_ids=[
                {
                    "participant_type": ParticipantType.USER,
                    "participant_id": user.id,
                }
            ],
            creator_type=ParticipantType.USER,
            creator_id=biz_owner.id,
            acting_user=biz_owner,
        )
        assert conv.scope_type == ScopeType.BUSINESS
        assert conv.scope_id == business.id

    # -- can_manage_chat RBAC check for org-scoped group creation (Fix #2) --

    @patch("apps.chat.services.ChatPolicy.can_manage_entity_chat", return_value=False)
    def test_create_group_in_business_scope_requires_can_manage_chat(
        self, mock_can_manage, user, business
    ):
        """Group creation in business scope should fail without can_manage_chat."""
        biz_owner = business.created_by
        with pytest.raises(PermissionDenied):
            ChatService.create_conversation(
                scope_type=ScopeType.BUSINESS,
                scope_id=business.id,
                conversation_type=ConversationType.GROUP,
                participant_ids=[
                    {
                        "participant_type": ParticipantType.USER,
                        "participant_id": user.id,
                    }
                ],
                name="Biz Group",
                creator_type=ParticipantType.USER,
                creator_id=biz_owner.id,
                acting_user=biz_owner,
            )
        mock_can_manage.assert_called_once_with(
            user=biz_owner,
            account_type=ScopeType.BUSINESS,
            account_id=business.id,
        )

    @patch("apps.chat.services.ChatPolicy.can_manage_entity_chat", return_value=True)
    def test_create_group_in_business_scope_with_permission(
        self, mock_can_manage, user, business
    ):
        """Group creation in business scope should succeed with can_manage_chat."""
        biz_owner = business.created_by
        conv = ChatService.create_conversation(
            scope_type=ScopeType.BUSINESS,
            scope_id=business.id,
            conversation_type=ConversationType.GROUP,
            participant_ids=[
                {
                    "participant_type": ParticipantType.USER,
                    "participant_id": user.id,
                }
            ],
            name="Biz Group",
            creator_type=ParticipantType.USER,
            creator_id=biz_owner.id,
            acting_user=biz_owner,
        )
        assert conv.conversation_type == ConversationType.GROUP
        assert conv.scope_type == ScopeType.BUSINESS
        mock_can_manage.assert_called_once()

    @patch("apps.chat.services.ChatPolicy.can_manage_entity_chat", return_value=False)
    def test_create_dm_in_business_scope_skips_can_manage_chat(
        self, mock_can_manage, user, business
    ):
        """DM creation in business scope should NOT check can_manage_chat (DMs are not groups)."""
        biz_owner = business.created_by
        conv = ChatService.create_conversation(
            scope_type=ScopeType.BUSINESS,
            scope_id=business.id,
            conversation_type=ConversationType.DIRECT,
            participant_ids=[
                {
                    "participant_type": ParticipantType.USER,
                    "participant_id": user.id,
                }
            ],
            creator_type=ParticipantType.USER,
            creator_id=biz_owner.id,
            acting_user=biz_owner,
        )
        assert conv.conversation_type == ConversationType.DIRECT
        # can_manage_entity_chat should NOT have been called for DM creation


# =============================================================================
# UPDATE GROUP
# =============================================================================


class TestUpdateGroup:
    def test_update_group_name(self, user, group_conversation):
        result = ChatService.update_group(
            conversation_id=group_conversation.id,
            name="New Name",
            user=user,
        )
        assert result.name == "New Name"

    def test_update_group_description(self, user, group_conversation):
        result = ChatService.update_group(
            conversation_id=group_conversation.id,
            description="New desc",
            user=user,
        )
        assert result.description == "New desc"

    def test_update_dm_raises(self, user, dm_conversation):
        with pytest.raises(BusinessRuleViolation) as exc:
            ChatService.update_group(
                conversation_id=dm_conversation.id,
                name="Bad",
                user=user,
            )
        assert exc.value.details["rule"] == "dm_not_updateable"

    def test_non_admin_cannot_update(self, user_b, group_conversation):
        """user_b is member, not admin."""
        with pytest.raises(PermissionDenied):
            ChatService.update_group(
                conversation_id=group_conversation.id,
                name="Denied",
                user=user_b,
            )


# =============================================================================
# SEND MESSAGE
# =============================================================================


class TestSendMessage:
    def test_send_text_message(self, user, dm_conversation):
        msg = ChatService.send_message(
            conversation_id=dm_conversation.id,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            acting_user_id=user.id,
            content="Hello!",
        )
        assert msg.content == "Hello!"
        assert msg.sequence_number == 1
        assert msg.status == MessageStatus.ACTIVE
        # Check denormalized fields
        dm_conversation.refresh_from_db()
        assert dm_conversation.last_message_id == msg.id
        assert dm_conversation.last_message_preview == "Hello!"

    def test_sequential_sequence_numbers(self, user, dm_conversation):
        m1 = ChatService.send_message(
            conversation_id=dm_conversation.id,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            acting_user_id=user.id,
            content="First",
        )
        m2 = ChatService.send_message(
            conversation_id=dm_conversation.id,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            acting_user_id=user.id,
            content="Second",
        )
        assert m1.sequence_number == 1
        assert m2.sequence_number == 2

    def test_empty_content_raises(self, user, dm_conversation):
        with pytest.raises(ValidationError):
            ChatService.send_message(
                conversation_id=dm_conversation.id,
                sender_type=ParticipantType.USER,
                sender_id=user.id,
                acting_user_id=user.id,
                content="",
            )

    def test_whitespace_only_content_raises(self, user, dm_conversation):
        with pytest.raises(ValidationError):
            ChatService.send_message(
                conversation_id=dm_conversation.id,
                sender_type=ParticipantType.USER,
                sender_id=user.id,
                acting_user_id=user.id,
                content="   ",
            )

    def test_max_length_exceeded_raises(self, user, dm_conversation):
        with pytest.raises(ValidationError):
            ChatService.send_message(
                conversation_id=dm_conversation.id,
                sender_type=ParticipantType.USER,
                sender_id=user.id,
                acting_user_id=user.id,
                content="x" * (CHAT_MESSAGE_MAX_LENGTH + 1),
            )

    def test_nonparticipant_cannot_send(self, user_c, dm_conversation):
        """user_c is not in dm_conversation."""
        with pytest.raises(PermissionDenied):
            ChatService.send_message(
                conversation_id=dm_conversation.id,
                sender_type=ParticipantType.USER,
                sender_id=user_c.id,
                acting_user_id=user_c.id,
                content="Denied",
            )

    def test_dm_request_limit(self, user, dm_with_request):
        """Sender can only send CHAT_REQUEST_MAX_MESSAGES before acceptance."""
        for i in range(CHAT_REQUEST_MAX_MESSAGES):
            ChatService.send_message(
                conversation_id=dm_with_request.id,
                sender_type=ParticipantType.USER,
                sender_id=user.id,
                acting_user_id=user.id,
                content=f"Message {i + 1}",
            )
        with pytest.raises(BusinessRuleViolation) as exc:
            ChatService.send_message(
                conversation_id=dm_with_request.id,
                sender_type=ParticipantType.USER,
                sender_id=user.id,
                acting_user_id=user.id,
                content="One too many",
            )
        assert exc.value.details["rule"] == "request_message_limit"

    def test_entity_sender_acting_user_id_set(self, user, dm_conversation):
        """When sender_type is not user, acting_user_id is stored."""
        biz_id = uuid.uuid4()
        conv = ConversationFactory(scope_type=ScopeType.GLOBAL)
        ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.BUSINESS,
            participant_id=biz_id,
        )
        msg = ChatService.send_message(
            conversation_id=conv.id,
            sender_type=ParticipantType.BUSINESS,
            sender_id=biz_id,
            acting_user_id=user.id,
            content="Business says hi",
        )
        assert msg.acting_user_id == user.id

    def test_user_sender_acting_user_id_null(self, user, dm_conversation):
        """When sender_type is user, acting_user_id is None."""
        msg = ChatService.send_message(
            conversation_id=dm_conversation.id,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            acting_user_id=user.id,
            content="Hi",
        )
        assert msg.acting_user_id is None


# =============================================================================
# EDIT MESSAGE
# =============================================================================


class TestEditMessage:
    def test_edit_own_message(self, user, dm_conversation):
        msg = ChatService.send_message(
            conversation_id=dm_conversation.id,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            acting_user_id=user.id,
            content="Original",
        )
        edited = ChatService.edit_message(
            message_id=msg.id,
            new_content="Edited",
            user=user,
        )
        assert edited.content == "Edited"
        assert edited.original_content == "Original"
        assert edited.status == MessageStatus.EDITED
        assert edited.edited_at is not None

    def test_edit_preserves_first_original_content(self, user, dm_conversation):
        """Multiple edits keep the very first original content."""
        msg = ChatService.send_message(
            conversation_id=dm_conversation.id,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            acting_user_id=user.id,
            content="V1",
        )
        ChatService.edit_message(message_id=msg.id, new_content="V2", user=user)
        edited = ChatService.edit_message(
            message_id=msg.id, new_content="V3", user=user
        )
        assert edited.original_content == "V1"
        assert edited.content == "V3"

    def test_edit_updates_last_message_preview(self, user, dm_conversation):
        msg = ChatService.send_message(
            conversation_id=dm_conversation.id,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            acting_user_id=user.id,
            content="Original preview",
        )
        ChatService.edit_message(
            message_id=msg.id, new_content="New preview", user=user
        )
        dm_conversation.refresh_from_db()
        assert dm_conversation.last_message_preview == "New preview"

    def test_cannot_edit_other_users_message(self, user, user_b, dm_conversation):
        msg = ChatService.send_message(
            conversation_id=dm_conversation.id,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            acting_user_id=user.id,
            content="My message",
        )
        with pytest.raises(PermissionDenied):
            ChatService.edit_message(
                message_id=msg.id, new_content="Hacked", user=user_b
            )

    def test_cannot_edit_deleted_message(self, user, dm_conversation):
        msg = MessageFactory(
            conversation=dm_conversation,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            status=MessageStatus.DELETED,
            content="",
            sequence_number=1,
        )
        with pytest.raises(BusinessRuleViolation) as exc:
            ChatService.edit_message(message_id=msg.id, new_content="Back?", user=user)
        assert exc.value.details["rule"] == "message_deleted"

    def test_edit_window_expired(self, user, dm_conversation):
        msg = ChatService.send_message(
            conversation_id=dm_conversation.id,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            acting_user_id=user.id,
            content="Old message",
        )
        # Move created_at back beyond edit window
        Message.objects.filter(id=msg.id).update(
            created_at=timezone.now()
            - timedelta(minutes=CHAT_MESSAGE_EDIT_WINDOW_MINUTES + 1)
        )
        msg.refresh_from_db()
        with pytest.raises(BusinessRuleViolation) as exc:
            ChatService.edit_message(
                message_id=msg.id, new_content="Too late", user=user
            )
        assert exc.value.details["rule"] == "edit_window_expired"

    def test_edit_empty_content_raises(self, user, dm_conversation):
        msg = ChatService.send_message(
            conversation_id=dm_conversation.id,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            acting_user_id=user.id,
            content="Original",
        )
        with pytest.raises(ValidationError):
            ChatService.edit_message(message_id=msg.id, new_content="", user=user)


# =============================================================================
# DELETE MESSAGE
# =============================================================================


class TestDeleteMessage:
    def test_delete_own_message(self, user, dm_conversation):
        msg = ChatService.send_message(
            conversation_id=dm_conversation.id,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            acting_user_id=user.id,
            content="Delete me",
        )
        ChatService.delete_message(message_id=msg.id, user=user)
        msg.refresh_from_db()
        assert msg.status == MessageStatus.DELETED
        assert msg.content == ""
        assert msg.original_content == "Delete me"

    def test_delete_updates_last_message_preview(self, user, dm_conversation):
        msg = ChatService.send_message(
            conversation_id=dm_conversation.id,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            acting_user_id=user.id,
            content="Preview gone",
        )
        ChatService.delete_message(message_id=msg.id, user=user)
        dm_conversation.refresh_from_db()
        assert dm_conversation.last_message_preview == ""

    def test_delete_idempotent(self, user, dm_conversation):
        msg = ChatService.send_message(
            conversation_id=dm_conversation.id,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            acting_user_id=user.id,
            content="Delete twice",
        )
        ChatService.delete_message(message_id=msg.id, user=user)
        # Should not raise
        ChatService.delete_message(message_id=msg.id, user=user)

    def test_non_author_cannot_delete_in_dm(self, user, user_b, dm_conversation):
        msg = ChatService.send_message(
            conversation_id=dm_conversation.id,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            acting_user_id=user.id,
            content="Protected",
        )
        with pytest.raises(PermissionDenied):
            ChatService.delete_message(message_id=msg.id, user=user_b)

    def test_group_admin_can_delete_any_message(self, user, user_b, group_conversation):
        """user is admin in group_conversation."""
        msg = ChatService.send_message(
            conversation_id=group_conversation.id,
            sender_type=ParticipantType.USER,
            sender_id=user_b.id,
            acting_user_id=user_b.id,
            content="Admin will delete this",
        )
        # user (admin) deletes user_b's message
        ChatService.delete_message(message_id=msg.id, user=user)
        msg.refresh_from_db()
        assert msg.status == MessageStatus.DELETED


# =============================================================================
# WATERMARKS
# =============================================================================


class TestUpdateSeenWatermark:
    def test_updates_watermark(self, user, dm_conversation):
        msg = MessageFactory(
            conversation=dm_conversation,
            sequence_number=1,
        )
        ChatService.update_seen_watermark(
            conversation_id=dm_conversation.id,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            last_seen_message_id=msg.id,
        )
        cp = ConversationParticipant.objects.get(
            conversation=dm_conversation,
            participant_id=user.id,
            is_active=True,
        )
        assert cp.last_seen_message_id == msg.id
        assert cp.last_seen_at is not None

    def test_nonparticipant_raises_not_found(self, user_c, dm_conversation):
        msg_id = uuid.uuid4()
        with pytest.raises(NotFound):
            ChatService.update_seen_watermark(
                conversation_id=dm_conversation.id,
                participant_type=ParticipantType.USER,
                participant_id=user_c.id,
                last_seen_message_id=msg_id,
            )


class TestUpdateDeliveredWatermark:
    def test_updates_watermark(self, user, dm_conversation):
        msg = MessageFactory(
            conversation=dm_conversation,
            sequence_number=1,
        )
        ChatService.update_delivered_watermark(
            conversation_id=dm_conversation.id,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            last_delivered_message_id=msg.id,
        )
        cp = ConversationParticipant.objects.get(
            conversation=dm_conversation,
            participant_id=user.id,
            is_active=True,
        )
        assert cp.last_delivered_message_id == msg.id

    def test_nonparticipant_raises(self, user_c, dm_conversation):
        with pytest.raises(NotFound):
            ChatService.update_delivered_watermark(
                conversation_id=dm_conversation.id,
                participant_type=ParticipantType.USER,
                participant_id=user_c.id,
                last_delivered_message_id=uuid.uuid4(),
            )


# =============================================================================
# CHAT REQUESTS
# =============================================================================


class TestAcceptRequest:
    def test_accept_pending_request(self, user_b, dm_with_request):
        """user_b has a pending request in dm_with_request."""
        ChatService.accept_request(conversation_id=dm_with_request.id, user=user_b)
        cp = ConversationParticipant.objects.get(
            conversation=dm_with_request,
            participant_id=user_b.id,
            is_active=True,
        )
        assert cp.request_status == RequestStatus.ACCEPTED

    def test_accept_nonexistent_request_raises(self, user, dm_conversation):
        """user in dm_conversation has no pending request."""
        with pytest.raises(NotFound):
            ChatService.accept_request(conversation_id=dm_conversation.id, user=user)


class TestIgnoreRequest:
    def test_ignore_pending_request(self, user_b, dm_with_request):
        ChatService.ignore_request(conversation_id=dm_with_request.id, user=user_b)
        cp = ConversationParticipant.objects.get(
            conversation=dm_with_request,
            participant_id=user_b.id,
            is_active=True,
        )
        assert cp.request_status == RequestStatus.IGNORED

    def test_ignore_nonexistent_request_raises(self, user, dm_conversation):
        with pytest.raises(NotFound):
            ChatService.ignore_request(conversation_id=dm_conversation.id, user=user)


# =============================================================================
# ADD PARTICIPANT
# =============================================================================


class TestAddParticipant:
    def test_add_participant_to_group(self, user, group_conversation):
        new_user_id = uuid.uuid4()
        cp = ChatService.add_participant(
            conversation_id=group_conversation.id,
            participant_type=ParticipantType.USER,
            participant_id=new_user_id,
            added_by=user,
        )
        assert cp.participant_id == new_user_id
        assert cp.role == ParticipantRole.MEMBER

    def test_add_participant_to_dm_raises(self, user, dm_conversation):
        with pytest.raises(BusinessRuleViolation) as exc:
            ChatService.add_participant(
                conversation_id=dm_conversation.id,
                participant_type=ParticipantType.USER,
                participant_id=uuid.uuid4(),
                added_by=user,
            )
        assert exc.value.details["rule"] == "dm_no_add_participant"

    def test_non_admin_cannot_add(self, user_b, group_conversation):
        with pytest.raises(PermissionDenied):
            ChatService.add_participant(
                conversation_id=group_conversation.id,
                participant_type=ParticipantType.USER,
                participant_id=uuid.uuid4(),
                added_by=user_b,
            )

    def test_duplicate_active_participant_raises(
        self, user, user_b, group_conversation
    ):
        """user_b is already a participant."""
        with pytest.raises(ConflictError):
            ChatService.add_participant(
                conversation_id=group_conversation.id,
                participant_type=ParticipantType.USER,
                participant_id=user_b.id,
                added_by=user,
            )

    def test_rejoin_inactive_participant(self, user, user_b, group_conversation):
        """A previously removed participant can be re-added."""
        # Remove user_b
        cp = ConversationParticipant.objects.get(
            conversation=group_conversation,
            participant_id=user_b.id,
            is_active=True,
        )
        cp.is_active = False
        cp.removed_at = timezone.now()
        cp.save(update_fields=["is_active", "removed_at"])

        # Re-add
        rejoined = ChatService.add_participant(
            conversation_id=group_conversation.id,
            participant_type=ParticipantType.USER,
            participant_id=user_b.id,
            added_by=user,
        )
        assert rejoined.is_active is True
        assert rejoined.removed_at is None
        assert rejoined.role == ParticipantRole.MEMBER

    def test_system_message_sent_on_add(self, user, group_conversation):
        new_user_id = uuid.uuid4()
        ChatService.add_participant(
            conversation_id=group_conversation.id,
            participant_type=ParticipantType.USER,
            participant_id=new_user_id,
            added_by=user,
        )
        sys_msg = Message.objects.filter(
            conversation=group_conversation,
            content_type=MessageContentType.SYSTEM,
        ).last()
        assert sys_msg is not None
        assert str(new_user_id) in sys_msg.content


# =============================================================================
# REMOVE PARTICIPANT
# =============================================================================


class TestRemoveParticipant:
    @staticmethod
    def _row_pk(conversation, participant_id):
        return ConversationParticipant.objects.get(
            conversation=conversation,
            participant_type=ParticipantType.USER,
            participant_id=participant_id,
        ).id

    def test_remove_participant_from_group(self, user, user_b, group_conversation):
        ChatService.remove_participant(
            conversation_id=group_conversation.id,
            participant_pk=self._row_pk(group_conversation, user_b.id),
            removed_by=user,
        )
        cp = ConversationParticipant.objects.get(
            conversation=group_conversation,
            participant_id=user_b.id,
        )
        assert cp.is_active is False
        assert cp.removed_at is not None
        assert cp.removed_by == user

    def test_remove_from_dm_raises(self, user, user_b, dm_conversation):
        with pytest.raises(BusinessRuleViolation) as exc:
            ChatService.remove_participant(
                conversation_id=dm_conversation.id,
                participant_pk=self._row_pk(dm_conversation, user_b.id),
                removed_by=user,
            )
        assert exc.value.details["rule"] == "dm_no_remove_participant"

    def test_non_admin_cannot_remove(self, user_b, user_c, group_conversation):
        with pytest.raises(PermissionDenied):
            ChatService.remove_participant(
                conversation_id=group_conversation.id,
                participant_pk=self._row_pk(group_conversation, user_c.id),
                removed_by=user_b,
            )

    def test_remove_nonexistent_participant_raises(self, user, group_conversation):
        with pytest.raises(NotFound):
            ChatService.remove_participant(
                conversation_id=group_conversation.id,
                participant_pk=uuid.uuid4(),
                removed_by=user,
            )

    def test_system_message_sent_on_remove(self, user, user_b, group_conversation):
        ChatService.remove_participant(
            conversation_id=group_conversation.id,
            participant_pk=self._row_pk(group_conversation, user_b.id),
            removed_by=user,
        )
        sys_msg = Message.objects.filter(
            conversation=group_conversation,
            content_type=MessageContentType.SYSTEM,
        ).last()
        assert sys_msg is not None
        assert str(user_b.id) in sys_msg.content


# =============================================================================
# LEAVE CONVERSATION
# =============================================================================


class TestLeaveConversation:
    def test_leave_group(self, user_b, group_conversation):
        ChatService.leave_conversation(
            conversation_id=group_conversation.id, user=user_b
        )
        cp = ConversationParticipant.objects.get(
            conversation=group_conversation,
            participant_id=user_b.id,
        )
        assert cp.is_active is False
        assert cp.left_at is not None

    def test_leave_dm_raises(self, user, dm_conversation):
        with pytest.raises(BusinessRuleViolation) as exc:
            ChatService.leave_conversation(
                conversation_id=dm_conversation.id, user=user
            )
        assert exc.value.details["rule"] == "dm_no_leave"

    def test_last_participant_deactivates_conversation(self, user):
        conv = ConversationFactory(
            conversation_type=ConversationType.GROUP, name="Solo"
        )
        ConversationParticipant.objects.create(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            role=ParticipantRole.ADMIN,
        )
        ChatService.leave_conversation(conversation_id=conv.id, user=user)
        conv.refresh_from_db()
        assert conv.is_active is False

    def test_admin_succession(self, user, user_b, group_conversation):
        """When last admin leaves, oldest member is promoted."""
        ChatService.leave_conversation(conversation_id=group_conversation.id, user=user)
        # user_b or user_c should be promoted (whichever was added first)
        remaining_admins = ConversationParticipant.objects.filter(
            conversation=group_conversation,
            role=ParticipantRole.ADMIN,
            is_active=True,
        )
        assert remaining_admins.count() == 1

    def test_system_message_on_leave(self, user_b, group_conversation):
        ChatService.leave_conversation(
            conversation_id=group_conversation.id, user=user_b
        )
        sys_msg = Message.objects.filter(
            conversation=group_conversation,
            content_type=MessageContentType.SYSTEM,
        ).last()
        assert sys_msg is not None
        assert str(user_b.id) in sys_msg.content


# =============================================================================
# BLOCKS
# =============================================================================


class TestBlockParticipant:
    def test_block_user(self, user):
        blocked_id = uuid.uuid4()
        block = ChatService.block_participant(
            blocker=user,
            blocked_type=ParticipantType.USER,
            blocked_id=blocked_id,
        )
        assert block.blocker == user
        assert block.blocked_id == blocked_id

    def test_block_idempotent(self, user):
        blocked_id = uuid.uuid4()
        b1 = ChatService.block_participant(
            blocker=user,
            blocked_type=ParticipantType.USER,
            blocked_id=blocked_id,
        )
        b2 = ChatService.block_participant(
            blocker=user,
            blocked_type=ParticipantType.USER,
            blocked_id=blocked_id,
        )
        assert b1.id == b2.id

    def test_cannot_block_self(self, user):
        with pytest.raises(ValidationError):
            ChatService.block_participant(
                blocker=user,
                blocked_type=ParticipantType.USER,
                blocked_id=user.id,
            )


class TestUnblockParticipant:
    def test_unblock(self, user):
        blocked_id = uuid.uuid4()
        block = ChatBlockFactory(
            blocker=user,
            blocked_type=ParticipantType.USER,
            blocked_id=blocked_id,
        )
        ChatService.unblock_participant(blocker=user, block_id=block.id)
        assert not ChatBlock.objects.filter(id=block.id).exists()

    def test_unblock_nonexistent_raises(self, user):
        with pytest.raises(NotFound):
            ChatService.unblock_participant(blocker=user, block_id=uuid.uuid4())

    def test_unblock_other_users_block_raises(self, user, user_b):
        block = ChatBlockFactory(blocker=user_b)
        with pytest.raises(NotFound):
            ChatService.unblock_participant(blocker=user, block_id=block.id)


# =============================================================================
# GROUP MANAGEMENT
# =============================================================================


class TestPromoteToAdmin:
    def test_promote_member(self, user, user_b, group_conversation):
        ChatService.promote_to_admin(
            conversation_id=group_conversation.id,
            participant_id=user_b.id,
            user=user,
        )
        cp = ConversationParticipant.objects.get(
            conversation=group_conversation,
            participant_id=user_b.id,
            is_active=True,
        )
        assert cp.role == ParticipantRole.ADMIN

    def test_promote_already_admin_idempotent(self, user, group_conversation):
        """user is already admin — should not raise."""
        ChatService.promote_to_admin(
            conversation_id=group_conversation.id,
            participant_id=user.id,
            user=user,
        )

    def test_non_admin_cannot_promote(self, user_b, user_c, group_conversation):
        with pytest.raises(PermissionDenied):
            ChatService.promote_to_admin(
                conversation_id=group_conversation.id,
                participant_id=user_c.id,
                user=user_b,
            )

    def test_promote_nonexistent_raises(self, user, group_conversation):
        with pytest.raises(NotFound):
            ChatService.promote_to_admin(
                conversation_id=group_conversation.id,
                participant_id=uuid.uuid4(),
                user=user,
            )


class TestDemoteFromAdmin:
    def test_demote_admin_to_member(self, user, user_b, group_conversation):
        # First promote user_b to admin
        ChatService.promote_to_admin(
            conversation_id=group_conversation.id,
            participant_id=user_b.id,
            user=user,
        )
        # Now demote user_b
        ChatService.demote_from_admin(
            conversation_id=group_conversation.id,
            participant_id=user_b.id,
            user=user,
        )
        cp = ConversationParticipant.objects.get(
            conversation=group_conversation,
            participant_id=user_b.id,
            is_active=True,
        )
        assert cp.role == ParticipantRole.MEMBER

    def test_demote_already_member_idempotent(self, user, user_b, group_conversation):
        """user_b is already member — should not raise."""
        ChatService.demote_from_admin(
            conversation_id=group_conversation.id,
            participant_id=user_b.id,
            user=user,
        )

    def test_cannot_demote_last_admin(self, user, group_conversation):
        """Only one admin — cannot demote self."""
        with pytest.raises(BusinessRuleViolation) as exc:
            ChatService.demote_from_admin(
                conversation_id=group_conversation.id,
                participant_id=user.id,
                user=user,
            )
        assert exc.value.details["rule"] == "last_admin"

    def test_non_admin_cannot_demote(self, user_b, user, group_conversation):
        with pytest.raises(PermissionDenied):
            ChatService.demote_from_admin(
                conversation_id=group_conversation.id,
                participant_id=user.id,
                user=user_b,
            )

    def test_demote_sends_system_message(self, user, user_b, group_conversation):
        """Demoting an admin should create a system message."""
        ChatService.promote_to_admin(
            conversation_id=group_conversation.id,
            participant_id=user_b.id,
            user=user,
        )
        # Count messages before demote
        msg_count_before = Message.objects.filter(
            conversation=group_conversation
        ).count()

        ChatService.demote_from_admin(
            conversation_id=group_conversation.id,
            participant_id=user_b.id,
            user=user,
        )

        msgs = Message.objects.filter(
            conversation=group_conversation,
            content_type=MessageContentType.SYSTEM,
        ).order_by("-sequence_number")
        assert msgs.count() > 0
        latest_system = msgs.first()
        assert "was demoted from admin" in latest_system.content
        assert str(user_b.id) in latest_system.content


# =============================================================================
# INTERNAL HELPERS
# =============================================================================


class TestDetermineRequestStatus:
    @patch("apps.network.selectors.ConnectionSelector.is_connected", return_value=True)
    def test_connected_users_skip_request(self, mock_connected, user, user_b):
        result = ChatService._determine_request_status(
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            recipient_type=ParticipantType.USER,
            recipient_id=user_b.id,
            scope_type=ScopeType.GLOBAL,
        )
        assert result == RequestStatus.NONE

    @patch("apps.network.selectors.ConnectionSelector.is_connected", return_value=False)
    def test_strangers_get_pending(self, mock_connected, user, user_b):
        result = ChatService._determine_request_status(
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            recipient_type=ParticipantType.USER,
            recipient_id=user_b.id,
            scope_type=ScopeType.GLOBAL,
        )
        assert result == RequestStatus.PENDING

    def test_non_global_scope_no_request(self, user, user_b):
        result = ChatService._determine_request_status(
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            recipient_type=ParticipantType.USER,
            recipient_id=user_b.id,
            scope_type=ScopeType.BUSINESS,
        )
        assert result == RequestStatus.NONE

    def test_entity_sender_no_request(self, user):
        result = ChatService._determine_request_status(
            sender_type=ParticipantType.BUSINESS,
            sender_id=uuid.uuid4(),
            recipient_type=ParticipantType.USER,
            recipient_id=user.id,
            scope_type=ScopeType.GLOBAL,
        )
        assert result == RequestStatus.NONE

    def test_entity_recipient_no_request(self, user):
        result = ChatService._determine_request_status(
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            recipient_type=ParticipantType.BUSINESS,
            recipient_id=uuid.uuid4(),
            scope_type=ScopeType.GLOBAL,
        )
        assert result == RequestStatus.NONE


class TestGetNextSequenceNumber:
    def test_first_message_returns_1(self):
        conv = ConversationFactory()
        assert ChatService._get_next_sequence_number(conv.id) == 1

    def test_increments_correctly(self):
        conv = ConversationFactory()
        MessageFactory(conversation=conv, sequence_number=1)
        MessageFactory(conversation=conv, sequence_number=2)
        assert ChatService._get_next_sequence_number(conv.id) == 3
