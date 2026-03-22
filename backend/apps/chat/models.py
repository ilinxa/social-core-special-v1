"""
Chat Models
===========
Conversation, ConversationParticipant, Message, ChatBlock,
MessageAttachment, MessageReaction.

All use UUIDModel + TimeStampedModel (no soft delete — status fields
manage lifecycle, consistent with the network system pattern).
"""

from django.conf import settings
from django.db import models

from apps.chat.constants import (
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
from apps.core.models import TimeStampedModel, UUIDModel

# =============================================================================
# CONVERSATION
# =============================================================================


class Conversation(UUIDModel, TimeStampedModel):
    """
    A DM or group chat, scoped to exactly one isolation boundary.

    Scope isolation is immutable after creation — a conversation can never
    change scope. Every query in the system filters by scope_type + scope_id.
    """

    # Scope isolation (immutable after creation)
    scope_type = models.CharField(
        max_length=20,
        choices=ScopeType.choices,
        db_index=True,
    )
    scope_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Null for global scope, UUID for org scope",
    )

    # Conversation metadata
    conversation_type = models.CharField(
        max_length=20,
        choices=ConversationType.choices,
    )
    name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Group name (empty for DMs)",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Group description (empty for DMs)",
    )

    # Creator tracking
    created_by_type = models.CharField(
        max_length=20,
        choices=ParticipantType.choices,
    )
    created_by_id = models.UUIDField()

    # Denormalized last message (avoids N+1 on conversation list)
    last_message_id = models.UUIDField(null=True, blank=True)
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_message_preview = models.CharField(max_length=200, blank=True, default="")
    last_message_sender_type = models.CharField(max_length=20, blank=True, default="")
    last_message_sender_id = models.UUIDField(null=True, blank=True)

    # Active state
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "chat_conversation"
        ordering = ["-last_message_at", "-created_at"]
        indexes = [
            models.Index(
                fields=["scope_type", "scope_id", "is_active"],
                name="chat_conv_scope_active_idx",
            ),
            models.Index(
                fields=["scope_type", "scope_id", "last_message_at"],
                name="chat_conv_scope_lastmsg_idx",
            ),
            models.Index(
                fields=["conversation_type", "scope_type", "scope_id"],
                name="chat_conv_type_scope_idx",
            ),
        ]

    def __str__(self):
        scope = f"{self.scope_type}:{self.scope_id}" if self.scope_id else "global"
        return f"Conversation({self.conversation_type}, {scope})"


# =============================================================================
# CONVERSATION PARTICIPANT
# =============================================================================


class ConversationParticipant(UUIDModel, TimeStampedModel):
    """
    Links a participant (user or entity) to a conversation.

    Stores per-participant state: watermarks, request status, mute, role.
    """

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="participants",
    )

    # Polymorphic participant identity
    participant_type = models.CharField(
        max_length=20,
        choices=ParticipantType.choices,
    )
    participant_id = models.UUIDField()

    # Group chat role (ignored for DMs)
    role = models.CharField(
        max_length=20,
        choices=ParticipantRole.choices,
        default=ParticipantRole.MEMBER,
    )

    # Chat request state (DMs in global scope only)
    request_status = models.CharField(
        max_length=20,
        choices=RequestStatus.choices,
        default=RequestStatus.NONE,
    )

    # Delivery watermarks
    last_delivered_message_id = models.UUIDField(null=True, blank=True)
    last_seen_message_id = models.UUIDField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    # Notification control
    is_muted = models.BooleanField(default=False)

    # Participation lifecycle
    is_active = models.BooleanField(default=True, db_index=True)
    left_at = models.DateTimeField(null=True, blank=True)
    removed_at = models.DateTimeField(null=True, blank=True)
    removed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="removed_chat_participants",
    )

    # Entity delegation (who added this participant — for audit)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="added_chat_participants",
    )

    class Meta:
        db_table = "chat_conversation_participant"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "participant_type", "participant_id"],
                condition=models.Q(is_active=True),
                name="unique_active_participant",
            ),
        ]
        indexes = [
            models.Index(
                fields=["participant_type", "participant_id", "is_active"],
                name="chat_part_type_id_active_idx",
            ),
            models.Index(
                fields=["conversation", "is_active"],
                name="chat_part_conv_active_idx",
            ),
            models.Index(
                fields=["participant_type", "participant_id", "request_status"],
                name="chat_part_request_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.participant_type}:{self.participant_id} "
            f"in {self.conversation_id} ({self.role})"
        )


# =============================================================================
# MESSAGE
# =============================================================================


class Message(UUIDModel, TimeStampedModel):
    """
    A single message in a conversation.

    Immutable except for edit/delete (status field manages lifecycle).
    """

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    # Sender identity (polymorphic — user or entity)
    sender_type = models.CharField(
        max_length=20,
        choices=ParticipantType.choices,
    )
    sender_id = models.UUIDField()

    # Entity delegation audit — the human behind an entity message
    acting_user_id = models.UUIDField(null=True, blank=True)

    # Content
    content_type = models.CharField(
        max_length=20,
        choices=MessageContentType.choices,
        default=MessageContentType.TEXT,
    )
    content = models.TextField()
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="For rich content types (url preview, file info, etc.)",
    )

    # Ordering (gap-free within conversation)
    sequence_number = models.PositiveIntegerField(db_index=True)

    # Edit/delete lifecycle
    status = models.CharField(
        max_length=20,
        choices=MessageStatus.choices,
        default=MessageStatus.ACTIVE,
    )
    edited_at = models.DateTimeField(null=True, blank=True)
    original_content = models.TextField(
        blank=True,
        default="",
        help_text="Preserved on edit/delete for moderation audit",
    )

    class Meta:
        db_table = "chat_message"
        ordering = ["sequence_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "sequence_number"],
                name="unique_message_sequence",
            ),
        ]
        indexes = [
            models.Index(
                fields=["conversation", "created_at"],
                name="chat_msg_conv_created_idx",
            ),
            models.Index(
                fields=["conversation", "sequence_number"],
                name="chat_msg_conv_seq_idx",
            ),
            models.Index(
                fields=["sender_type", "sender_id"],
                name="chat_msg_sender_idx",
            ),
        ]

    def __str__(self):
        preview = self.content[:50] if self.content else ""
        return f"Message #{self.sequence_number} in {self.conversation_id}: {preview}"


# =============================================================================
# CHAT BLOCK
# =============================================================================


class ChatBlock(UUIDModel, TimeStampedModel):
    """
    Per-user block list. Global scope only.

    Prevents blocked participant from sending DMs to the blocker.
    """

    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_blocks",
    )
    blocked_type = models.CharField(
        max_length=20,
        choices=ParticipantType.choices,
    )
    blocked_id = models.UUIDField()

    class Meta:
        db_table = "chat_block"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["blocker", "blocked_type", "blocked_id"],
                name="unique_chat_block",
            ),
        ]
        indexes = [
            models.Index(
                fields=["blocker", "blocked_type", "blocked_id"],
                name="chat_block_blocker_idx",
            ),
            models.Index(
                fields=["blocked_type", "blocked_id"],
                name="chat_block_blocked_idx",
            ),
        ]

    def __str__(self):
        return f"{self.blocker_id} blocked {self.blocked_type}:{self.blocked_id}"


# =============================================================================
# MESSAGE ATTACHMENT
# =============================================================================


class MessageAttachment(UUIDModel, TimeStampedModel):
    """
    An image file attached to a chat message.

    Lifecycle: created with message=None (orphan on upload),
    linked to message on send, cleaned up if never linked (24h TTL).
    """

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="attachments",
        null=True,
        blank=True,
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_attachments",
    )

    # File metadata
    file_type = models.CharField(
        max_length=20,
        choices=AttachmentType.choices,
    )
    storage_key = models.CharField(max_length=500)
    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    file_size = models.PositiveIntegerField()

    # Image dimensions (best-effort via Pillow)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = "chat_message_attachment"
        ordering = ["created_at"]
        indexes = [
            models.Index(
                fields=["message"],
                name="chat_attach_msg_idx",
            ),
            models.Index(
                fields=["conversation"],
                name="chat_attach_conv_idx",
            ),
            models.Index(
                fields=["message"],
                condition=models.Q(message__isnull=True),
                name="chat_attach_orphan_idx",
            ),
        ]

    def __str__(self):
        linked = f"msg:{self.message_id}" if self.message_id else "orphan"
        return f"Attachment({self.original_filename}, {linked})"


# =============================================================================
# MESSAGE REACTION
# =============================================================================


class MessageReaction(UUIDModel, TimeStampedModel):
    """
    An emoji reaction on a message. Preset types only.

    Only real users can react (no entity reactions).
    """

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="reactions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_reactions",
    )
    reaction = models.CharField(
        max_length=20,
        choices=ReactionType.choices,
    )

    class Meta:
        db_table = "chat_message_reaction"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["message", "user", "reaction"],
                name="unique_message_user_reaction",
            ),
        ]
        indexes = [
            models.Index(
                fields=["message"],
                name="chat_reaction_msg_idx",
            ),
        ]

    def __str__(self):
        return f"{self.user_id} reacted {self.reaction} on {self.message_id}"
