"""
Chat Service
=============
Write operations for the chat system.
All methods are @staticmethod with @transaction.atomic for writes.
"""

from uuid import UUID

from django.db import models, transaction
from django.utils import timezone

from apps.chat.constants import (
    CHAT_ALLOWED_IMAGE_EXTENSIONS,
    CHAT_ALLOWED_IMAGE_TYPES,
    CHAT_ATTACHMENT_ORPHAN_TTL_HOURS,
    CHAT_GROUP_MAX_PARTICIPANTS,
    CHAT_MAX_ATTACHMENTS_PER_MESSAGE,
    CHAT_MAX_IMAGE_SIZE,
    CHAT_MESSAGE_EDIT_WINDOW_MINUTES,
    CHAT_MESSAGE_MAX_LENGTH,
    CHAT_MESSAGE_PREVIEW_LENGTH,
    CHAT_REQUEST_MAX_MESSAGES,
    AttachmentType,
    ConversationType,
    MessageContentType,
    MessageStatus,
    ParticipantRole,
    ParticipantType,
    ReactionType,
    RequestStatus,
    ScopeType,
)
from apps.chat.models import (
    ChatBlock,
    Conversation,
    ConversationParticipant,
    Message,
    MessageAttachment,
    MessageReaction,
)
from apps.chat.policies import ChatPolicy
from apps.chat.selectors import ChatSelector
from apps.core.exceptions import (
    BusinessRuleViolation,
    ConflictError,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from apps.core.observability import get_logger
from apps.core.observability.audit import AuditLog, AuditService

logger = get_logger(__name__)


class ChatService:
    """Write operations for the chat system."""

    # =========================================================================
    # CONVERSATIONS
    # =========================================================================

    @staticmethod
    @transaction.atomic
    def create_conversation(
        *,
        scope_type: str,
        scope_id: UUID | None = None,
        conversation_type: str,
        participant_ids: list[dict],
        name: str = "",
        creator_type: str = ParticipantType.USER,
        creator_id: UUID,
        acting_user,
        request=None,
    ) -> Conversation:
        """
        Create a new conversation (DM or group).

        Args:
            scope_type: Scope isolation (global, business, platform)
            scope_id: Scope identifier (None for global)
            conversation_type: "direct" or "group"
            participant_ids: List of {"participant_type": str, "participant_id": UUID}
            name: Group name (required for group, ignored for DM)
            creator_type: Type of the creator participant
            creator_id: ID of the creator participant
            acting_user: The authenticated user performing the action
            request: HTTP request for audit context
        """
        # Validate scope eligibility for creator
        ChatPolicy.validate_scope_eligibility(
            user=acting_user,
            participant_type=creator_type,
            participant_id=creator_id,
            scope_type=scope_type,
            scope_id=scope_id,
        )

        # DM validation
        if conversation_type == ConversationType.DIRECT:
            if len(participant_ids) != 1:
                raise ValidationError(
                    message="Direct messages require exactly one other participant",
                    field="participant_ids",
                )

            other = participant_ids[0]

            # Check for existing DM
            existing = ChatSelector.get_dm_conversation(
                scope_type=scope_type,
                scope_id=scope_id,
                participant_a_type=creator_type,
                participant_a_id=creator_id,
                participant_b_type=other["participant_type"],
                participant_b_id=other["participant_id"],
            )
            if existing:
                return existing

            # Check block status
            ChatService._check_block_status(
                sender_type=creator_type,
                sender_id=creator_id,
                recipient_type=other["participant_type"],
                recipient_id=other["participant_id"],
            )

        # Group validation
        if conversation_type == ConversationType.GROUP:
            if not name.strip():
                raise ValidationError(
                    message="Group name is required",
                    field="name",
                )
            if len(participant_ids) > CHAT_GROUP_MAX_PARTICIPANTS - 1:
                raise BusinessRuleViolation(
                    message=f"Group cannot exceed {CHAT_GROUP_MAX_PARTICIPANTS} participants",
                    rule="group_max_participants",
                )

        # Create conversation
        conversation = Conversation.objects.create(
            scope_type=scope_type,
            scope_id=scope_id,
            conversation_type=conversation_type,
            name=name,
            created_by_type=creator_type,
            created_by_id=creator_id,
        )

        # Add creator as participant (admin for groups)
        creator_role = (
            ParticipantRole.ADMIN
            if conversation_type == ConversationType.GROUP
            else ParticipantRole.MEMBER
        )
        ConversationParticipant.objects.create(
            conversation=conversation,
            participant_type=creator_type,
            participant_id=creator_id,
            role=creator_role,
            request_status=RequestStatus.NONE,
            added_by=acting_user,
        )

        # Add other participants
        for p in participant_ids:
            # Determine request status for DMs in global scope
            request_status = RequestStatus.NONE
            if (
                conversation_type == ConversationType.DIRECT
                and scope_type == ScopeType.GLOBAL
            ):
                request_status = ChatService._determine_request_status(
                    sender_type=creator_type,
                    sender_id=creator_id,
                    recipient_type=p["participant_type"],
                    recipient_id=p["participant_id"],
                    scope_type=scope_type,
                )

            ConversationParticipant.objects.create(
                conversation=conversation,
                participant_type=p["participant_type"],
                participant_id=p["participant_id"],
                role=ParticipantRole.MEMBER,
                request_status=request_status,
                added_by=acting_user,
            )

        logger.info(
            "chat.conversation.created",
            conversation_id=str(conversation.id),
            scope_type=scope_type,
            conversation_type=conversation_type,
            creator=f"{creator_type}:{creator_id}",
            participant_count=len(participant_ids) + 1,
        )

        AuditService.log(
            action=AuditLog.Action.CHAT_CONVERSATION_CREATED,
            actor=acting_user,
            resource=conversation,
            request=request,
            details={
                "scope_type": scope_type,
                "scope_id": str(scope_id) if scope_id else None,
                "conversation_type": conversation_type,
                "creator_type": creator_type,
                "creator_id": str(creator_id),
                "participant_ids": [
                    f"{p['participant_type']}:{p['participant_id']}"
                    for p in participant_ids
                ],
            },
        )

        # Notify recipient of chat request (DM with PENDING only)
        if conversation_type == ConversationType.DIRECT:
            pending_participants = ConversationParticipant.objects.filter(
                conversation=conversation,
                request_status=RequestStatus.PENDING,
            )
            for pp in pending_participants:
                if pp.participant_type == ParticipantType.USER:
                    from apps.users.models import User

                    recipient = User.objects.filter(id=pp.participant_id).first()
                    if recipient:
                        transaction.on_commit(
                            lambda r=recipient: ChatService._notify_safe(
                                "request_received",
                                conversation=conversation,
                                requester_name=f"{creator_type}:{creator_id}",
                                recipient_user=r,
                            )
                        )

        return conversation

    @staticmethod
    @transaction.atomic
    def update_group(
        *,
        conversation_id: UUID,
        name: str | None = None,
        description: str | None = None,
        user,
        request=None,
    ) -> Conversation:
        """Update group conversation metadata."""
        conversation = ChatSelector.get_conversation_by_id(
            conversation_id=conversation_id
        )

        if conversation.conversation_type != ConversationType.GROUP:
            raise BusinessRuleViolation(
                message="Cannot update metadata on a direct message",
                rule="dm_not_updateable",
            )

        if not ChatPolicy.can_manage_group(user=user, conversation=conversation):
            raise PermissionDenied(
                message="Only group admins can update group metadata",
                action="update_group",
                resource="Conversation",
            )

        update_fields = ["updated_at"]
        if name is not None:
            conversation.name = name
            update_fields.append("name")
        if description is not None:
            conversation.description = description
            update_fields.append("description")

        conversation.save(update_fields=update_fields)

        logger.info(
            "chat.group.updated",
            conversation_id=str(conversation_id),
            user_id=str(user.id),
        )

        return conversation

    # =========================================================================
    # MESSAGES
    # =========================================================================

    @staticmethod
    @transaction.atomic
    def send_message(
        *,
        conversation_id: UUID,
        sender_type: str,
        sender_id: UUID,
        acting_user_id: UUID,
        content: str,
        content_type: str = MessageContentType.TEXT,
        metadata: dict | None = None,
        attachment_ids: list[UUID] | None = None,
        request=None,
    ) -> Message:
        """
        Send a message to a conversation.

        Args:
            attachment_ids: Optional list of orphan attachment UUIDs to link to this message.
        """
        has_attachments = bool(attachment_ids)
        if not content.strip() and not has_attachments:
            raise ValidationError(
                message="Either content or attachments are required",
                field="content",
            )
        if len(content) > CHAT_MESSAGE_MAX_LENGTH:
            raise ValidationError(
                message=f"Message exceeds maximum length of {CHAT_MESSAGE_MAX_LENGTH} characters",
                field="content",
            )

        conversation = ChatSelector.get_conversation_by_id(
            conversation_id=conversation_id
        )

        # Verify sender is an active participant
        participant = ChatSelector.get_participant(
            conversation_id=conversation_id,
            participant_type=sender_type,
            participant_id=sender_id,
        )
        if not participant:
            raise PermissionDenied(
                message="You are not a participant in this conversation",
                action="send_message",
                resource="Conversation",
            )

        # Check DM request status — if recipient has pending request,
        # limit to CHAT_REQUEST_MAX_MESSAGES
        if conversation.conversation_type == ConversationType.DIRECT:
            ChatService._check_dm_request_limit(
                conversation=conversation,
                sender_type=sender_type,
                sender_id=sender_id,
            )

        # Get next sequence number
        seq = ChatService._get_next_sequence_number(conversation_id)

        # Create message
        message = Message.objects.create(
            conversation=conversation,
            sender_type=sender_type,
            sender_id=sender_id,
            acting_user_id=acting_user_id if sender_type != ParticipantType.USER else None,
            content_type=content_type,
            content=content,
            metadata=metadata or {},
            sequence_number=seq,
        )

        # Link attachments if provided
        if attachment_ids:
            ChatService._link_attachments_to_message(
                message=message,
                attachment_ids=attachment_ids,
                conversation_id=conversation_id,
                uploaded_by_id=acting_user_id if sender_type != ParticipantType.USER else sender_id,
            )

        # Update conversation denormalized fields
        ChatService._update_conversation_last_message(conversation, message)

        logger.info(
            "chat.message.sent",
            conversation_id=str(conversation_id),
            message_id=str(message.id),
            sender=f"{sender_type}:{sender_id}",
            sequence_number=seq,
            attachment_count=len(attachment_ids) if attachment_ids else 0,
        )

        # Audit entity messages only (user messages are too high-volume)
        if sender_type != ParticipantType.USER:
            from apps.users.models import User

            acting_user = User.objects.filter(id=acting_user_id).first()
            AuditService.log(
                action=AuditLog.Action.CHAT_MESSAGE_SENT,
                actor=acting_user,
                resource=message,
                request=request,
                details={
                    "conversation_id": str(conversation_id),
                    "sender_type": sender_type,
                    "sender_id": str(sender_id),
                    "acting_user_id": str(acting_user_id),
                },
            )

        transaction.on_commit(
            lambda: ChatService._notify_safe(
                "new_message", message=message, conversation=conversation
            )
        )

        return message

    @staticmethod
    @transaction.atomic
    def edit_message(
        *,
        message_id: UUID,
        new_content: str,
        user,
        request=None,
    ) -> Message:
        """Edit a message within the edit window."""
        message = ChatSelector.get_message_by_id(message_id=message_id)

        # Only author can edit
        if not (
            message.sender_type == ParticipantType.USER
            and message.sender_id == user.id
        ) and not (
            message.acting_user_id and message.acting_user_id == user.id
        ):
            raise PermissionDenied(
                message="You can only edit your own messages",
                action="edit_message",
                resource="Message",
            )

        if message.status == MessageStatus.DELETED:
            raise BusinessRuleViolation(
                message="Cannot edit a deleted message",
                rule="message_deleted",
            )

        # Check edit window
        elapsed = (timezone.now() - message.created_at).total_seconds() / 60
        if elapsed > CHAT_MESSAGE_EDIT_WINDOW_MINUTES:
            raise BusinessRuleViolation(
                message=f"Edit window of {CHAT_MESSAGE_EDIT_WINDOW_MINUTES} minutes has expired",
                rule="edit_window_expired",
            )

        if not new_content.strip():
            raise ValidationError(
                message="Message content cannot be empty",
                field="content",
            )
        if len(new_content) > CHAT_MESSAGE_MAX_LENGTH:
            raise ValidationError(
                message=f"Message exceeds maximum length of {CHAT_MESSAGE_MAX_LENGTH} characters",
                field="content",
            )

        # Preserve original content
        if not message.original_content:
            message.original_content = message.content

        message.content = new_content
        message.status = MessageStatus.EDITED
        message.edited_at = timezone.now()
        message.save(
            update_fields=[
                "content",
                "original_content",
                "status",
                "edited_at",
                "updated_at",
            ]
        )

        # Update last message preview if this was the last message
        conversation = message.conversation
        if conversation.last_message_id == message.id:
            conversation.last_message_preview = new_content[:CHAT_MESSAGE_PREVIEW_LENGTH]
            conversation.save(update_fields=["last_message_preview", "updated_at"])

        logger.info(
            "chat.message.edited",
            message_id=str(message_id),
            conversation_id=str(message.conversation_id),
            user_id=str(user.id),
        )

        AuditService.log(
            action=AuditLog.Action.CHAT_MESSAGE_EDITED,
            actor=user,
            resource=message,
            request=request,
            details={
                "conversation_id": str(message.conversation_id),
                "message_id": str(message_id),
                "acting_user_id": str(user.id),
            },
        )

        return message

    @staticmethod
    @transaction.atomic
    def delete_message(
        *,
        message_id: UUID,
        user,
        request=None,
    ) -> None:
        """Delete a message (soft delete — preserves original_content for moderation)."""
        message = ChatSelector.get_message_by_id(message_id=message_id)
        conversation = message.conversation

        if not ChatPolicy.can_delete_message(
            user=user, message=message, conversation=conversation
        ):
            raise PermissionDenied(
                message="You do not have permission to delete this message",
                action="delete_message",
                resource="Message",
            )

        if message.status == MessageStatus.DELETED:
            return  # Idempotent

        # Preserve original content for moderation
        message.original_content = message.content
        message.content = ""
        message.status = MessageStatus.DELETED
        message.save(
            update_fields=["content", "original_content", "status", "updated_at"]
        )

        # Update last message preview if this was the last message
        if conversation.last_message_id == message.id:
            conversation.last_message_preview = ""
            conversation.save(update_fields=["last_message_preview", "updated_at"])

        logger.info(
            "chat.message.deleted",
            message_id=str(message_id),
            conversation_id=str(conversation.id),
            user_id=str(user.id),
        )

        AuditService.log(
            action=AuditLog.Action.CHAT_MESSAGE_DELETED,
            actor=user,
            resource=message,
            request=request,
            details={
                "conversation_id": str(conversation.id),
                "message_id": str(message_id),
                "acting_user_id": str(user.id),
            },
        )

    # =========================================================================
    # WATERMARKS
    # =========================================================================

    @staticmethod
    def update_seen_watermark(
        *,
        conversation_id: UUID,
        participant_type: str,
        participant_id: UUID,
        last_seen_message_id: UUID,
    ) -> None:
        """Update the seen watermark for a participant."""
        updated = ConversationParticipant.objects.filter(
            conversation_id=conversation_id,
            participant_type=participant_type,
            participant_id=participant_id,
            is_active=True,
        ).update(
            last_seen_message_id=last_seen_message_id,
            last_seen_at=timezone.now(),
        )
        if not updated:
            raise NotFound(resource="ConversationParticipant")

    @staticmethod
    def update_delivered_watermark(
        *,
        conversation_id: UUID,
        participant_type: str,
        participant_id: UUID,
        last_delivered_message_id: UUID,
    ) -> None:
        """Update the delivered watermark for a participant."""
        updated = ConversationParticipant.objects.filter(
            conversation_id=conversation_id,
            participant_type=participant_type,
            participant_id=participant_id,
            is_active=True,
        ).update(last_delivered_message_id=last_delivered_message_id)
        if not updated:
            raise NotFound(resource="ConversationParticipant")

    # =========================================================================
    # CHAT REQUESTS
    # =========================================================================

    @staticmethod
    @transaction.atomic
    def accept_request(*, conversation_id: UUID, user) -> None:
        """Accept a pending chat request."""
        participant = ConversationParticipant.objects.filter(
            conversation_id=conversation_id,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            request_status=RequestStatus.PENDING,
            is_active=True,
        ).first()

        if not participant:
            raise NotFound(
                message="No pending chat request found",
                resource="ChatRequest",
            )

        participant.request_status = RequestStatus.ACCEPTED
        participant.save(update_fields=["request_status", "updated_at"])

        # Notify the original requester (conversation creator) that request was accepted
        conversation = Conversation.objects.filter(id=conversation_id).first()
        if conversation:
            creator_id = conversation.created_by_id
            if conversation.created_by_type == ParticipantType.USER and creator_id != user.id:
                from apps.users.models import User

                requester = User.objects.filter(id=creator_id).first()
                if requester:
                    accepter_name = user.username or str(user.id)
                    transaction.on_commit(
                        lambda: ChatService._notify_safe(
                            "request_accepted",
                            conversation=conversation,
                            accepter_name=accepter_name,
                            requester_user=requester,
                        )
                    )

        logger.info(
            "chat.request.accepted",
            conversation_id=str(conversation_id),
            user_id=str(user.id),
        )

        AuditService.log(
            action=AuditLog.Action.CHAT_REQUEST_ACCEPTED,
            actor=user,
            resource=conversation,
            details={
                "conversation_id": str(conversation_id),
                "requester_type": conversation.created_by_type if conversation else None,
                "requester_id": str(conversation.created_by_id) if conversation else None,
            },
        )

    @staticmethod
    @transaction.atomic
    def ignore_request(*, conversation_id: UUID, user) -> None:
        """Ignore a pending chat request."""
        participant = ConversationParticipant.objects.filter(
            conversation_id=conversation_id,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            request_status=RequestStatus.PENDING,
            is_active=True,
        ).first()

        if not participant:
            raise NotFound(
                message="No pending chat request found",
                resource="ChatRequest",
            )

        participant.request_status = RequestStatus.IGNORED
        participant.save(update_fields=["request_status", "updated_at"])

        logger.info(
            "chat.request.ignored",
            conversation_id=str(conversation_id),
            user_id=str(user.id),
        )

    # =========================================================================
    # PARTICIPANTS
    # =========================================================================

    @staticmethod
    @transaction.atomic
    def add_participant(
        *,
        conversation_id: UUID,
        participant_type: str,
        participant_id: UUID,
        added_by,
        request=None,
    ) -> ConversationParticipant:
        """Add a participant to a group conversation."""
        conversation = ChatSelector.get_conversation_by_id(
            conversation_id=conversation_id
        )

        if conversation.conversation_type != ConversationType.GROUP:
            raise BusinessRuleViolation(
                message="Cannot add participants to a direct message",
                rule="dm_no_add_participant",
            )

        if not ChatPolicy.can_manage_group(user=added_by, conversation=conversation):
            raise PermissionDenied(
                message="Only group admins can add participants",
                action="add_participant",
                resource="Conversation",
            )

        # Check group size limit
        active_count = ConversationParticipant.objects.filter(
            conversation=conversation, is_active=True
        ).count()
        if active_count >= CHAT_GROUP_MAX_PARTICIPANTS:
            raise BusinessRuleViolation(
                message=f"Group cannot exceed {CHAT_GROUP_MAX_PARTICIPANTS} participants",
                rule="group_max_participants",
            )

        # Check for existing active participant
        existing = ConversationParticipant.objects.filter(
            conversation=conversation,
            participant_type=participant_type,
            participant_id=participant_id,
            is_active=True,
        ).first()
        if existing:
            raise ConflictError(
                message="Participant is already in this conversation",
                resource="ConversationParticipant",
                conflict_type="duplicate",
            )

        # Check for previously inactive participant (rejoin)
        inactive = ConversationParticipant.objects.filter(
            conversation=conversation,
            participant_type=participant_type,
            participant_id=participant_id,
            is_active=False,
        ).first()
        if inactive:
            inactive.is_active = True
            inactive.left_at = None
            inactive.removed_at = None
            inactive.removed_by = None
            inactive.role = ParticipantRole.MEMBER
            inactive.added_by = added_by
            inactive.save(
                update_fields=[
                    "is_active",
                    "left_at",
                    "removed_at",
                    "removed_by",
                    "role",
                    "added_by",
                    "updated_at",
                ]
            )
            participant = inactive
        else:
            participant = ConversationParticipant.objects.create(
                conversation=conversation,
                participant_type=participant_type,
                participant_id=participant_id,
                role=ParticipantRole.MEMBER,
                added_by=added_by,
            )

        # Send system message
        ChatService._send_system_message(
            conversation=conversation,
            content=f"{participant_type}:{participant_id} was added to the group",
        )

        # Notify added participant (user-type only)
        if participant_type == ParticipantType.USER:
            from apps.users.models import User

            added_user = User.objects.filter(id=participant_id).first()
            if added_user:
                added_by_name = added_by.username or str(added_by.id)
                transaction.on_commit(
                    lambda: ChatService._notify_safe(
                        "group_added",
                        conversation=conversation,
                        added_user=added_user,
                        added_by_name=added_by_name,
                    )
                )

        logger.info(
            "chat.participant.added",
            conversation_id=str(conversation_id),
            participant=f"{participant_type}:{participant_id}",
            added_by=str(added_by.id),
        )

        AuditService.log(
            action=AuditLog.Action.CHAT_PARTICIPANT_ADDED,
            actor=added_by,
            resource=participant,
            request=request,
            details={
                "conversation_id": str(conversation_id),
                "participant_type": participant_type,
                "participant_id": str(participant_id),
                "added_by": str(added_by.id),
            },
        )

        return participant

    @staticmethod
    @transaction.atomic
    def remove_participant(
        *,
        conversation_id: UUID,
        participant_type: str,
        participant_id: UUID,
        removed_by,
        request=None,
    ) -> None:
        """Remove a participant from a group conversation."""
        conversation = ChatSelector.get_conversation_by_id(
            conversation_id=conversation_id
        )

        if conversation.conversation_type != ConversationType.GROUP:
            raise BusinessRuleViolation(
                message="Cannot remove participants from a direct message",
                rule="dm_no_remove_participant",
            )

        if not ChatPolicy.can_manage_group(user=removed_by, conversation=conversation):
            raise PermissionDenied(
                message="Only group admins can remove participants",
                action="remove_participant",
                resource="Conversation",
            )

        participant = ConversationParticipant.objects.filter(
            conversation=conversation,
            participant_type=participant_type,
            participant_id=participant_id,
            is_active=True,
        ).first()

        if not participant:
            raise NotFound(resource="ConversationParticipant")

        participant.is_active = False
        participant.removed_at = timezone.now()
        participant.removed_by = removed_by
        participant.save(
            update_fields=["is_active", "removed_at", "removed_by", "updated_at"]
        )

        ChatService._send_system_message(
            conversation=conversation,
            content=f"{participant_type}:{participant_id} was removed from the group",
        )

        logger.info(
            "chat.participant.removed",
            conversation_id=str(conversation_id),
            participant=f"{participant_type}:{participant_id}",
            removed_by=str(removed_by.id),
        )

        AuditService.log(
            action=AuditLog.Action.CHAT_PARTICIPANT_REMOVED,
            actor=removed_by,
            resource=participant,
            request=request,
            details={
                "conversation_id": str(conversation_id),
                "participant_type": participant_type,
                "participant_id": str(participant_id),
                "removed_by": str(removed_by.id),
            },
        )

    @staticmethod
    @transaction.atomic
    def leave_conversation(*, conversation_id: UUID, user) -> None:
        """Leave a group conversation."""
        conversation = ChatSelector.get_conversation_by_id(
            conversation_id=conversation_id
        )

        if conversation.conversation_type != ConversationType.GROUP:
            raise BusinessRuleViolation(
                message="Cannot leave a direct message. Block the user instead.",
                rule="dm_no_leave",
            )

        participant = ConversationParticipant.objects.filter(
            conversation=conversation,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
            is_active=True,
        ).first()

        if not participant:
            raise NotFound(resource="ConversationParticipant")

        participant.is_active = False
        participant.left_at = timezone.now()
        participant.save(update_fields=["is_active", "left_at", "updated_at"])

        # Check if conversation has remaining active participants
        remaining = ConversationParticipant.objects.filter(
            conversation=conversation, is_active=True
        )

        if not remaining.exists():
            # No participants left — deactivate conversation
            conversation.is_active = False
            conversation.save(update_fields=["is_active", "updated_at"])
        else:
            # Admin succession: if last admin left, promote oldest member
            has_admin = remaining.filter(role=ParticipantRole.ADMIN).exists()
            if not has_admin:
                oldest = remaining.order_by("created_at").first()
                if oldest:
                    oldest.role = ParticipantRole.ADMIN
                    oldest.save(update_fields=["role", "updated_at"])

                    ChatService._send_system_message(
                        conversation=conversation,
                        content=f"{oldest.participant_type}:{oldest.participant_id} was promoted to admin",
                    )

        ChatService._send_system_message(
            conversation=conversation,
            content=f"user:{user.id} left the group",
        )

        logger.info(
            "chat.participant.left",
            conversation_id=str(conversation_id),
            user_id=str(user.id),
        )

    # =========================================================================
    # BLOCKS
    # =========================================================================

    @staticmethod
    @transaction.atomic
    def block_participant(
        *,
        blocker,
        blocked_type: str,
        blocked_id: UUID,
        request=None,
    ) -> ChatBlock:
        """Block a participant from sending DMs."""
        # Check not blocking self
        if blocked_type == ParticipantType.USER and blocked_id == blocker.id:
            raise ValidationError(
                message="Cannot block yourself",
                field="blocked_id",
            )

        # Check not already blocked
        existing = ChatBlock.objects.filter(
            blocker=blocker,
            blocked_type=blocked_type,
            blocked_id=blocked_id,
        ).first()
        if existing:
            return existing  # Idempotent

        block = ChatBlock.objects.create(
            blocker=blocker,
            blocked_type=blocked_type,
            blocked_id=blocked_id,
        )

        logger.info(
            "chat.block.created",
            blocker_id=str(blocker.id),
            blocked=f"{blocked_type}:{blocked_id}",
        )

        AuditService.log(
            action=AuditLog.Action.CHAT_BLOCK_CREATED,
            actor=blocker,
            resource=block,
            request=request,
            details={
                "blocker_id": str(blocker.id),
                "blocked_type": blocked_type,
                "blocked_id": str(blocked_id),
            },
        )

        return block

    @staticmethod
    @transaction.atomic
    def unblock_participant(
        *,
        blocker,
        block_id: UUID,
        request=None,
    ) -> None:
        """Unblock a participant."""
        block = ChatBlock.objects.filter(
            id=block_id,
            blocker=blocker,
        ).first()
        if not block:
            raise NotFound(resource="ChatBlock", resource_id=str(block_id))

        blocked_info = f"{block.blocked_type}:{block.blocked_id}"
        block.delete()

        logger.info(
            "chat.block.removed",
            blocker_id=str(blocker.id),
            blocked=blocked_info,
        )

        AuditService.log(
            action=AuditLog.Action.CHAT_BLOCK_REMOVED,
            actor=blocker,
            resource_type="ChatBlock",
            resource_id=str(block_id),
            request=request,
            details={
                "blocker_id": str(blocker.id),
                "blocked": blocked_info,
            },
        )

    # =========================================================================
    # GROUP MANAGEMENT
    # =========================================================================

    @staticmethod
    @transaction.atomic
    def promote_to_admin(
        *, conversation_id: UUID, participant_id: UUID, user
    ) -> None:
        """Promote a participant to group admin."""
        conversation = ChatSelector.get_conversation_by_id(
            conversation_id=conversation_id
        )

        if not ChatPolicy.can_manage_group(user=user, conversation=conversation):
            raise PermissionDenied(
                message="Only group admins can promote participants",
                action="promote_to_admin",
                resource="Conversation",
            )

        participant = ConversationParticipant.objects.filter(
            conversation=conversation,
            participant_id=participant_id,
            is_active=True,
        ).first()
        if not participant:
            raise NotFound(resource="ConversationParticipant")

        if participant.role == ParticipantRole.ADMIN:
            return  # Idempotent

        participant.role = ParticipantRole.ADMIN
        participant.save(update_fields=["role", "updated_at"])

        ChatService._send_system_message(
            conversation=conversation,
            content=f"{participant.participant_type}:{participant.participant_id} was promoted to admin",
        )

    @staticmethod
    @transaction.atomic
    def demote_from_admin(
        *, conversation_id: UUID, participant_id: UUID, user
    ) -> None:
        """Demote a participant from group admin to member."""
        conversation = ChatSelector.get_conversation_by_id(
            conversation_id=conversation_id
        )

        if not ChatPolicy.can_manage_group(user=user, conversation=conversation):
            raise PermissionDenied(
                message="Only group admins can demote participants",
                action="demote_from_admin",
                resource="Conversation",
            )

        participant = ConversationParticipant.objects.filter(
            conversation=conversation,
            participant_id=participant_id,
            is_active=True,
        ).first()
        if not participant:
            raise NotFound(resource="ConversationParticipant")

        if participant.role == ParticipantRole.MEMBER:
            return  # Idempotent

        # Cannot demote self if last admin
        admin_count = ConversationParticipant.objects.filter(
            conversation=conversation,
            role=ParticipantRole.ADMIN,
            is_active=True,
        ).count()
        if admin_count <= 1:
            raise BusinessRuleViolation(
                message="Cannot demote the last admin. Promote another member first.",
                rule="last_admin",
            )

        participant.role = ParticipantRole.MEMBER
        participant.save(update_fields=["role", "updated_at"])

    # =========================================================================
    # ATTACHMENTS
    # =========================================================================

    @staticmethod
    @transaction.atomic
    def upload_attachment(
        *,
        conversation_id: UUID,
        user,
        file,
    ) -> MessageAttachment:
        """
        Upload an image file for later attachment to a message.

        Validates MIME type, extension, file size. Stores to default_storage,
        creates an orphan MessageAttachment (message=None).
        """
        import os
        import uuid as uuid_mod

        from django.core.files.storage import default_storage

        # Verify participant
        if not ChatSelector.is_participant(
            conversation_id=conversation_id,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        ):
            raise PermissionDenied(
                message="You are not a participant in this conversation",
                action="upload_attachment",
                resource="Conversation",
            )

        # Validate extension
        original_filename = file.name or "unknown"
        ext = os.path.splitext(original_filename)[1].lstrip(".").lower()
        if ext not in CHAT_ALLOWED_IMAGE_EXTENSIONS:
            raise ValidationError(
                message=f"File extension '{ext}' is not allowed. Allowed: {', '.join(sorted(CHAT_ALLOWED_IMAGE_EXTENSIONS))}",
                field="file",
            )

        # Validate MIME type
        mime_type = file.content_type or ""
        if mime_type not in CHAT_ALLOWED_IMAGE_TYPES:
            raise ValidationError(
                message=f"MIME type '{mime_type}' is not allowed. Allowed: {', '.join(sorted(CHAT_ALLOWED_IMAGE_TYPES))}",
                field="file",
            )

        # Validate file size
        if file.size > CHAT_MAX_IMAGE_SIZE:
            raise ValidationError(
                message=f"File size exceeds maximum of {CHAT_MAX_IMAGE_SIZE // (1024 * 1024)} MB",
                field="file",
            )

        # Generate storage key
        storage_key = f"chat/{conversation_id}/attachments/{uuid_mod.uuid4().hex}.{ext}"

        # Save to storage
        default_storage.save(storage_key, file)

        # Extract image dimensions (best-effort)
        width = None
        height = None
        try:
            from PIL import Image

            file.seek(0)
            img = Image.open(file)
            width, height = img.size
        except Exception:
            pass

        attachment = MessageAttachment.objects.create(
            message=None,
            conversation_id=conversation_id,
            uploaded_by=user,
            file_type=AttachmentType.IMAGE,
            storage_key=storage_key,
            original_filename=original_filename,
            mime_type=mime_type,
            file_size=file.size,
            width=width,
            height=height,
        )

        logger.info(
            "chat.attachment.uploaded",
            attachment_id=str(attachment.id),
            conversation_id=str(conversation_id),
            user_id=str(user.id),
            file_size=file.size,
            mime_type=mime_type,
        )

        return attachment

    @staticmethod
    def _link_attachments_to_message(
        *,
        message: Message,
        attachment_ids: list[UUID],
        conversation_id: UUID,
        uploaded_by_id: UUID,
    ) -> None:
        """
        Link orphan attachments to a message. Called inside send_message's transaction.

        Validates: all IDs exist, all belong to same conversation, all uploaded
        by same user, all are orphans (message=None), count <= max.
        """
        if len(attachment_ids) > CHAT_MAX_ATTACHMENTS_PER_MESSAGE:
            raise ValidationError(
                message=f"Cannot attach more than {CHAT_MAX_ATTACHMENTS_PER_MESSAGE} files per message",
                field="attachment_ids",
            )

        attachments = MessageAttachment.objects.filter(id__in=attachment_ids)
        if attachments.count() != len(attachment_ids):
            raise ValidationError(
                message="One or more attachment IDs are invalid",
                field="attachment_ids",
            )

        for att in attachments:
            if att.conversation_id != conversation_id:
                raise ValidationError(
                    message="Attachment does not belong to this conversation",
                    field="attachment_ids",
                )
            if att.uploaded_by_id != uploaded_by_id:
                raise ValidationError(
                    message="Attachment was not uploaded by you",
                    field="attachment_ids",
                )
            if att.message_id is not None:
                raise ValidationError(
                    message="Attachment is already linked to a message",
                    field="attachment_ids",
                )

        attachments.update(message=message)

    # =========================================================================
    # REACTIONS
    # =========================================================================

    @staticmethod
    @transaction.atomic
    def add_reaction(
        *,
        message_id: UUID,
        user,
        reaction: str,
    ) -> MessageReaction:
        """
        Add a preset emoji reaction to a message.

        Validates reaction type, verifies user is a participant.
        Broadcasts and optionally notifies on commit.
        """
        from django.db import IntegrityError

        if reaction not in ReactionType.values:
            raise ValidationError(
                message=f"Invalid reaction type: {reaction}",
                field="reaction",
            )

        message = ChatSelector.get_message_by_id(message_id=message_id)

        if message.status == MessageStatus.DELETED:
            raise NotFound(resource="Message", resource_id=str(message_id))

        # Verify user is participant
        if not ChatSelector.is_participant(
            conversation_id=message.conversation_id,
            participant_type=ParticipantType.USER,
            participant_id=user.id,
        ):
            raise PermissionDenied(
                message="You are not a participant in this conversation",
                action="add_reaction",
                resource="Conversation",
            )

        try:
            reaction_obj = MessageReaction.objects.create(
                message=message,
                user=user,
                reaction=reaction,
            )
        except IntegrityError:
            raise ConflictError(
                message="You have already added this reaction",
                resource="MessageReaction",
                conflict_type="duplicate",
            )

        conversation = message.conversation

        # Broadcast reaction update on commit
        transaction.on_commit(
            lambda: ChatService._broadcast_reaction_safe(
                conversation.id, message_id, user.id, reaction, "add"
            )
        )

        # Notify message author on commit (if different user)
        if (
            message.sender_type == ParticipantType.USER
            and message.sender_id != user.id
        ):
            transaction.on_commit(
                lambda: ChatService._notify_safe(
                    "reaction_received",
                    message=message,
                    conversation=conversation,
                    reactor_user=user,
                )
            )

        logger.info(
            "chat.reaction.added",
            message_id=str(message_id),
            user_id=str(user.id),
            reaction=reaction,
        )

        return reaction_obj

    @staticmethod
    @transaction.atomic
    def remove_reaction(
        *,
        message_id: UUID,
        user,
        reaction: str,
    ) -> None:
        """Remove a reaction from a message."""
        reaction_obj = MessageReaction.objects.filter(
            message_id=message_id,
            user=user,
            reaction=reaction,
        ).first()

        if not reaction_obj:
            raise NotFound(resource="MessageReaction")

        message = reaction_obj.message
        conversation_id = message.conversation_id
        reaction_obj.delete()

        # Broadcast reaction update on commit
        transaction.on_commit(
            lambda: ChatService._broadcast_reaction_safe(
                conversation_id, message_id, user.id, reaction, "remove"
            )
        )

        logger.info(
            "chat.reaction.removed",
            message_id=str(message_id),
            user_id=str(user.id),
            reaction=reaction,
        )

    @staticmethod
    def _broadcast_reaction_safe(
        conversation_id, message_id, user_id, reaction, action
    ) -> None:
        """Broadcast reaction update (best-effort, never raises)."""
        try:
            from apps.chat.broadcast import broadcast_reaction_update

            broadcast_reaction_update(
                conversation_id, message_id, user_id, reaction, action
            )
        except Exception as exc:
            logger.warning(
                "chat.reaction.broadcast_failed",
                error=str(exc),
            )

    # =========================================================================
    # INTERNAL HELPERS
    # =========================================================================

    @staticmethod
    def _check_block_status(
        sender_type: str,
        sender_id: UUID,
        recipient_type: str,
        recipient_id: UUID,
    ) -> None:
        """Check if either participant has blocked the other."""
        # Check if sender blocked recipient
        if sender_type == ParticipantType.USER:
            if ChatSelector.is_blocked(
                blocker_id=sender_id,
                blocked_type=recipient_type,
                blocked_id=recipient_id,
            ):
                raise BusinessRuleViolation(
                    message="You have blocked this participant",
                    rule="blocked_by_sender",
                )

        # Check if recipient blocked sender
        if recipient_type == ParticipantType.USER:
            if ChatSelector.is_blocked(
                blocker_id=recipient_id,
                blocked_type=sender_type,
                blocked_id=sender_id,
            ):
                raise PermissionDenied(
                    message="Cannot send message to this participant",
                    action="send_message",
                    resource="Conversation",
                )

    @staticmethod
    def _determine_request_status(
        sender_type: str,
        sender_id: UUID,
        recipient_type: str,
        recipient_id: UUID,
        scope_type: str,
    ) -> str:
        """
        Determine the request status for a new DM recipient.

        Connected users skip the request flow (auto-accept).
        Entity-to-entity and entity-to-user skip the request flow.
        """
        # Non-global scope: no requests (org members are trusted)
        if scope_type != ScopeType.GLOBAL:
            return RequestStatus.NONE

        # Entity participants: no request needed
        if sender_type != ParticipantType.USER or recipient_type != ParticipantType.USER:
            return RequestStatus.NONE

        # Check if users are connected
        from apps.network.selectors import ConnectionSelector

        if ConnectionSelector.is_connected(user_a_id=sender_id, user_b_id=recipient_id):
            return RequestStatus.NONE

        # Strangers: requires request approval
        return RequestStatus.PENDING

    @staticmethod
    def _check_dm_request_limit(
        conversation: Conversation,
        sender_type: str,
        sender_id: UUID,
    ) -> None:
        """Check if a sender in a DM with pending request has exceeded the message limit."""
        # Find the recipient's participant record
        recipient = ConversationParticipant.objects.filter(
            conversation=conversation,
            request_status=RequestStatus.PENDING,
            is_active=True,
        ).exclude(
            participant_type=sender_type,
            participant_id=sender_id,
        ).first()

        if not recipient:
            return  # No pending request, send freely

        # Count messages from sender
        msg_count = Message.objects.filter(
            conversation=conversation,
            sender_type=sender_type,
            sender_id=sender_id,
        ).count()

        if msg_count >= CHAT_REQUEST_MAX_MESSAGES:
            raise BusinessRuleViolation(
                message=f"Cannot send more than {CHAT_REQUEST_MAX_MESSAGES} messages before the request is accepted",
                rule="request_message_limit",
            )

    @staticmethod
    def _get_next_sequence_number(conversation_id: UUID) -> int:
        """Get the next sequence number for a conversation."""
        last = (
            Message.objects.filter(conversation_id=conversation_id)
            .aggregate(max_seq=models.Max("sequence_number"))
        )
        return (last["max_seq"] or 0) + 1

    @staticmethod
    def _update_conversation_last_message(
        conversation: Conversation, message: Message
    ) -> None:
        """Update denormalized last message fields on conversation."""
        conversation.last_message_id = message.id
        conversation.last_message_at = message.created_at
        conversation.last_message_preview = message.content[:CHAT_MESSAGE_PREVIEW_LENGTH]
        conversation.last_message_sender_type = message.sender_type
        conversation.last_message_sender_id = message.sender_id
        conversation.save(
            update_fields=[
                "last_message_id",
                "last_message_at",
                "last_message_preview",
                "last_message_sender_type",
                "last_message_sender_id",
                "updated_at",
            ]
        )

    @staticmethod
    def _send_system_message(*, conversation: Conversation, content: str) -> Message:
        """Send a system message to a conversation."""
        seq = ChatService._get_next_sequence_number(conversation.id)
        message = Message.objects.create(
            conversation=conversation,
            sender_type=ParticipantType.USER,
            sender_id=conversation.created_by_id,
            content_type=MessageContentType.SYSTEM,
            content=content,
            sequence_number=seq,
        )
        ChatService._update_conversation_last_message(conversation, message)
        return message

    # =========================================================================
    # NOTIFICATIONS (best-effort, never fail)
    # =========================================================================

    @staticmethod
    def _notify_safe(event_type: str, **kwargs) -> None:
        """
        Fire a chat notification (best-effort).
        Never raises — logs and swallows all exceptions.
        """
        try:
            from apps.notifications.services import NotificationService
        except ImportError:
            return
        try:
            handler = getattr(ChatService, f"_notify_{event_type}", None)
            if handler:
                handler(NotificationService, **kwargs)
        except Exception as exc:
            logger.warning(
                "chat.notification.failed",
                event_type=event_type,
                error=str(exc),
            )

    @staticmethod
    def _is_rate_limited(user_id, conversation_id) -> bool:
        """
        Check if chat notification is rate-limited (1 per conversation per 5 min).
        Fail-open: send notification if Redis is unavailable.
        """
        try:
            from apps.chat.presence import PresenceManager

            redis_client = PresenceManager._get_redis()
            if not redis_client or redis_client == "unavailable":
                return False
            key = f"chat:notif_ratelimit:{user_id}:{conversation_id}"
            if redis_client.exists(key):
                return True
            redis_client.setex(key, 300, "1")
            return False
        except Exception:
            return False

    @staticmethod
    def _notify_new_message(NS, *, message, conversation) -> None:
        """Notify offline participants about a new message."""
        from apps.chat.presence import PresenceManager
        from apps.users.models import User

        participants = ConversationParticipant.objects.filter(
            conversation=conversation,
            participant_type=ParticipantType.USER,
            is_active=True,
        ).exclude(participant_id=message.sender_id)

        for p in participants:
            if PresenceManager.is_online(p.participant_id):
                continue
            if ChatService._is_rate_limited(p.participant_id, conversation.id):
                continue

            user = User.objects.filter(id=p.participant_id).first()
            if not user:
                continue

            NS.send(
                user=user,
                notification_type="chat_message_received",
                context={
                    "conversation_id": str(conversation.id),
                    "sender_name": f"{message.sender_type}:{message.sender_id}",
                    "preview": message.content[:100],
                },
            )

    @staticmethod
    def _notify_request_received(
        NS, *, conversation, requester_name, recipient_user
    ) -> None:
        """Notify a user that they received a chat request."""
        NS.send(
            user=recipient_user,
            notification_type="chat_request_received",
            context={
                "conversation_id": str(conversation.id),
                "requester_name": requester_name,
                "preview": "",
            },
        )

    @staticmethod
    def _notify_request_accepted(
        NS, *, conversation, accepter_name, requester_user
    ) -> None:
        """Notify the requester that their chat request was accepted."""
        NS.send(
            user=requester_user,
            notification_type="chat_request_accepted",
            context={
                "conversation_id": str(conversation.id),
                "accepter_name": accepter_name,
            },
        )

    @staticmethod
    def _notify_group_added(NS, *, conversation, added_user, added_by_name) -> None:
        """Notify a user that they were added to a group conversation."""
        NS.send(
            user=added_user,
            notification_type="chat_group_added",
            context={
                "conversation_id": str(conversation.id),
                "group_name": conversation.name or "Group",
                "added_by_name": added_by_name,
            },
        )

    @staticmethod
    def _notify_reaction_received(NS, *, message, conversation, reactor_user) -> None:
        """Notify message author when someone reacts to their message."""
        if message.sender_type != ParticipantType.USER:
            return
        if message.sender_id == reactor_user.id:
            return

        from apps.users.models import User

        author = User.objects.filter(id=message.sender_id).first()
        if not author:
            return

        NS.send(
            user=author,
            notification_type="chat_reaction_received",
            context={
                "conversation_id": str(conversation.id),
                "reactor_name": reactor_user.username or str(reactor_user.id),
                "message_preview": message.content[:100],
            },
        )
