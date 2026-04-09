"""
Chat Policy Tests
==================
Tests for ChatPolicy authorization logic.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from apps.chat.constants import (
    ConversationType,
    MessageContentType,
    ParticipantRole,
    ParticipantType,
    ScopeType,
)
from apps.chat.models import ConversationParticipant, Message
from apps.chat.policies import ChatPolicy
from apps.chat.tests.factories import (
    ConversationFactory,
    ConversationParticipantFactory,
    MessageFactory,
)
from apps.core.exceptions import PermissionDenied

pytestmark = pytest.mark.django_db


# =============================================================================
# VALIDATE SCOPE ELIGIBILITY
# =============================================================================


class TestValidateScopeEligibility:
    def test_user_global_scope_allowed(self, user):
        """Any authenticated user can participate in global scope."""
        # Should not raise
        ChatPolicy.validate_scope_eligibility(
            user=user,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            scope_type=ScopeType.GLOBAL,
            scope_id=None,
        )

    def test_entity_global_scope_with_permission(self, user):
        """Entity in global scope — user must have can_manage_chat."""
        biz_id = uuid.uuid4()
        with patch.object(ChatPolicy, "can_manage_entity_chat", return_value=True):
            ChatPolicy.validate_scope_eligibility(
                user=user,
                participant_type=ParticipantType.BUSINESS,
                participant_id=biz_id,
                scope_type=ScopeType.GLOBAL,
                scope_id=None,
            )

    def test_entity_global_scope_without_permission(self, user):
        biz_id = uuid.uuid4()
        with patch.object(ChatPolicy, "can_manage_entity_chat", return_value=False):
            with pytest.raises(PermissionDenied):
                ChatPolicy.validate_scope_eligibility(
                    user=user,
                    participant_type=ParticipantType.BUSINESS,
                    participant_id=biz_id,
                    scope_type=ScopeType.GLOBAL,
                    scope_id=None,
                )

    def test_entity_non_global_scope_rejected(self, user):
        """Entities can only chat in global scope."""
        with pytest.raises(PermissionDenied):
            ChatPolicy.validate_scope_eligibility(
                user=user,
                participant_type=ParticipantType.BUSINESS,
                participant_id=uuid.uuid4(),
                scope_type=ScopeType.BUSINESS,
                scope_id=uuid.uuid4(),
            )

    @patch("apps.rbac.selectors.MembershipSelector.is_user_member_of_account")
    def test_user_business_scope_member(self, mock_member, user):
        mock_member.return_value = True
        biz_id = uuid.uuid4()
        ChatPolicy.validate_scope_eligibility(
            user=user,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            scope_type=ScopeType.BUSINESS,
            scope_id=biz_id,
        )
        mock_member.assert_called_once_with(
            user=user, account_type="business", account_id=biz_id
        )

    @patch("apps.rbac.selectors.MembershipSelector.is_user_member_of_account")
    def test_user_business_scope_non_member(self, mock_member, user):
        mock_member.return_value = False
        with pytest.raises(PermissionDenied):
            ChatPolicy.validate_scope_eligibility(
                user=user,
                participant_type=ParticipantType.USER,
                participant_id=user.id,
                scope_type=ScopeType.BUSINESS,
                scope_id=uuid.uuid4(),
            )

    def test_business_scope_requires_scope_id(self, user):
        with pytest.raises(PermissionDenied):
            ChatPolicy.validate_scope_eligibility(
                user=user,
                participant_type=ParticipantType.USER,
                participant_id=user.id,
                scope_type=ScopeType.BUSINESS,
                scope_id=None,
            )

    @patch("apps.rbac.selectors.MembershipSelector.is_user_member_of_account")
    def test_user_platform_scope_member(self, mock_member, user):
        mock_member.return_value = True
        plat_id = uuid.uuid4()
        ChatPolicy.validate_scope_eligibility(
            user=user,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            scope_type=ScopeType.PLATFORM,
            scope_id=plat_id,
        )
        mock_member.assert_called_once_with(
            user=user, account_type="platform", account_id=plat_id
        )

    @patch("apps.rbac.selectors.MembershipSelector.is_user_member_of_account")
    def test_user_platform_scope_non_member(self, mock_member, user):
        mock_member.return_value = False
        with pytest.raises(PermissionDenied):
            ChatPolicy.validate_scope_eligibility(
                user=user,
                participant_type=ParticipantType.USER,
                participant_id=user.id,
                scope_type=ScopeType.PLATFORM,
                scope_id=uuid.uuid4(),
            )

    def test_platform_scope_requires_scope_id(self, user):
        with pytest.raises(PermissionDenied):
            ChatPolicy.validate_scope_eligibility(
                user=user,
                participant_type=ParticipantType.USER,
                participant_id=user.id,
                scope_type=ScopeType.PLATFORM,
                scope_id=None,
            )

    def test_unknown_scope_type_raises(self, user):
        with pytest.raises(PermissionDenied):
            ChatPolicy.validate_scope_eligibility(
                user=user,
                participant_type=ParticipantType.USER,
                participant_id=user.id,
                scope_type="unknown",
                scope_id=None,
            )


# =============================================================================
# CAN MANAGE ENTITY CHAT
# =============================================================================


class TestCanManageEntityChat:
    def test_staff_bypass(self, user):
        user.is_staff = True
        user.save(update_fields=["is_staff"])
        assert ChatPolicy.can_manage_entity_chat(
            user=user,
            account_type=ParticipantType.BUSINESS,
            account_id=uuid.uuid4(),
        )

    @patch("apps.rbac.selectors.PermissionSelector.get_permissions_for_membership")
    @patch(
        "apps.rbac.selectors.MembershipSelector.get_active_membership_for_user_account"
    )
    def test_member_with_permission(self, mock_membership, mock_perms, user):
        mock_membership.return_value = MagicMock()
        mock_perms.return_value = [("can_manage_chat", "business")]
        assert ChatPolicy.can_manage_entity_chat(
            user=user,
            account_type=ParticipantType.BUSINESS,
            account_id=uuid.uuid4(),
        )

    @patch("apps.rbac.selectors.PermissionSelector.get_permissions_for_membership")
    @patch(
        "apps.rbac.selectors.MembershipSelector.get_active_membership_for_user_account"
    )
    def test_member_without_permission(self, mock_membership, mock_perms, user):
        mock_membership.return_value = MagicMock()
        mock_perms.return_value = [("can_edit_business", "business")]
        assert not ChatPolicy.can_manage_entity_chat(
            user=user,
            account_type=ParticipantType.BUSINESS,
            account_id=uuid.uuid4(),
        )

    @patch(
        "apps.rbac.selectors.MembershipSelector.get_active_membership_for_user_account"
    )
    def test_non_member(self, mock_membership, user):
        mock_membership.return_value = None
        assert not ChatPolicy.can_manage_entity_chat(
            user=user,
            account_type=ParticipantType.BUSINESS,
            account_id=uuid.uuid4(),
        )


# =============================================================================
# CAN MANAGE GROUP
# =============================================================================


class TestCanManageGroup:
    def test_admin_can_manage(self, user, group_conversation):
        assert ChatPolicy.can_manage_group(user=user, conversation=group_conversation)

    def test_member_cannot_manage(self, user_b, group_conversation):
        assert not ChatPolicy.can_manage_group(
            user=user_b, conversation=group_conversation
        )

    def test_dm_returns_false(self, user, dm_conversation):
        assert not ChatPolicy.can_manage_group(user=user, conversation=dm_conversation)

    def test_nonparticipant_cannot_manage(self, user_c):
        conv = ConversationFactory(
            conversation_type=ConversationType.GROUP, name="Group"
        )
        assert not ChatPolicy.can_manage_group(user=user_c, conversation=conv)


# =============================================================================
# CAN SEND MESSAGE
# =============================================================================


class TestCanSendMessage:
    def test_active_user_participant(self, user, dm_conversation):
        assert ChatPolicy.can_send_message(
            user=user,
            conversation=dm_conversation,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
        )

    def test_inactive_participant_cannot_send(self, user):
        conv = ConversationFactory()
        ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            is_active=False,
        )
        assert not ChatPolicy.can_send_message(
            user=user,
            conversation=conv,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
        )

    def test_nonparticipant_cannot_send(self, user):
        conv = ConversationFactory()
        assert not ChatPolicy.can_send_message(
            user=user,
            conversation=conv,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
        )

    def test_entity_sender_with_permission(self, user):
        biz_id = uuid.uuid4()
        conv = ConversationFactory()
        ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.BUSINESS,
            participant_id=biz_id,
        )
        with patch.object(ChatPolicy, "can_manage_entity_chat", return_value=True):
            assert ChatPolicy.can_send_message(
                user=user,
                conversation=conv,
                sender_type=ParticipantType.BUSINESS,
                sender_id=biz_id,
            )

    def test_entity_sender_without_permission(self, user):
        biz_id = uuid.uuid4()
        conv = ConversationFactory()
        ConversationParticipantFactory(
            conversation=conv,
            participant_type=ParticipantType.BUSINESS,
            participant_id=biz_id,
        )
        with patch.object(ChatPolicy, "can_manage_entity_chat", return_value=False):
            assert not ChatPolicy.can_send_message(
                user=user,
                conversation=conv,
                sender_type=ParticipantType.BUSINESS,
                sender_id=biz_id,
            )


# =============================================================================
# CAN DELETE MESSAGE
# =============================================================================


class TestCanDeleteMessage:
    def test_author_can_delete(self, user, dm_conversation):
        msg = MessageFactory(
            conversation=dm_conversation,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            sequence_number=1,
        )
        assert ChatPolicy.can_delete_message(
            user=user, message=msg, conversation=dm_conversation
        )

    def test_non_author_cannot_delete_in_dm(self, user, user_b, dm_conversation):
        msg = MessageFactory(
            conversation=dm_conversation,
            sender_type=ParticipantType.USER,
            sender_id=user.id,
            sequence_number=1,
        )
        assert not ChatPolicy.can_delete_message(
            user=user_b, message=msg, conversation=dm_conversation
        )

    def test_acting_user_can_delete_entity_message(self, user):
        conv = ConversationFactory()
        msg = MessageFactory(
            conversation=conv,
            sender_type=ParticipantType.BUSINESS,
            sender_id=uuid.uuid4(),
            acting_user_id=user.id,
            sequence_number=1,
        )
        assert ChatPolicy.can_delete_message(user=user, message=msg, conversation=conv)

    def test_group_admin_can_delete_any(self, user, user_b, group_conversation):
        msg = MessageFactory(
            conversation=group_conversation,
            sender_type=ParticipantType.USER,
            sender_id=user_b.id,
            sequence_number=1,
        )
        # user is admin
        assert ChatPolicy.can_delete_message(
            user=user, message=msg, conversation=group_conversation
        )

    def test_staff_can_delete(self, user, dm_conversation):
        user.is_staff = True
        user.save(update_fields=["is_staff"])
        other_id = uuid.uuid4()
        msg = MessageFactory(
            conversation=dm_conversation,
            sender_type=ParticipantType.USER,
            sender_id=other_id,
            sequence_number=1,
        )
        assert ChatPolicy.can_delete_message(
            user=user, message=msg, conversation=dm_conversation
        )


# =============================================================================
# GET VIEWER PERMISSIONS (Tier 1.5)
# =============================================================================


class TestGetViewerPermissions:
    def test_participant_permissions(self, user, dm_conversation):
        perms = ChatPolicy.get_viewer_permissions(
            user=user, conversation=dm_conversation
        )
        assert perms["can_send_message"] is True
        assert perms["can_view_messages"] is True
        assert perms["can_leave"] is True
        # DM — no group management
        assert perms["can_manage_group"] is False
        assert perms["can_add_participant"] is False
        assert perms["can_remove_participant"] is False
        assert perms["can_edit_group"] is False

    def test_group_admin_permissions(self, user, group_conversation):
        perms = ChatPolicy.get_viewer_permissions(
            user=user, conversation=group_conversation
        )
        assert perms["can_send_message"] is True
        assert perms["can_manage_group"] is True
        assert perms["can_add_participant"] is True
        assert perms["can_remove_participant"] is True
        assert perms["can_edit_group"] is True

    def test_group_member_permissions(self, user_b, group_conversation):
        perms = ChatPolicy.get_viewer_permissions(
            user=user_b, conversation=group_conversation
        )
        assert perms["can_send_message"] is True
        assert perms["can_manage_group"] is False
        assert perms["can_add_participant"] is False

    def test_nonparticipant_permissions(self, user_c):
        conv = ConversationFactory()
        perms = ChatPolicy.get_viewer_permissions(user=user_c, conversation=conv)
        assert perms["can_send_message"] is False
        assert perms["can_view_messages"] is False
        assert perms["can_leave"] is False
        assert perms["can_manage_group"] is False
