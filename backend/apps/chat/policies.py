"""
Chat Policies
=============
Authorization logic for all chat actions.
"""

from uuid import UUID

from apps.chat.constants import (
    ConversationType,
    ParticipantRole,
    ParticipantType,
    ScopeType,
)
from apps.core.exceptions import PermissionDenied


class ChatPolicy:
    """Authorization for all chat actions."""

    @staticmethod
    def validate_scope_eligibility(
        *,
        user,
        participant_type: str,
        participant_id: UUID,
        scope_type: str,
        scope_id: UUID | None,
    ) -> None:
        """
        Validates that a participant can act in the given scope.
        Raises PermissionDenied if not eligible.

        Rules:
        - Global scope: any authenticated user, or entity with can_manage_chat
        - Business scope: must be ACTIVE member of that business
        - Platform scope: must be ACTIVE platform member
        - Entity participants: global scope only, acting_user must have can_manage_chat
        """
        # Entity participants are global-scope only
        if participant_type != ParticipantType.USER:
            if scope_type != ScopeType.GLOBAL:
                raise PermissionDenied(
                    message="Entity participants can only chat in global scope",
                    action="chat",
                    resource="Conversation",
                )
            # Verify the acting user has can_manage_chat for this entity
            if not ChatPolicy.can_manage_entity_chat(
                user=user,
                account_type=participant_type,
                account_id=participant_id,
            ):
                raise PermissionDenied(
                    message="You do not have permission to manage chat for this entity",
                    action="manage_entity_chat",
                    resource="Conversation",
                )
            return

        # User participants
        if scope_type == ScopeType.GLOBAL:
            # Any authenticated user can participate in global scope
            return

        if scope_type == ScopeType.BUSINESS:
            if not scope_id:
                raise PermissionDenied(
                    message="Business scope requires scope_id",
                    action="chat",
                    resource="Conversation",
                )
            from apps.rbac.selectors import MembershipSelector

            if not MembershipSelector.is_user_member_of_account(
                user=user,
                account_type="business",
                account_id=scope_id,
            ):
                raise PermissionDenied(
                    message="You must be an active member of this business to chat here",
                    action="chat",
                    resource="Conversation",
                )
            return

        if scope_type == ScopeType.PLATFORM:
            from apps.rbac.selectors import MembershipSelector

            if not scope_id:
                raise PermissionDenied(
                    message="Platform scope requires scope_id",
                    action="chat",
                    resource="Conversation",
                )
            if not MembershipSelector.is_user_member_of_account(
                user=user,
                account_type="platform",
                account_id=scope_id,
            ):
                raise PermissionDenied(
                    message="You must be an active platform member to chat here",
                    action="chat",
                    resource="Conversation",
                )
            return

        raise PermissionDenied(
            message=f"Unknown scope type: {scope_type}",
            action="chat",
            resource="Conversation",
        )

    @staticmethod
    def can_manage_entity_chat(*, user, account_type: str, account_id: UUID) -> bool:
        """Check if user has can_manage_chat permission for this entity."""
        if user.is_staff or user.is_superuser:
            return True

        from apps.rbac.selectors import MembershipSelector, PermissionSelector

        membership = MembershipSelector.get_active_membership_for_user_account(
            user=user,
            account_type=account_type,
            account_id=account_id,
        )
        if not membership:
            return False

        permissions = PermissionSelector.get_permissions_for_membership(
            membership_id=membership.id,
        )
        return any(code == "can_manage_chat" for code, scope in permissions)

    @staticmethod
    def can_manage_group(*, user, conversation) -> bool:
        """Check if user is admin of this group conversation."""
        if conversation.conversation_type != ConversationType.GROUP:
            return False

        from apps.chat.models import ConversationParticipant

        return ConversationParticipant.objects.filter(
            conversation=conversation,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            role=ParticipantRole.ADMIN,
            is_active=True,
        ).exists()

    @staticmethod
    def can_send_message(
        *, user, conversation, sender_type: str, sender_id: UUID
    ) -> bool:
        """Check if user can send a message to this conversation."""
        from apps.chat.models import ConversationParticipant

        # Must be active participant
        participant = ConversationParticipant.objects.filter(
            conversation=conversation,
            participant_type=sender_type,
            participant_id=sender_id,
            is_active=True,
        ).first()
        if not participant:
            return False

        # For entity senders, verify acting user has permission
        if sender_type != ParticipantType.USER:
            if not ChatPolicy.can_manage_entity_chat(
                user=user,
                account_type=sender_type,
                account_id=sender_id,
            ):
                return False

        return True

    @staticmethod
    def can_delete_message(*, user, message, conversation) -> bool:
        """
        Check if user can delete this message.

        Who can delete:
        - Message author (any time)
        - Group admin (any message in their group)
        - Org-scope moderator with moderation permission
        """
        # Author can always delete own messages
        if message.sender_type == ParticipantType.USER and message.sender_id == user.id:
            return True

        # Entity message — acting user can delete
        if message.acting_user_id and message.acting_user_id == user.id:
            return True

        # Group admin can delete any message
        if ChatPolicy.can_manage_group(user=user, conversation=conversation):
            return True

        # Staff/superuser can always delete
        if user.is_staff or user.is_superuser:
            return True

        return False

    @staticmethod
    def get_viewer_permissions(*, user, conversation) -> dict:
        """Tier 1.5 permissions for conversation detail view."""
        from apps.chat.models import ConversationParticipant

        is_participant = ConversationParticipant.objects.filter(
            conversation=conversation,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            is_active=True,
        ).exists()

        is_admin = False
        if is_participant and conversation.conversation_type == ConversationType.GROUP:
            is_admin = ConversationParticipant.objects.filter(
                conversation=conversation,
                participant_type=ParticipantType.USER,
                participant_id=user.id,
                role=ParticipantRole.ADMIN,
                is_active=True,
            ).exists()

        return {
            "can_send_message": is_participant,
            "can_view_messages": is_participant,
            "can_leave": is_participant,
            "can_manage_group": is_admin,
            "can_add_participant": is_admin,
            "can_remove_participant": is_admin,
            "can_edit_group": is_admin,
        }
