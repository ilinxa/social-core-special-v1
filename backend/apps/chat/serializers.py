"""
Chat Serializers
================
Input and output serializers for the chat system.
"""

from rest_framework import serializers

from apps.chat.constants import (
    CHAT_MAX_ATTACHMENTS_PER_MESSAGE,
    ConversationType,
    MessageContentType,
    ParticipantType,
    ReactionType,
    ScopeType,
)

# =============================================================================
# INPUT SERIALIZERS
# =============================================================================


class ParticipantIdSerializer(serializers.Serializer):
    participant_type = serializers.ChoiceField(choices=ParticipantType.choices)
    participant_id = serializers.UUIDField()


class ConversationCreateInputSerializer(serializers.Serializer):
    scope_type = serializers.ChoiceField(choices=ScopeType.choices)
    scope_id = serializers.UUIDField(required=False, allow_null=True)
    conversation_type = serializers.ChoiceField(choices=ConversationType.choices)
    participant_ids = ParticipantIdSerializer(many=True)
    name = serializers.CharField(max_length=255, required=False, default="")


class ConversationUpdateInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False)


class MessageCreateInputSerializer(serializers.Serializer):
    content = serializers.CharField(
        max_length=5000, required=False, default="", allow_blank=True
    )
    content_type = serializers.ChoiceField(
        choices=MessageContentType.choices,
        required=False,
        default=MessageContentType.TEXT,
    )
    sender_type = serializers.ChoiceField(
        choices=ParticipantType.choices,
        required=False,
    )
    sender_id = serializers.UUIDField(required=False)
    attachment_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
        max_length=CHAT_MAX_ATTACHMENTS_PER_MESSAGE,
    )

    def validate(self, data):
        if not data.get("content", "").strip() and not data.get("attachment_ids"):
            raise serializers.ValidationError(
                "Either content or attachment_ids is required."
            )
        return data


class ReactionInputSerializer(serializers.Serializer):
    reaction = serializers.ChoiceField(choices=ReactionType.choices)


class MessageEditInputSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=5000)


class AddParticipantInputSerializer(serializers.Serializer):
    participant_type = serializers.ChoiceField(choices=ParticipantType.choices)
    participant_id = serializers.UUIDField()


class BlockCreateInputSerializer(serializers.Serializer):
    blocked_type = serializers.ChoiceField(choices=ParticipantType.choices)
    blocked_id = serializers.UUIDField()


# =============================================================================
# OUTPUT SERIALIZERS
# =============================================================================


def _resolve_participant_display(participant_type: str, participant_id):
    """
    Resolve display_name and avatar_url for a participant.

    Key model paths (from plan Section 12.1):
    - user: User.profile.display_name, User.profile.avatar
    - business: BusinessProfile.display_name, BusinessProfile.logo
    - platform: PlatformProfile.name, PlatformProfile.logo
    """
    display_name = ""
    avatar_url = None

    try:
        if participant_type == ParticipantType.USER:
            from apps.users.models import User

            user = (
                User.objects.select_related("profile").filter(id=participant_id).first()
            )
            if user and hasattr(user, "profile"):
                display_name = user.profile.display_name or ""
                if user.profile.avatar:
                    avatar_url = user.profile.avatar.url

        elif participant_type == ParticipantType.BUSINESS:
            from apps.organization.business.models import BusinessProfile

            profile = BusinessProfile.objects.filter(business_id=participant_id).first()
            if profile:
                display_name = profile.display_name or ""
                if profile.logo:
                    avatar_url = profile.logo.url

        elif participant_type == ParticipantType.PLATFORM:
            from apps.organization.platform.models import PlatformProfile

            profile = PlatformProfile.objects.filter(platform_id=participant_id).first()
            if profile:
                display_name = profile.name or ""
                if profile.logo:
                    avatar_url = profile.logo.url
    except Exception:
        pass

    return display_name, avatar_url


class ParticipantOutputSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    participant_type = serializers.CharField()
    participant_id = serializers.UUIDField()
    display_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    role = serializers.CharField()
    request_status = serializers.CharField()
    is_muted = serializers.BooleanField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()

    def get_display_name(self, obj):
        name, _ = _resolve_participant_display(obj.participant_type, obj.participant_id)
        return name

    def get_avatar_url(self, obj):
        _, avatar = _resolve_participant_display(
            obj.participant_type, obj.participant_id
        )
        return avatar


class LastMessageSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="last_message_id")
    sender_type = serializers.CharField(source="last_message_sender_type")
    sender_id = serializers.UUIDField(source="last_message_sender_id")
    sender_name = serializers.SerializerMethodField()
    content_preview = serializers.CharField(source="last_message_preview")
    created_at = serializers.DateTimeField(source="last_message_at")

    def get_sender_name(self, obj):
        if not obj.last_message_sender_type or not obj.last_message_sender_id:
            return ""
        name, _ = _resolve_participant_display(
            obj.last_message_sender_type, obj.last_message_sender_id
        )
        return name


class ConversationListOutputSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    scope_type = serializers.CharField()
    scope_id = serializers.UUIDField(allow_null=True)
    conversation_type = serializers.CharField()
    name = serializers.CharField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    is_muted = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()

    def get_last_message(self, obj):
        if not obj.last_message_id:
            return None
        return LastMessageSerializer(obj).data

    def get_unread_count(self, obj):
        request = self.context.get("request")
        if not request or not request.user:
            return 0
        from apps.chat.selectors import ChatSelector

        return ChatSelector.get_unread_count(
            conversation_id=obj.id,
            participant_type=ParticipantType.USER,
            participant_id=request.user.id,
        )

    def get_is_muted(self, obj):
        request = self.context.get("request")
        if not request or not request.user:
            return False
        from apps.chat.models import ConversationParticipant

        participant = (
            ConversationParticipant.objects.filter(
                conversation=obj,
                participant_type=ParticipantType.USER,
                participant_id=request.user.id,
                is_active=True,
            )
            .values_list("is_muted", flat=True)
            .first()
        )
        return participant or False


class ConversationDetailOutputSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    scope_type = serializers.CharField()
    scope_id = serializers.UUIDField(allow_null=True)
    conversation_type = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    participants = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()

    def get_participants(self, obj):
        from apps.chat.models import ConversationParticipant

        participants = ConversationParticipant.objects.filter(
            conversation=obj, is_active=True
        ).order_by("created_at")
        return ParticipantOutputSerializer(
            participants, many=True, context=self.context
        ).data

    def get_last_message(self, obj):
        if not obj.last_message_id:
            return None
        return LastMessageSerializer(obj).data


class AttachmentOutputSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    file_type = serializers.CharField()
    original_filename = serializers.CharField()
    mime_type = serializers.CharField()
    file_size = serializers.IntegerField()
    width = serializers.IntegerField(allow_null=True)
    height = serializers.IntegerField(allow_null=True)
    url = serializers.SerializerMethodField()

    def get_url(self, obj):
        from django.core.files.storage import default_storage

        return default_storage.url(obj.storage_key)


class MessageOutputSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    conversation_id = serializers.UUIDField()
    sender_type = serializers.CharField()
    sender_id = serializers.UUIDField()
    sender_name = serializers.SerializerMethodField()
    sender_avatar_url = serializers.SerializerMethodField()
    content_type = serializers.CharField()
    content = serializers.CharField()
    status = serializers.CharField()
    sequence_number = serializers.IntegerField()
    edited_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()
    attachments = serializers.SerializerMethodField()
    reactions = serializers.SerializerMethodField()
    my_reactions = serializers.SerializerMethodField()

    def get_sender_name(self, obj):
        name, _ = _resolve_participant_display(obj.sender_type, obj.sender_id)
        return name

    def get_sender_avatar_url(self, obj):
        _, avatar = _resolve_participant_display(obj.sender_type, obj.sender_id)
        return avatar

    def get_attachments(self, obj):
        atts = getattr(obj, "_prefetched_attachments", None)
        if atts is None:
            from apps.chat.models import MessageAttachment

            atts = MessageAttachment.objects.filter(message=obj).order_by("created_at")
        return AttachmentOutputSerializer(atts, many=True, context=self.context).data

    def get_reactions(self, obj):
        data = getattr(obj, "_prefetched_reactions", None)
        if data is not None:
            return data.get("counts", {})
        from apps.chat.selectors import ChatSelector

        result = ChatSelector.get_reactions_for_messages(message_ids=[obj.id])
        return result.get(obj.id, {}).get("counts", {})

    def get_my_reactions(self, obj):
        data = getattr(obj, "_prefetched_reactions", None)
        if data is not None:
            return data.get("my_reactions", [])
        request = self.context.get("request")
        uid = (
            request.user.id
            if request and hasattr(request, "user") and request.user
            else None
        )
        if uid:
            from apps.chat.models import MessageReaction

            return list(
                MessageReaction.objects.filter(message=obj, user_id=uid).values_list(
                    "reaction", flat=True
                )
            )
        return []


class ChatRequestOutputSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField(source="conversation.id")
    requester = serializers.SerializerMethodField()
    preview_messages = serializers.SerializerMethodField()
    message_count = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()

    def get_requester(self, obj):
        """Get the sender (other participant) of this DM."""
        from apps.chat.models import ConversationParticipant

        sender = (
            ConversationParticipant.objects.filter(
                conversation=obj.conversation,
                is_active=True,
            )
            .exclude(
                participant_type=obj.participant_type,
                participant_id=obj.participant_id,
            )
            .first()
        )

        if not sender:
            return None

        name, avatar = _resolve_participant_display(
            sender.participant_type, sender.participant_id
        )
        return {
            "participant_type": sender.participant_type,
            "participant_id": str(sender.participant_id),
            "display_name": name,
            "avatar_url": avatar,
        }

    def get_preview_messages(self, obj):
        from apps.chat.models import Message

        messages = (
            Message.objects.filter(
                conversation=obj.conversation,
            )
            .exclude(
                sender_type=obj.participant_type,
                sender_id=obj.participant_id,
            )
            .order_by("sequence_number")[:3]
        )

        return [
            {
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ]

    def get_message_count(self, obj):
        from apps.chat.models import Message

        return (
            Message.objects.filter(
                conversation=obj.conversation,
            )
            .exclude(
                sender_type=obj.participant_type,
                sender_id=obj.participant_id,
            )
            .count()
        )


class ChatBlockOutputSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    blocked_type = serializers.CharField()
    blocked_id = serializers.UUIDField()
    blocked_name = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()

    def get_blocked_name(self, obj):
        name, _ = _resolve_participant_display(obj.blocked_type, obj.blocked_id)
        return name


class MessageSearchOutputSerializer(serializers.Serializer):
    """Slim output for search results — message + conversation context."""

    id = serializers.UUIDField()
    conversation_id = serializers.UUIDField()
    sender_type = serializers.CharField()
    sender_id = serializers.UUIDField()
    sender_name = serializers.SerializerMethodField()
    content = serializers.CharField()
    status = serializers.CharField()
    sequence_number = serializers.IntegerField()
    created_at = serializers.DateTimeField()

    # Search-specific: conversation name for context
    conversation_name = serializers.SerializerMethodField()

    def get_sender_name(self, obj):
        name, _ = _resolve_participant_display(obj.sender_type, obj.sender_id)
        return name

    def get_conversation_name(self, obj):
        conv = getattr(obj, "conversation", None)
        if conv:
            return conv.name or ""
        return ""
